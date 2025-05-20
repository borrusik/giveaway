from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from services.draw_manager import create_draw, get_active_draws, get_draw_details, end_draw, cancel_draw
from config import ADMIN_IDS, CHANNEL_ID
from instance import bot

# Initialize router
router = Router()

@router.message(Command("newdraw"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_new_draw(message: Message):
    """Handle /newdraw command - create a new draw"""
    # Parse command arguments: /newdraw [name] [prize] [days]
    parts = message.text.split(maxsplit=3)
    
    name = "Розіграш"
    prize = "Приз"
    days = 7
    
    # Get arguments if provided
    if len(parts) >= 2:
        name = parts[1]
    if len(parts) >= 3:
        prize = parts[2]
    if len(parts) >= 4:
        try:
            days = int(parts[3])
        except ValueError:
            pass
    
    # Create the draw
    result = await create_draw(name, prize, days)
    
    # Format the response
    end_date = result["end_date"].strftime("%d.%m.%Y %H:%M")
    
    await message.answer(
        f"✅ Створено новий розіграш!\n\n"
        f"🏆 Назва: <b>{result['name']}</b>\n"
        f"🎁 Приз: <b>{result['prize']}</b>\n"
        f"📅 Дата закінчення: <b>{end_date}</b> (через {days} днів)\n\n"
        f"ID розіграшу: <code>{result['id']}</code>"
    )
    
    # Announce in the channel
    try:
        await bot.send_message(
            CHANNEL_ID,
            f"🎉 <b>Новий розіграш розпочато!</b>\n\n"
            f"🏆 {result['name']}\n"
            f"🎁 Приз: <b>{result['prize']}</b>\n"
            f"📅 Розіграш закінчиться: <b>{end_date}</b>\n\n"
            f"Запрошуйте друзів та збільшуйте свої шанси на перемогу! /start"
        )
    except Exception as e:
        await message.answer(f"Помилка при відправці оголошення в канал: {str(e)}")

@router.message(Command("draws"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_list_draws(message: Message):
    """Handle /draws command - list active draws"""
    draws = await get_active_draws()
    
    if not draws:
        await message.answer("На даний момент немає активних розіграшів.")
        return
    
    # Build response
    response = "<b>📋 Активні розіграші:</b>\n\n"
    
    for draw in draws:
        end_date = draw["end_date"].strftime("%d.%m.%Y %H:%M") if draw["end_date"] else "Не вказано"
        days_left = f"{draw['days_left']} днів" if draw["days_left"] is not None else "Не вказано"
        
        response += (
            f"🆔 <code>{draw['id']}</code>\n"
            f"🏆 <b>{draw['name']}</b>\n"
            f"🎁 Приз: {draw['prize']}\n"
            f"⏳ Залишилось: {days_left}\n"
            f"📅 Закінчення: {end_date}\n\n"
        )
    
    # Add inline keyboard for actions
    builder = InlineKeyboardBuilder()
    
    for draw in draws:
        builder.button(
            text=f"Закінчити #{draw['id']}", 
            callback_data=f"end_draw:{draw['id']}"
        )
    
    for draw in draws:
        builder.button(
            text=f"Скасувати #{draw['id']}", 
            callback_data=f"cancel_draw:{draw['id']}"
        )
    
    # Adjust grid layout
    builder.adjust(1)
    
    await message.answer(response, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("end_draw:"))
async def callback_end_draw(callback: CallbackQuery):
    """Handle callback to end a draw"""
    # Check if user is admin
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас немає прав для цієї дії.")
        return
    
    # Get the draw ID from callback data
    draw_id = int(callback.data.split(":")[1])
    
    # Show "processing" message
    await callback.answer("Проводимо розіграш і перевіряємо учасників...")
    
    # End the draw
    result = await end_draw(draw_id)
    
    if not result:
        await callback.answer("Не вдалося завершити розіграш.")
        await callback.message.answer("❌ Помилка: розіграш не знайдено або вже завершений.")
        return
    
    # Format winner announcement
    if "message" in result:
        # No eligible participants
        await callback.message.answer(
            f"ℹ️ Розіграш #{draw_id} завершено, але {result['message'].lower()}."
        )
        return
    
    win_chance_formatted = f"{result['win_chance']:.2f}%"
    
    # Include eligibility stats
    eligibility_info = ""
    if "eligible_users_count" in result and "total_users_count" in result:
        eligibility_info = f"👥 Учасників розіграшу: <b>{result['eligible_users_count']}</b> з {result['total_users_count']} (активні учасники каналу)\n"
    
    winner_text = (
        f"🎉 <b>Розіграш завершено!</b>\n\n"
        f"🏆 Розіграш: <b>{result['draw_name']}</b>\n"
        f"{eligibility_info}"
        f"👑 Переможець: "
        f"{'@' + result['winner_username'] if result['winner_username'] else 'Учасник'}\n"
        f"🆔 ID: <code>{result['winner_id']}</code>\n"
        f"🎟 Кількість квитків: <b>{result['winner_tickets']}</b>\n"
        f"🎯 Шанс на перемогу: <b>{win_chance_formatted}</b>\n"
        f"🏆 Загальна кількість квитків: <b>{result['total_tickets']}</b>\n\n"
        f"🎁 Приз: <b>{result['prize']}</b>"
    )
    
    # Send winner announcement to admin
    await callback.message.answer(winner_text)
    
    # Send winner announcement to channel (without eligibility info)
    try:
        channel_text = winner_text.replace(eligibility_info, "")  # Remove eligibility stats for channel announcement
        await bot.send_message(CHANNEL_ID, channel_text)
    except Exception as e:
        await callback.message.answer(f"Помилка при відправці повідомлення в канал: {str(e)}")

@router.callback_query(F.data.startswith("cancel_draw:"))
async def callback_cancel_draw(callback: CallbackQuery):
    """Handle callback to cancel a draw"""
    # Check if user is admin
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас немає прав для цієї дії.")
        return
    
    # Get the draw ID from callback data
    draw_id = int(callback.data.split(":")[1])
    
    # Cancel the draw
    success = await cancel_draw(draw_id)
    
    if not success:
        await callback.answer("Не вдалося скасувати розіграш.")
        await callback.message.answer("❌ Помилка: розіграш не знайдено або вже завершений.")
        return
    
    await callback.answer("Розіграш успішно скасовано!")
    await callback.message.answer(f"❌ Розіграш #{draw_id} скасовано.")
    
    # Announce in the channel
    try:
        draw_details = await get_draw_details(draw_id)
        if draw_details:
            await bot.send_message(
                CHANNEL_ID,
                f"❌ <b>Розіграш '{draw_details['name']}' скасовано.</b>\n\n"
                f"Наступний розіграш буде оголошено незабаром!"
            )
    except Exception as e:
        await callback.message.answer(f"Помилка при відправці повідомлення в канал: {str(e)}")

@router.message(Command("draw"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_draw(message: Message):
    """Handle /draw command - manual draw (legacy support)"""
    # Parse command arguments
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    prize = " ".join(args) if args else "Приз"
    
    # Create draw and immediately end it
    draw_result = await create_draw("Моментальний розіграш", prize, 0)
    result = await end_draw(draw_result["id"])
    
    if not result or "message" in result:
        await message.answer("Немає учасників з квитками для проведення розіграшу.")
        return
    
    # Format winner announcement
    win_chance_formatted = f"{result['win_chance']:.2f}%"
    
    winner_text = (
        f"🎉 <b>Переможець розіграшу</b>: "
        f"{'@' + result['winner_username'] if result['winner_username'] else 'Учасник'}\n"
        f"🆔 ID: <code>{result['winner_id']}</code>\n"
        f"🎟 Кількість квитків: <b>{result['winner_tickets']}</b>\n"
        f"🎯 Шанс на перемогу: <b>{win_chance_formatted}</b>\n"
        f"🏆 Загальна кількість квитків: <b>{result['total_tickets']}</b>\n\n"
        f"🎁 Приз: <b>{result['prize']}</b>"
    )
    
    # Send winner announcement to admin
    await message.answer(winner_text)
    
    # Send winner announcement to channel
    try:
        await bot.send_message(CHANNEL_ID, winner_text)
    except Exception as e:
        await message.answer(f"Помилка при відправці повідомлення в канал: {str(e)}")

@router.message(Command("verify"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_verify_members(message: Message):
    """Handle /verify command - check channel membership of all users with tickets"""
    # Notify admin that this might take some time
    processing_msg = await message.answer("⏳ Перевіряємо учасників... Це може зайняти деякий час.")
    
    session = get_session()
    
    # Get all users with tickets
    users_with_tickets = session.query(User).filter(User.ticket_count > 0).all()
    
    if not users_with_tickets:
        await processing_msg.edit_text("В базі даних немає користувачів з квитками.")
        return
    
    # Check channel membership for each user
    total_users = len(users_with_tickets)
    active_members = 0
    non_members = 0
    
    for user in users_with_tickets:
        is_member = await check_channel_membership(user.id)
        if is_member:
            active_members += 1
        else:
            non_members += 1
    
    # Prepare report
    report = (
        f"📊 <b>Звіт про учасників:</b>\n\n"
        f"👥 Загальна кількість користувачів з квитками: <b>{total_users}</b>\n"
        f"✅ Активні учасники каналу: <b>{active_members}</b>\n"
        f"❌ Неактивні (вийшли з каналу): <b>{non_members}</b>\n\n"
        f"📊 Відсоток активних учасників: <b>{active_members/total_users*100:.2f}%</b>"
    )
    
    await processing_msg.edit_text(report)