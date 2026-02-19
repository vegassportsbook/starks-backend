from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import datetime
import random

from database import engine, Base, get_db
import models
from schemas import TicketCreate, TicketSettle

# Create tables (Phase 1 simple approach)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS (lock to your Vercel domains later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Odds math helpers
# -----------------------------
def american_to_decimal(a: Optional[int]) -> Optional[float]:
    if a is None or a == 0:
        return None
    if a > 0:
        return 1 + (a / 100.0)
    return 1 + (100.0 / abs(a))

def american_to_implied_prob(a: Optional[int]) -> Optional[float]:
    if a is None or a == 0:
        return None
    if a > 0:
        return 100.0 / (a + 100.0)
    return abs(a) / (abs(a) + 100.0)

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

# Edge tiers based on projected_edge (0.06=6%)
def classify_tier(edge: Optional[float]) -> str:
    if edge is None:
        return "C"
    if edge >= 0.06:
        return "A"
    if edge >= 0.03:
        return "B"
    return "C"

# -----------------------------
# ROOT HEALTH CHECK
# -----------------------------
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {
        "ok": True,
        "message": "Starks Edge Lab Backend Online",
        "timestamp": str(datetime.datetime.utcnow())
    }

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "starks-edge-lab",
        "timestamp": str(datetime.datetime.utcnow())
    }

# -----------------------------
# Demo board (kept from your old build)
# -----------------------------
@app.get("/api/board")
def board():
    def move_line(base):
        return base + random.choice([-1, 0, 1])

    def compute_signal(edge_pct: float, odds_delta: float):
        ev_score = min((edge_pct or 0) / 0.05, 1)  # normalize: 5% edge -> 1
        steam_flag = abs(odds_delta) >= 1
        steam_score = 1 if steam_flag else 0
        drift_score = min(abs(odds_delta) / 2.0, 1)

        signal_score = (
            (ev_score * 30) +
            (steam_score * 35) +
            (drift_score * 20) +
            random.uniform(0, 15)
        )
        signal_score = min(round(signal_score), 100)

        if signal_score >= 81:
            label = "ELITE"
        elif signal_score >= 61:
            label = "SHARP WATCH"
        elif signal_score >= 31:
            label = "INTEREST"
        else:
            label = "NOISE"

        return signal_score, label, steam_flag

    raw_rows = [
        {"sport":"NCAAB","start":"02/18, 10:18 PM","matchup":"KANSAS @ BAYLOR","market":"ML","line":"KANSAS","base_odds":-135,"book":"DraftKings","edge_pct":0.032},
        {"sport":"NBA","start":"02/18, 8:57 PM","matchup":"BOS @ MIA","market":"SPREAD","line":"BOS -2.5","base_odds":-110,"book":"Circa","edge_pct":0.021},
        {"sport":"NFL","start":"02/18, 10:37 PM","matchup":"KC @ CIN","market":"TOTAL","line":"O 47.5","base_odds":-108,"book":"FanDuel","edge_pct":0.014},
    ]

    rows = []
    for r in raw_rows:
        moved_odds = move_line(r["base_odds"])
        odds_delta = moved_odds - r["base_odds"]
        signal_score, signal_label, steam_flag = compute_signal(r["edge_pct"], odds_delta)
        rows.append({
            "sport": r["sport"],
            "start": r["start"],
            "matchup": r["matchup"],
            "market": r["market"],
            "line": r["line"],
            "odds": moved_odds,
            "book": r["book"],
            "edge_pct": r["edge_pct"],
            "signal_score": signal_score,
            "signal_label": signal_label,
            "steam_detected": steam_flag
        })

    return JSONResponse({"ok": True, "rows": rows, "timestamp": str(datetime.datetime.utcnow())})

