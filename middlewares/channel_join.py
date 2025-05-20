from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.exceptions import TelegramAPIError
from config import CHANNEL_ID
from instance import bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class ChannelJoinMiddleware(BaseMiddleware):
    """Middleware to verify if a user has joined the channel"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Skip middleware for start command
        if event.text and event.text.startswith('/start'):
            return await handler(event, data)
        
        # Check if user is subscribed to the channel
        try:
            user_id = event.from_user.id
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            
            # Check member status - handle both string and enum cases
            status = member.status
            if isinstance(status, str):
                member_status = status
            else:
                # For older versions of aiogram where status might be an enum
                member_status = status.value
                
            # If user is not a member or left the channel
            if member_status in ['left', 'kicked', 'restricted']:
                invite_link = await bot.export_chat_invite_link(CHANNEL_ID)
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Перейти в канал", url=invite_link)],
                    [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_join")]
                ])
                await event.answer(
                    f"Підпишіться на канал: {invite_link}\n"
                    f"Після підписки натисніть /start"
                )
                return None
                
        except TelegramAPIError as e:
            # Log the error but continue processing
            print(f"Error checking channel membership: {e}")
            pass
            
        return await handler(event, data)