from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Starks Sportsbook Backend Online",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status")
def status():
    return {
        "ok": True
    }

@app.get("/health")
def health():
    return {"healthy": True}