# -----------------------------
# Create tickets (Postgres)
# - single: one ticket per leg
# - parlay: one ticket with multiple legs
# -----------------------------
@app.post("/api/tickets")
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    if not payload.legs:
        raise HTTPException(status_code=400, detail="No legs provided")

    created_ids: List[int] = []

    def insert_ticket(bet_type: str, legs):
        # Combine probabilities/decimals for parlay, or use single leg for single
        if bet_type == "single":
            lg = legs[0]
            dec = american_to_decimal(lg.odds)
            imp = american_to_implied_prob(lg.odds)
            model_p = None
            if imp is not None and lg.edge_pct is not None:
                model_p = clamp01(imp + float(lg.edge_pct))
            edge = float(lg.edge_pct) if lg.edge_pct is not None else None
            tier = classify_tier(edge)

            cost = float(payload.stake)
            ev_profit = None
            if dec is not None and model_p is not None:
                ev_profit = cost * (dec * model_p - 1.0)

            t = models.Ticket(
                bet_type="single",
                market_type=lg.market_type,
                confidence_tier=tier,
                stake=payload.stake,
                cost=cost,
                american_odds=lg.odds,
                decimal_odds=dec,
                implied_prob=imp,
                model_prob=model_p,
                projected_edge=edge,
                ev_profit=ev_profit,
                status="pending",
                sport=payload.sport or lg.sport,
                event=payload.event or lg.matchup,
                selection=payload.selection or lg.line,
                book=payload.book or lg.book,
            )
            db.add(t)
            db.flush()  # get t.id

            leg_row = models.Leg(
                ticket_id=t.id,
                sport=lg.sport,
                start=lg.start,
                matchup=lg.matchup,
                market_type=lg.market_type,
                market=lg.market,
                line=lg.line,
                odds=lg.odds,
                book=lg.book,
                edge_pct=lg.edge_pct,
                signal_score=lg.signal_score,
                signal_label=lg.signal_label,
                steam_detected=bool(lg.steam_detected),
                implied_prob=imp,
                model_prob=model_p,
                decimal_odds=dec,
            )
            db.add(leg_row)
            return t.id

        # parlay
        decimals = []
        implieds = []
        models_p = []
        edges = []

        for lg in legs:
            dec = american_to_decimal(lg.odds)
            imp = american_to_implied_prob(lg.odds)
            model_p = None
            if imp is not None and lg.edge_pct is not None:
                model_p = clamp01(imp + float(lg.edge_pct))

            if dec is not None: decimals.append(dec)
            if imp is not None: implieds.append(imp)
            if model_p is not None: models_p.append(model_p)
            if lg.edge_pct is not None: edges.append(float(lg.edge_pct))

        dec_total = None
        imp_total = None
        model_total = None

        if decimals:
            d = 1.0
            for x in decimals: d *= x
            dec_total = d

        if implieds:
            p = 1.0
            for x in implieds: p *= x
            imp_total = p

        if models_p:
            mp = 1.0
            for x in models_p: mp *= x
            model_total = mp

        # Ticket-level projected edge (simple aggregate: mean of leg edges)
        edge = (sum(edges) / len(edges)) if edges else None
        tier = classify_tier(edge)

        cost = float(payload.stake)
        ev_profit = None
        if dec_total is not None and model_total is not None:
            ev_profit = cost * (dec_total * model_total - 1.0)

        t = models.Ticket(
            bet_type="parlay",
            market_type=None,
            confidence_tier=tier,
            stake=payload.stake,
            cost=cost,
            american_odds=None,
            decimal_odds=dec_total,
            implied_prob=imp_total,
            model_prob=model_total,
            projected_edge=edge,
            ev_profit=ev_profit,
            status="pending",
            sport=payload.sport,
            event=payload.event,
            selection=payload.selection,
            book=payload.book,
        )
        db.add(t)
        db.flush()

        for lg in legs:
            dec = american_to_decimal(lg.odds)
            imp = american_to_implied_prob(lg.odds)
            model_p = None
            if imp is not None and lg.edge_pct is not None:
                model_p = clamp01(imp + float(lg.edge_pct))

            db.add(models.Leg(
                ticket_id=t.id,
                sport=lg.sport,
                start=lg.start,
                matchup=lg.matchup,
                market_type=lg.market_type,
                market=lg.market,
                line=lg.line,
                odds=lg.odds,
                book=lg.book,
                edge_pct=lg.edge_pct,
                signal_score=lg.signal_score,
                signal_label=lg.signal_label,
                steam_detected=bool(lg.steam_detected),
                implied_prob=imp,
                model_prob=model_p,
                decimal_odds=dec,
            ))

        return t.id

    if payload.bet_type == "single":
        for lg in payload.legs:
            created_ids.append(insert_ticket("single", [lg]))
    else:
        created_ids.append(insert_ticket("parlay", payload.legs))

    db.commit()
    return {"ok": True, "created_ticket_ids": created_ids}

