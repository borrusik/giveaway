from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    referral_code = Column(String, unique=True, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # One-to-many: One user can refer many others
    referrals = relationship("Referral", back_populates="referrer", foreign_keys="Referral.referrer_id")
    
    # Who referred this user
    referred_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    # Tickets earned (for faster lookup)
    ticket_count = Column(Integer, default=0)
    
    # Draw history
    wins = relationship("Draw", back_populates="winner")

class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    referred_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    referrer = relationship("User", back_populates="referrals", foreign_keys=[referrer_id])
    referred = relationship("User", foreign_keys=[referred_id])

class Draw(Base):
    __tablename__ = "draws"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, default="Розіграш")
    status = Column(String, nullable=False, default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_end = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    winner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    total_tickets = Column(Integer, nullable=True)
    prize_description = Column(String, nullable=True)
    
    # Relationship
    winner = relationship("User", back_populates="wins")