from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import datetime
import random
import sqlite3
import os
import json

app = FastAPI()

# -----------------------------
# CORS (CRITICAL FOR VERCEL)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock to Vercel later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# DB (SQLite)
# -----------------------------
DB_PATH = os.getenv("STARKS_DB_PATH", "starks.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        mode TEXT NOT NULL,                   -- single | parlay
        stake REAL NOT NULL,                  -- stake per ticket (parlay) or per-leg (single)
        bankroll REAL NOT NULL,
        cost REAL NOT NULL,
        decimal_odds REAL,
        implied_prob REAL,
        model_prob REAL,
        ev_profit REAL,
        status TEXT NOT NULL,                 -- pending | settled
        result TEXT,                          -- win | loss
        profit REAL,                          -- +profit or -cost
        meta_json TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS legs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        sport TEXT,
        start TEXT,
        matchup TEXT,
        market TEXT,
        line TEXT,
        odds REAL,
        book TEXT,
        edge REAL,
        signal_score REAL,
        signal_label TEXT,
        steam_detected INTEGER,
        implied_prob REAL,
        model_prob REAL,
        decimal_odds REAL,
        FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Odds math helpers
# -----------------------------
def american_to_decimal(a: Optional[float]) -> Optional[float]:
    if a is None or a == 0:
        return None
    if a > 0:
        return 1 + (a / 100.0)
    return 1 + (100.0 / abs(a))

def american_to_implied_prob(a: Optional[float]) -> Optional[float]:
    if a is None or a == 0:
        return None
    if a > 0:
        return 100.0 / (a + 100.0)
    return abs(a) / (abs(a) + 100.0)

# -----------------------------
# ROOT HEALTH CHECK
# -----------------------------
@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Starks Sportsbook Backend Online",
        "timestamp": str(datetime.datetime.utcnow())
    }

# -----------------------------
# API HEALTH
# -----------------------------
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "starks-backend",
        "timestamp": str(datetime.datetime.utcnow())
    }

# -----------------------------
# LIVE BOARD (DEMO + SIGNAL ENGINE)
# -----------------------------
@app.get("/api/board")
def board():

    def move_line(base):
        return base + random.choice([-1, 0, 1])

    def compute_signal(edge: float, odds_delta: float):
        ev_score = min((edge or 0) / 5.0, 1)
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
        {
            "sport": "NCAAB",
            "start": "02/18, 10:18 PM",
            "matchup": "KANSAS @ BAYLOR",
            "market": "ML",
            "line": "KANSAS",
            "base_odds": -135,
            "book": "DraftKings",
            "edge": round(random.uniform(1.5, 3.5), 2)
        },
        {
            "sport": "NBA",
            "start": "02/18, 8:57 PM",
            "matchup": "BOS @ MIA",
            "market": "SPREAD",
            "line": "BOS -2.5",
            "base_odds": -110,
            "book": "Circa",
            "edge": round(random.uniform(1.0, 3.0), 2)
        },
        {
            "sport": "NFL",
            "start": "02/18, 10:37 PM",
            "matchup": "KC @ CIN",
            "market": "TOTAL",
            "line": "O 47.5",
            "base_odds": -108,
            "book": "FanDuel",
            "edge": round(random.uniform(0.5, 2.5), 2)
        }
    ]

    rows = []
    for r in raw_rows:
        moved_odds = move_line(r["base_odds"])
        odds_delta = moved_odds - r["base_odds"]
        signal_score, signal_label, steam_flag = compute_signal(r["edge"], odds_delta)

        rows.append({
            "sport": r["sport"],
            "start": r["start"],
            "matchup": r["matchup"],
            "market": r["market"],
            "line": r["line"],
            "odds": moved_odds,
            "book": r["book"],
            "edge": r["edge"],
            "signal_score": signal_score,
            "signal_label": signal_label,
            "steam_detected": steam_flag
        })

    return JSONResponse({
        "ok": True,
        "rows": rows,
        "timestamp": str(datetime.datetime.utcnow())
    })

