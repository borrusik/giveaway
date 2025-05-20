import asyncio
import logging
import signal
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime

from config import BOT_TOKEN, LOG_LEVEL
from db.database import init_db, close_db
from instance import bot
from middlewares.channel_join import ChannelJoinMiddleware
from middlewares.error_handler import ErrorHandlerMiddleware
from services.draw_manager import check_scheduled_draws
from utils.logger import setup_logger

# Configure logging
logger = setup_logger("bot", LOG_LEVEL)

# Global shutdown flag
shutdown_event = asyncio.Event()

# Scheduler task
async def scheduled_tasks():
    check_interval = 3600  # Default: check every hour
    
    while not shutdown_event.is_set():
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
                        logger.info(f"Winner announcement sent to channel for draw #{result['draw_id']}")
                    except Exception as e:
                        logger.error(f"Error sending winner announcement: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error in scheduler: {e}", exc_info=True)
        
        # Wait for next check interval or until shutdown is requested
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=check_interval)
        except asyncio.TimeoutError:
            pass  # Normal timeout, continue with the next iteration

async def shutdown(dispatcher: Dispatcher):
    """Graceful shutdown function"""
    logger.info("Shutting down...")
    
    # Signal scheduler task to stop
    shutdown_event.set()
    
    # Close bot session
    await bot.session.close()
    
    # Close DB connections
    close_db()
    
    logger.info("Shutdown complete")

async def main():
    # Initialize dispatcher with storage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middlewares
    dp.message.middleware(ChannelJoinMiddleware())
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    
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
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(dp)))
    
    # Start the scheduler task
    scheduler_task = asyncio.create_task(scheduled_tasks())
    
    try:
        # Start polling
        logger.info("Starting bot")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        # Ensure the scheduler task is cancelled if polling stops
        scheduler_task.cancel()
        await shutdown(dp)
    
async def set_commands():
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="Почати участь у розіграші"),
        BotCommand(command="me", description="Переглянути свою статистику"),
        BotCommand(command="top", description="Переглянути лідерів запрошень"),
        BotCommand(command="draws", description="Переглянути активні розіграші"),
        BotCommand(command="help", description="Показати довідку")
    ]
    await bot.set_my_commands(commands)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")