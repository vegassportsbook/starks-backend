from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
