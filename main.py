from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import datetime

app = FastAPI()

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROOT ROUTE (THIS FIXES YOUR ISSUE)
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

@app.post("/mock_slate")
def mock_slate(data: dict):
    rows = data.get("rows", 100)
    return {
        "ok": True,
        "rows_generated": rows
    }

@app.post("/optimize")
def optimize(data: dict):
    return {
        "ok": True,
        "profile": data.get("profile"),
        "lineups": data.get("lineups"),
        "message": "Optimization complete"
    }
