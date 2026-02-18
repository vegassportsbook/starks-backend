from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import datetime

app = FastAPI(title="Starks Sportsbook Backend")

# --------------------------------------------------
# CORS (Allow Vercel + Browser Access)
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict later to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Root Health Check
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Starks Sportsbook Backend Online",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

# --------------------------------------------------
# Status Endpoint
# --------------------------------------------------

@app.get("/status")
def status():
    return {
        "backend": "running",
        "engine": "online",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

# --------------------------------------------------
# Mock Slate Endpoint
# --------------------------------------------------

@app.post("/mock_slate")
def mock_slate(rows: int = 100):
    return {
        "ok": True,
        "rows_generated": rows,
        "note": "Mock slate created"
    }

# --------------------------------------------------
# Set Sport Endpoint
# --------------------------------------------------

@app.post("/set_sport")
def set_sport(payload: dict):
    return {
        "ok": True,
        "sport_selected": payload.get("sport", "Unknown")
    }

# --------------------------------------------------
# Optimize Endpoint
# --------------------------------------------------

@app.post("/optimize")
def optimize(payload: dict):
    return {
        "ok": True,
        "profile": payload.get("profile"),
        "lineups_requested": payload.get("lineups"),
        "result": "Optimization simulated"
    }

# --------------------------------------------------
# CSV Upload Endpoint
# --------------------------------------------------

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    return {
        "ok": True,
        "filename": file.filename,
        "note": "File received successfully"
    }
