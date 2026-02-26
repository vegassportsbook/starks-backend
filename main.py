from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import datetime
import random

from database import engine, Base, get_db
import models
from schemas import TicketCreate, TicketSettle, EvalRequest, EvalResponse
from intelligence import evaluate_market_rows

app = FastAPI()

# -----------------------------
# STARTUP EVENT (SAFE DB INIT)
# -----------------------------
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# -----------------------------
# CORS
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
        "message": "Starks Edge Lab Backend Online",
        "timestamp": str(datetime.datetime.utcnow())
    }

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "starks-edge-lab",
        "timestamp": str(datetime.datetime.utcnow())
    }

# -----------------------------
# PHASE 2 – EVALUATION ENGINE
# -----------------------------
@app.post("/api/eval", response_model=EvalResponse)
def eval_lines(payload: EvalRequest):
    rows = [r.model_dump() for r in payload.rows]

    evaluated = evaluate_market_rows(
        rows=rows,
        bankroll=float(payload.bankroll),
        unit_size=float(payload.unit_size),
        kelly_fraction=float(payload.kelly_fraction),
        max_units=float(payload.max_units),
        sharp_watch_threshold=float(payload.sharp_watch_threshold),
    )

    return {
        "ok": True,
        "rows": evaluated,
        "timestamp": str(datetime.datetime.utcnow())
    }