# -----------------------------
# Ticket list
# -----------------------------
@app.get("/api/tickets")
def list_tickets(limit: int = 50, db: Session = Depends(get_db)):
    tickets = db.query(models.Ticket).order_by(models.Ticket.id.desc()).limit(limit).all()

    out = []
    for t in tickets:
        out.append({
            "id": t.id,
            "created_at": str(t.created_at),
            "status": t.status,
            "result": t.result,
            "bet_type": t.bet_type,
            "market_type": t.market_type,
            "confidence_tier": t.confidence_tier,
            "stake": float(t.stake),
            "cost": float(t.cost),
            "profit": float(t.profit) if t.profit is not None else None,
            "projected_edge": float(t.projected_edge) if t.projected_edge is not None else None,
            "clv": float(t.clv) if t.clv is not None else None,
            "legs": [{
                "id": lg.id,
                "sport": lg.sport,
                "start": lg.start,
                "matchup": lg.matchup,
                "market_type": lg.market_type,
                "market": lg.market,
                "line": lg.line,
                "odds": lg.odds,
                "book": lg.book,
                "edge_pct": float(lg.edge_pct) if lg.edge_pct is not None else None,
                "signal_score": lg.signal_score,
                "signal_label": lg.signal_label,
                "steam_detected": lg.steam_detected,
            } for lg in (t.legs or [])]
        })

    return {"ok": True, "tickets": out}

# -----------------------------
# Settle a ticket
# profit convention:
# - loss: -cost
# - win: (stake * decimal_odds) - cost
# - push: 0
# -----------------------------
@app.post("/api/tickets/{ticket_id}/settle")
def settle_ticket(ticket_id: int, payload: TicketSettle, db: Session = Depends(get_db)):
    t = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status == "settled":
        return {"ok": True, "ticket_id": ticket_id, "status": "settled"}

    cost = float(t.cost)
    stake = float(t.stake)
    dec = float(t.decimal_odds) if t.decimal_odds is not None else None

    if payload.profit_override is not None:
        profit = float(payload.profit_override)
    else:
        if payload.result == "loss":
            profit = -cost
        elif payload.result == "push":
            profit = 0.0
        else:
            if dec is None:
                profit = stake - cost
            else:
                payout = stake * dec
                profit = payout - cost

    # CLV (simple placeholder): if closing_line provided and we have an american_odds (single)
    clv = None
    if payload.closing_line is not None and t.american_odds is not None:
        clv = float(payload.closing_line - int(t.american_odds))

    t.status = "settled"
    t.result = payload.result
    t.profit = profit
    t.closing_line = payload.closing_line
    t.clv = clv

    db.commit()
    return {"ok": True, "ticket_id": ticket_id, "result": payload.result, "profit": profit, "clv": clv}

# -----------------------------
# Performance summary (overall + splits)
# -----------------------------
@app.get("/api/performance")
def performance(db: Session = Depends(get_db)):
    tickets_all = db.query(models.Ticket).all()
    tickets_settled = db.query(models.Ticket).filter(models.Ticket.status == "settled").all()

    total = len(tickets_all)
    settled = len(tickets_settled)

    wins = sum(1 for t in tickets_settled if t.result == "win")
    losses = sum(1 for t in tickets_settled if t.result == "loss")

    profit = sum(float(t.profit) for t in tickets_settled if t.profit is not None)
    cost = sum(float(t.cost) for t in tickets_settled if t.cost is not None)

    roi = (profit / cost) if cost > 0 else 0.0
    winrate = (wins / settled) if settled > 0 else 0.0

    def split(filter_fn):
        group = [t for t in tickets_settled if filter_fn(t)]
        g_profit = sum(float(t.profit) for t in group if t.profit is not None)
        g_cost = sum(float(t.cost) for t in group if t.cost is not None)
        g_wins = sum(1 for t in group if t.result == "win")
        g_settled = len(group)
        return {
            "settled": g_settled,
            "wins": g_wins,
            "winrate": (g_wins / g_settled) if g_settled else 0.0,
            "profit": g_profit,
            "cost": g_cost,
            "roi": (g_profit / g_cost) if g_cost else 0.0,
        }

    by_tier = {
        "A": split(lambda t: t.confidence_tier == "A"),
        "B": split(lambda t: t.confidence_tier == "B"),
        "C": split(lambda t: t.confidence_tier == "C"),
    }

    singles = split(lambda t: t.bet_type == "single")
    parlays = split(lambda t: t.bet_type == "parlay")

    return {
        "ok": True,
        "total_tickets": total,
        "settled_tickets": settled,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "profit": profit,
        "cost": cost,
        "roi": roi,
        "splits": {
            "by_tier": by_tier,
            "singles": singles,
            "parlays": parlays,
        },
        "timestamp": str(datetime.datetime.utcnow())
    }