# -----------------------------
# TICKET LOGGING MODELS
# -----------------------------
class LegIn(BaseModel):
    sport: Optional[str] = None
    start: Optional[str] = None
    matchup: Optional[str] = None
    market: Optional[str] = None
    line: Optional[str] = None
    odds: Optional[float] = None
    book: Optional[str] = None
    edge: Optional[float] = None
    signal_score: Optional[float] = None
    signal_label: Optional[str] = None
    steam_detected: Optional[bool] = None

class TicketCreate(BaseModel):
    mode: Literal["single", "parlay"] = "parlay"
    stake: float = 25.0
    bankroll: float = 10000.0
    legs: List[LegIn] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

class TicketSettle(BaseModel):
    result: Literal["win", "loss"]

# -----------------------------
# Create tickets
# - single mode: creates one ticket per leg (clean analytics)
# - parlay mode: creates one ticket for the slip
# -----------------------------
@app.post("/api/tickets")
def create_ticket(payload: TicketCreate):
    created_at = str(datetime.datetime.utcnow())
    stake = float(payload.stake)
    bankroll = float(payload.bankroll)
    legs = payload.legs or []

    if not legs:
        return JSONResponse({"ok": False, "error": "No legs provided"}, status_code=400)

    conn = db()
    cur = conn.cursor()

    created_ids = []

    def insert_ticket(mode: str, ticket_legs: List[LegIn]) -> int:
        # compute combined decimals/probs
        decimals = []
        implieds = []
        models = []

        for lg in ticket_legs:
            dec = american_to_decimal(lg.odds)
            imp = american_to_implied_prob(lg.odds)
            # model prob approx: implied + edge
            model = None
            if imp is not None and lg.edge is not None:
                model = max(0.0, min(1.0, imp + (float(lg.edge) / 100.0)))

            if dec is not None: decimals.append(dec)
            if imp is not None: implieds.append(imp)
            if model is not None: models.append(model)

        if mode == "parlay":
            dec_total = 1.0
            imp_total = 1.0
            model_total = 1.0
            any_dec = False
            any_imp = False
            any_model = False

            for d in decimals:
                dec_total *= d
                any_dec = True
            for p in implieds:
                imp_total *= p
                any_imp = True
            for mp in models:
                model_total *= mp
                any_model = True

            decimal_odds = dec_total if any_dec else None
            implied_prob = imp_total if any_imp else None
            model_prob = model_total if any_model else None

            cost = stake
            ev_profit = None
            if decimal_odds is not None and model_prob is not None:
                ev_profit = cost * (decimal_odds * model_prob - 1.0)

        else:
            # single ticket: one leg only
            lg = ticket_legs[0]
            decimal_odds = american_to_decimal(lg.odds)
            implied_prob = american_to_implied_prob(lg.odds)
            model_prob = None
            if implied_prob is not None and lg.edge is not None:
                model_prob = max(0.0, min(1.0, implied_prob + (float(lg.edge) / 100.0)))
            cost = stake
            ev_profit = None
            if decimal_odds is not None and model_prob is not None:
                ev_profit = cost * (decimal_odds * model_prob - 1.0)

        cur.execute("""
            INSERT INTO tickets
            (created_at, mode, stake, bankroll, cost, decimal_odds, implied_prob, model_prob, ev_profit, status, result, profit, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?)
        """, (
            created_at, mode, stake, bankroll, float(cost),
            decimal_odds, implied_prob, model_prob, ev_profit,
            json.dumps(payload.meta or {})
        ))

        ticket_id = cur.lastrowid

        for lg in ticket_legs:
            dec = american_to_decimal(lg.odds)
            imp = american_to_implied_prob(lg.odds)
            model = None
            if imp is not None and lg.edge is not None:
                model = max(0.0, min(1.0, imp + (float(lg.edge) / 100.0)))

            cur.execute("""
                INSERT INTO legs
                (ticket_id, sport, start, matchup, market, line, odds, book, edge, signal_score, signal_label, steam_detected, implied_prob, model_prob, decimal_odds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_id,
                lg.sport, lg.start, lg.matchup, lg.market, lg.line,
                lg.odds, lg.book, lg.edge,
                lg.signal_score, lg.signal_label,
                1 if lg.steam_detected else 0,
                imp, model, dec
            ))

        return ticket_id

    if payload.mode == "single":
        for lg in legs:
            created_ids.append(insert_ticket("single", [lg]))
    else:
        created_ids.append(insert_ticket("parlay", legs))

    conn.commit()
    conn.close()

    return {"ok": True, "created_ticket_ids": created_ids}

# -----------------------------
# Ticket history
# -----------------------------
@app.get("/api/tickets")
def list_tickets(limit: int = 50):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM tickets ORDER BY id DESC LIMIT ?
    """, (limit,))
    tickets = [dict(r) for r in cur.fetchall()]

    # attach legs
    for t in tickets:
        cur.execute("SELECT * FROM legs WHERE ticket_id = ? ORDER BY id ASC", (t["id"],))
        t["legs"] = [dict(x) for x in cur.fetchall()]
        # coerce some fields
        if t.get("meta_json"):
            try:
                t["meta"] = json.loads(t["meta_json"])
            except:
                t["meta"] = {}
        else:
            t["meta"] = {}
        t.pop("meta_json", None)

    conn.close()
    return {"ok": True, "tickets": tickets}

