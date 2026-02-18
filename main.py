from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import datetime

app = FastAPI()

# 🔥 Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_sport = "MLB"

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Starks Sportsbook Backend Online",
        "timestamp": str(datetime.datetime.utcnow())
    }

@app.post("/api/set_sport")
def set_sport(data: dict):
    global current_sport
    current_sport = data.get("sport", "MLB")
    return {"ok": True, "sport": current_sport}

@app.post("/api/mock_slate")
def mock_slate(data: dict):
    rows = data.get("rows", 100)
    return {
        "ok": True,
        "message": f"Mock slate generated",
        "rows": rows,
        "sport": current_sport
    }

@app.get("/api/status")
def status():
    return {
        "ok": True,
        "sport": current_sport,
        "engine": "FastAPI Live"
    }

@app.post("/api/optimize")
def optimize(data: dict):
    return {
        "ok": True,
        "profile": data.get("profile"),
        "lineups_requested": data.get("lineups"),
        "result": "Optimization complete (mock)"
    }

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    return {
        "ok": True,
        "filename": file.filename,
        "message": "File received"
    }
