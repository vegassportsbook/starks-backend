from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP
from sqlalchemy.sql import func
from database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    sport = Column(String)
    market_type = Column(String)
    bet_type = Column(String)

    event = Column(String)
    selection = Column(String)

    odds = Column(Integer)
    stake = Column(DECIMAL)

    confidence_tier = Column(String)
    implied_probability = Column(DECIMAL)
    projected_edge = Column(DECIMAL)

    result = Column(String, default="pending")
    payout = Column(DECIMAL)

    closing_line = Column(Integer)
    clv = Column(DECIMAL)
