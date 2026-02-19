from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Classification / splits
    bet_type = Column(String, nullable=False)       # "single" | "parlay"
    market_type = Column(String, nullable=True)     # "game_line" | "prop" (optional on ticket; legs can have their own)

    confidence_tier = Column(String(1), nullable=False, default="C")  # A/B/C

    # Money
    stake = Column(Numeric(10, 2), nullable=False, default=0)
    cost = Column(Numeric(10, 2), nullable=False, default=0)

    # Odds + model
    american_odds = Column(Integer, nullable=True)                 # for parlay this can be null
    decimal_odds = Column(Numeric(12, 6), nullable=True)
    implied_prob = Column(Numeric(12, 6), nullable=True)
    model_prob = Column(Numeric(12, 6), nullable=True)
    projected_edge = Column(Numeric(12, 6), nullable=True)         # 0.06 = 6%
    ev_profit = Column(Numeric(12, 6), nullable=True)

    # Result / settlement
    status = Column(String, nullable=False, default="pending")     # pending | settled
    result = Column(String, nullable=True)                         # win | loss | push (optional)
    profit = Column(Numeric(12, 6), nullable=True)

    # CLV
    closing_line = Column(Integer, nullable=True)
    clv = Column(Numeric(12, 6), nullable=True)

    # Optional metadata
    sport = Column(String, nullable=True)
    event = Column(String, nullable=True)
    selection = Column(String, nullable=True)
    book = Column(String, nullable=True)

    legs = relationship("Leg", back_populates="ticket", cascade="all, delete-orphan")


class Leg(Base):
    __tablename__ = "legs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)

    sport = Column(String, nullable=True)
    start = Column(String, nullable=True)
    matchup = Column(String, nullable=True)

    market_type = Column(String, nullable=True)  # "game_line" | "prop"
    market = Column(String, nullable=True)
    line = Column(String, nullable=True)

    odds = Column(Integer, nullable=True)        # American odds
    book = Column(String, nullable=True)

    # Signal/edge
    edge_pct = Column(Numeric(12, 6), nullable=True)        # 0.03 = 3%
    signal_score = Column(Integer, nullable=True)
    signal_label = Column(String, nullable=True)
    steam_detected = Column(Boolean, nullable=False, default=False)

    implied_prob = Column(Numeric(12, 6), nullable=True)
    model_prob = Column(Numeric(12, 6), nullable=True)
    decimal_odds = Column(Numeric(12, 6), nullable=True)

    ticket = relationship("Ticket", back_populates="legs")
