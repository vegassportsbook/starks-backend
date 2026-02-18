from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

app = FastAPI()

# --- CORS (allow Vercel frontend) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROOT ROUTE ---
@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Starks Sportsbook Backend Online",
        "timestamp": datetime.utcnow().isoformat()
    }

# --- STATUS ROUTE ---
@app.get("/status")
def status():
    return {
        "ok": True,
        "service": "running",
        "timestamp": datetime.utcnow().isoformat()
    }
