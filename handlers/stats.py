from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from db.database import get_session
from db.models import User

# Initialize router
router = Router()

@router.message(Command("top"))
async def cmd_top(message: Message):
    """Handle /top command - show top referrers"""
    session = get_session()
    
    # Get top 10 users by ticket count
    top_users = session.query(User).order_by(User.ticket_count.desc()).limit(10).all()
    
    if not top_users:
        await message.answer("Поки що немає учасників з квитками.")
        return
    
    top_text = f"<b>🏆 ТОП 10 учасників за кількістю квитків:</b>\n\n"
    
    for i, user in enumerate(top_users, 1):
        username = user.username or f"ID: {user.id}"
        name_display = f"@{username}" if user.username else username
        
        top_text += f"{i}. {name_display} — <b>{user.ticket_count}</b> квитків\n"
    
    await message.answer(top_text)