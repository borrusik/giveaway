import random
from db.database import get_session
from db.models import User, Draw
from sqlalchemy import func

async def conduct_draw(prize_description=None):
    """Conduct a weighted random draw"""
    session = get_session()
    
    # Get all users with tickets
    users_with_tickets = session.query(User).filter(User.ticket_count > 0).all()
    
    if not users_with_tickets:
        return None  # No eligible participants
    
    # Prepare user IDs and weights for random.choices
    user_ids = [user.id for user in users_with_tickets]
    weights = [user.ticket_count for user in users_with_tickets]
    
    # Calculate total tickets
    total_tickets = sum(weights)
    
    # Select a winner based on ticket weights
    winner_id = random.choices(user_ids, weights=weights, k=1)[0]
    
    # Create draw record
    draw = Draw(
        winner_id=winner_id,
        total_tickets=total_tickets,
        prize_description=prize_description
    )
    
    session.add(draw)
    session.commit()
    
    # Get winner details for return
    winner = session.query(User).filter(User.id == winner_id).first()
    
    result = {
        "winner_id": winner.id,
        "winner_username": winner.username,
        "winner_first_name": winner.first_name,
        "winner_tickets": winner.ticket_count,
        "total_tickets": total_tickets,
        "win_chance": (winner.ticket_count / total_tickets) * 100,
        "draw_id": draw.id
    }
    
    return result