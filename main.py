from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

# Allow requests from anywhere (safe for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Starks Sportsbook Backend Online",
        "timestamp": str(datetime.datetime.utcnow())
    }

@app.get("/status")
def status():
    return {
        "status": "running",
        "timestamp": str(datetime.datetime.utcnow())
    }

@app.get("/api/board")
def board():
    now = datetime.datetime.utcnow()

    return {
        "rows": [
            {
                "sport": "NBA",
                "start": str(now + datetime.timedelta(minutes=20)),
                "matchup": "BOS @ MIA",
                "market": "SPREAD",
                "line": "BOS -2.5",
                "odds": "-110",
                "book": "Circa",
                "edge": 2.4,
                "live": True
            },
            {
                "sport": "NCAAB",
                "start": str(now + datetime.timedelta(minutes=45)),
                "matchup": "KANSAS @ BAYLOR",
                "market": "ML",
                "line": "KANSAS",
                "odds": "+135",
                "book": "DraftKings",
                "edge": 3.1,
                "live": False
            },
            {
                "sport": "NFL",
                "start": str(now + datetime.timedelta(hours=3)),
                "matchup": "KC @ CIN",
                "market": "TOTAL",
                "line": "O 47.5",
                "odds": "-108",
                "book": "FanDuel",
                "edge": 1.7,
                "live": False
            }
        ]
    }
