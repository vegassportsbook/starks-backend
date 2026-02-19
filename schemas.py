from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any


class LegIn(BaseModel):
    sport: Optional[str] = None
    start: Optional[str] = None
    matchup: Optional[str] = None

    market_type: Optional[Literal["game_line", "prop"]] = None
    market: Optional[str] = None
    line: Optional[str] = None

    odds: Optional[int] = None
    book: Optional[str] = None

    edge_pct: Optional[float] = None          # 0.06 = 6%
    signal_score: Optional[int] = None
    signal_label: Optional[str] = None
    steam_detected: Optional[bool] = False


class TicketCreate(BaseModel):
    bet_type: Literal["single", "parlay"] = "parlay"
    stake: float = 25.0
    legs: List[LegIn] = Field(default_factory=list)

    # optional top-level metadata
    sport: Optional[str] = None
    event: Optional[str] = None
    selection: Optional[str] = None
    book: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TicketSettle(BaseModel):
    result: Literal["win", "loss", "push"] = "win"
    closing_line: Optional[int] = None
    # If you want to override profit manually, allow it:
    profit_override: Optional[float] = None


class TicketOut(BaseModel):
    id: int
    status: str
    result: Optional[str] = None
    bet_type: str
    confidence_tier: str
    stake: float
    cost: float
    profit: Optional[float] = None

    class Config:
        from_attributes = True
