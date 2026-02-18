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
    allow_origins=["*"],  # You can lock this to your Vercel URL later
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
# LIVE BOARD (DEMO GENERATOR)
# -----------------------------
@app.get("/api/board")
def board():

    # Slight random line movement each refresh
    def move_line(base):
        return base + random.choice([-1, 0, 1])

    rows = [
        {
            "sport": "NCAAB",
            "start": "02/18, 10:18 PM",
            "matchup": "KANSAS @ BAYLOR",
            "market": "ML",
            "line": "KANSAS",
            "odds": move_line(-135),
            "book": "DraftKings",
            "edge": round(random.uniform(1.5, 3.5), 2)
        },
        {
            "sport": "NBA",
            "start": "02/18, 8:57 PM",
            "matchup": "BOS @ MIA",
            "market": "SPREAD",
            "line": "BOS -2.5",
            "odds": move_line(-110),
            "book": "Circa",
            "edge": round(random.uniform(1.0, 3.0), 2)
        },
        {
            "sport": "NFL",
            "start": "02/18, 10:37 PM",
            "matchup": "KC @ CIN",
            "market": "TOTAL",
            "line": "O 47.5",
            "odds": move_line(-108),
            "book": "FanDuel",
            "edge": round(random.uniform(0.5, 2.5), 2)
        }
    ]

    return JSONResponse({
        "ok": True,
        "rows": rows,
        "timestamp": str(datetime.datetime.utcnow())
    })
