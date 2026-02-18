
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import datetime
import random

app = FastAPI()

# -----------------------------
# CORS (CRITICAL FOR VERCEL)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # -----------------------------
    # SIGNAL ENGINE
    # -----------------------------
    def compute_signal(edge, odds_delta):

        # Normalize EV (assuming 0–5% typical range)
        ev_score = min(edge / 5.0, 1)

        # Steam detection
        steam_flag = abs(odds_delta) >= 1
        steam_score = 1 if steam_flag else 0

        # Drift intensity
        drift_score = min(abs(odds_delta) / 2.0, 1)

        # Weighted scoring
        signal_score = (
            (ev_score * 30) +
            (steam_score * 35) +
            (drift_score * 20) +
            random.uniform(0, 15)  # demo variation
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

        signal_score, signal_label, steam_flag = compute_signal(
            r["edge"],
            odds_delta
        )

        rows.append({
            "sport": r["sport"],
            "start": r["start"],
            "matchup": r["matchup"],
            "market": r["market"],
            "line": r["line"],
            "odds": moved_odds,
            "book": r["book"],
            "edge": r["edge"],

            # 🔴 NEW FIELDS
            "signal_score": signal_score,
            "signal_label": signal_label,
            "steam_detected": steam_flag
        })

    return JSONResponse({
        "ok": True,
        "rows": rows,
        "timestamp": str(datetime.datetime.utcnow())
    })
