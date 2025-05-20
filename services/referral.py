import uuid
import base64
from db.database import get_session
from db.models import User, Referral
from config import CHANNEL_USERNAME

def generate_referral_code():
    """Generate a unique referral code"""
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8')[:8]

def create_referral_link(user_id):
    """Create a referral link for a user"""
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        return None
    
    # Create a deep link to the bot (not channel) with the referral code as start parameter
    # This is the correct way to track referrals in Telegram
    bot_username = "AirChainMiniAppBot"  # Replace with your bot's username
    link = f"https://t.me/{bot_username}?start={user.referral_code}"
    
    return link

async def process_referral(referrer_id, referred_id):
    """Process a successful referral, update tickets"""
    session = get_session()
    
    # Check if this is a new referral
    existing = session.query(Referral).filter(
        Referral.referrer_id == referrer_id, 
        Referral.referred_id == referred_id
    ).first()
    
    if existing:
        return False  # Already processed
    
    # Create the referral record
    referral = Referral(referrer_id=referrer_id, referred_id=referred_id)
    session.add(referral)
    
    # Update the referrer's ticket count
    referrer = session.query(User).filter(User.id == referrer_id).first()
    referrer.ticket_count += 1
    
    session.commit()
    return True

def get_referral_stats(user_id):
    """Get referral statistics for a user"""
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        return None
    
    # Calculate total tickets in the system for chance calculation
    total_tickets = session.query(User).with_entities(
        User.ticket_count).filter(User.ticket_count > 0).all()
    
    total_tickets_sum = sum(t[0] for t in total_tickets)
    win_chance = (user.ticket_count / max(total_tickets_sum, 1)) * 100 if total_tickets_sum > 0 else 0
    
    result = {
        "tickets": user.ticket_count,
        "total_tickets": total_tickets_sum,
        "win_chance": round(win_chance, 2),
        "referrals_count": len(user.referrals)
    }
    
    return result