import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime

from config import BOT_TOKEN
from db.database import init_db
from instance import bot
from middlewares.channel_join import ChannelJoinMiddleware
from services.draw_manager import check_scheduled_draws

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scheduler task
# Scheduler task
async def scheduled_tasks():
    while True:
        try:
            # Check for draws that need to be ended
            results = await check_scheduled_draws()
            
            # Announce winners for completed draws
            if results:
                for result in results:
                    if "message" in result:
                        logger.info(f"Draw {result.get('draw_id', 'unknown')} completed: {result['message']}")
                        continue
                    
                    logger.info(f"Draw #{result['draw_id']} completed, winner: {result['winner_id']}")
                    
                    # Format winner announcement
                    win_chance_formatted = f"{result['win_chance']:.2f}%"
                    
                    # Include eligibility stats for logs
                    eligibility_info = ""
                    eligibility_log = ""
                    if "eligible_users_count" in result and "total_users_count" in result:
                        eligibility_info = f"👥 Учасників розіграшу: <b>{result['eligible_users_count']}</b> з {result['total_users_count']} (активні учасники каналу)\n"
                        eligibility_log = f"Eligible users: {result['eligible_users_count']} of {result['total_users_count']}"
                    
                    logger.info(f"Draw #{result['draw_id']} completed. {eligibility_log}")
                    
                    winner_text = (
                        f"🎉 <b>Розіграш автоматично завершено!</b>\n\n"
                        f"🏆 Розіграш: <b>{result['draw_name']}</b>\n"
                        f"👑 Переможець: "
                        f"{'@' + result['winner_username'] if result['winner_username'] else 'Учасник'}\n"
                        f"🆔 ID: <code>{result['winner_id']}</code>\n"
                        f"🎟 Кількість квитків: <b>{result['winner_tickets']}</b>\n"
                        f"🎯 Шанс на перемогу: <b>{win_chance_formatted}</b>\n"
                        f"🏆 Загальна кількість квитків: <b>{result['total_tickets']}</b>\n\n"
                        f"🎁 Приз: <b>{result['prize']}</b>"
                    )
                    
                    # Send winner announcement to channel
                    try:
                        from config import CHANNEL_ID
                        await bot.send_message(CHANNEL_ID, winner_text)
                    except Exception as e:
                        logger.error(f"Error sending winner announcement: {e}")
            
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)

async def main():
    # Initialize dispatcher with storage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middlewares
    dp.message.middleware(ChannelJoinMiddleware())
    
    # Import routers here to avoid circular imports
    from handlers import admin, common, stats
    
    # Register routers
    dp.include_router(common.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)
    
    # Initialize database
    init_db()
    
    # Set bot commands
    await set_commands()
    
    # Start the scheduler task
    asyncio.create_task(scheduled_tasks())
    
    # Start polling
    await dp.start_polling(bot, skip_updates=True)
    
async def set_commands():
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="Почати участь у розіграші"),
        BotCommand(command="me", description="Переглянути свою статистику"),
        BotCommand(command="top", description="Переглянути лідерів запрошень"),
        BotCommand(command="help", description="Показати довідку")
    ]
    await bot.set_my_commands(commands)

if __name__ == "__main__":
    logger.info("Starting bot")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")