# -----------------------------
# Settle ticket (win/loss) and compute profit
# profit convention:
# - loss: -cost
# - win: (stake * decimal_odds) - cost
# -----------------------------
@app.post("/api/tickets/{ticket_id}/settle")
def settle_ticket(ticket_id: int, payload: TicketSettle):
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    t = cur.fetchone()
    if not t:
        conn.close()
        return JSONResponse({"ok": False, "error": "Ticket not found"}, status_code=404)

    if t["status"] == "settled":
        conn.close()
        return {"ok": True, "ticket_id": ticket_id, "status": "settled"}

    cost = float(t["cost"])
    stake = float(t["stake"])
    dec = t["decimal_odds"]
    mode = t["mode"]

    if payload.result == "loss":
        profit = -cost
    else:
        if dec is None:
            # if decimal unknown, assume even money payout
            profit = stake - cost
        else:
            payout = stake * float(dec)
            profit = payout - cost

    cur.execute("""
        UPDATE tickets
        SET status='settled', result=?, profit=?
        WHERE id=?
    """, (payload.result, float(profit), ticket_id))

    conn.commit()
    conn.close()

    return {"ok": True, "ticket_id": ticket_id, "result": payload.result, "profit": profit}

# -----------------------------
# Performance summary
# -----------------------------
@app.get("/api/performance")
def performance():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as n FROM tickets")
    total = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM tickets WHERE status='settled'")
    settled = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM tickets WHERE status='settled' AND result='win'")
    wins = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM tickets WHERE status='settled' AND result='loss'")
    losses = cur.fetchone()["n"]

    cur.execute("SELECT COALESCE(SUM(profit), 0) as p FROM tickets WHERE status='settled'")
    profit = float(cur.fetchone()["p"] or 0)

    cur.execute("SELECT COALESCE(SUM(cost), 0) as c FROM tickets WHERE status='settled'")
    cost = float(cur.fetchone()["c"] or 0)

    roi = (profit / cost) if cost > 0 else 0.0
    winrate = (wins / settled) if settled > 0 else 0.0

    # last 30 days
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat()
    cur.execute("SELECT COALESCE(SUM(profit),0) as p FROM tickets WHERE status='settled' AND created_at >= ?", (cutoff,))
    profit_30 = float(cur.fetchone()["p"] or 0)

    conn.close()

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
        "profit_30d": profit_30,
        "timestamp": str(datetime.datetime.utcnow())
    }
