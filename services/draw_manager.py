from datetime import datetime, timedelta
import random
from sqlalchemy import desc
from db.database import get_session
from db.models import User, Draw
from config import CHANNEL_ID
from instance import bot
import asyncio

async def create_draw(name, prize_description, days_duration=7):
    """Create a new draw with scheduled end date"""
    session = get_session()
    
    # Calculate end date based on duration
    end_date = datetime.utcnow() + timedelta(days=days_duration)
    
    # Create the draw
    draw = Draw(
        name=name,
        prize_description=prize_description,
        scheduled_end=end_date,
        status="active"
    )
    
    session.add(draw)
    session.commit()
    
    return {
        "id": draw.id,
        "name": draw.name,
        "prize": draw.prize_description,
        "end_date": draw.scheduled_end
    }

async def get_active_draws():
    """Get list of active draws"""
    session = get_session()
    draws = session.query(Draw).filter(Draw.status == "active").all()
    
    result = []
    for draw in draws:
        result.append({
            "id": draw.id,
            "name": draw.name,
            "prize": draw.prize_description,
            "end_date": draw.scheduled_end,
            "days_left": (draw.scheduled_end - datetime.utcnow()).days if draw.scheduled_end else None
        })
    
    session.close()
    return result

async def get_draw_details(draw_id):
    """Get details of a specific draw"""
    session = get_session()
    draw = session.query(Draw).filter(Draw.id == draw_id).first()
    
    if not draw:
        session.close()
        return None
    
    result = {
        "id": draw.id,
        "name": draw.name,
        "status": draw.status,
        "prize": draw.prize_description,
        "created_at": draw.created_at,
        "scheduled_end": draw.scheduled_end,
        "ended_at": draw.ended_at,
        "winner_id": draw.winner_id
    }
    
    # Add winner details if available
    if draw.winner_id:
        winner = session.query(User).filter(User.id == draw.winner_id).first()
        if winner:
            result["winner_username"] = winner.username
            result["winner_first_name"] = winner.first_name
    
    session.close()
    return result

import asyncio

async def check_channel_membership(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status = member.status if isinstance(member.status, str) else member.status.value
        return status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def end_draw(draw_id):
    session = get_session()
    draw = session.query(Draw).filter(Draw.id == draw_id).first()
    if not draw or draw.status != "active":
        session.close()
        return None

    users_with_tickets = session.query(User).filter(User.ticket_count > 0).all()
    if not users_with_tickets:
        draw.status = "completed"
        draw.ended_at = datetime.utcnow()
        session.commit()
        session.close()
        return {"status": "completed", "message": "No eligible participants"}

    # Асинхронно проверяем всех
    checks = await asyncio.gather(
        *(check_channel_membership(u.id) for u in users_with_tickets)
    )
    eligible_users = [u for u, is_member in zip(users_with_tickets, checks) if is_member]

    if not eligible_users:
        draw.status = "completed"
        draw.ended_at = datetime.utcnow()
        session.commit()
        session.close()
        return {"status": "completed", "message": "No eligible participants who are channel members"}

    user_ids = [u.id for u in eligible_users]
    weights = [u.ticket_count for u in eligible_users]
    winner_id = random.choices(user_ids, weights=weights, k=1)[0]
    winner = session.query(User).filter(User.id == winner_id).first()

    draw.winner_id = winner_id
    draw.total_tickets = sum(weights)
    draw.status = "completed"
    draw.ended_at = datetime.utcnow()
    session.commit()
    session.close()
    return {
        "draw_id": draw.id,
        "winner_id": winner.id,
        "winner_username": winner.username,
        "winner_first_name": winner.first_name,
        "winner_tickets": winner.ticket_count,
        "total_tickets": sum(weights),
        "prize": draw.prize_description
    }

async def check_scheduled_draws():
    """Check for draws that should be ended based on schedule"""
    session = get_session()
    now = datetime.utcnow()
    
    # Find active draws that have reached their scheduled end time
    draws_to_end = session.query(Draw).filter(
        Draw.status == "active",
        Draw.scheduled_end <= now
    ).all()
    
    results = []
    for draw in draws_to_end:
        # End each draw and collect results
        draw_result = await end_draw(draw.id)
        if draw_result:
            results.append(draw_result)
    
    return results

async def cancel_draw(draw_id):
    """Cancel an active draw"""
    session = get_session()
    draw = session.query(Draw).filter(Draw.id == draw_id).first()
    
    if not draw or draw.status != "active":
        session.close()
        return False
    
    draw.status = "cancelled"
    draw.ended_at = datetime.utcnow()
    
    session.commit()
    session.close()
    return True