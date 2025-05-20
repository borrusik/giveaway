from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from db.database import get_session
from db.models import User
from services.referral import generate_referral_code, create_referral_link, process_referral, get_referral_stats
from config import CHANNEL_ID, CHANNEL_USERNAME
from instance import bot

# Initialize router
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Check if user exists in DB
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    # If user doesn't exist, create new user
    if not user:
        referral_code = generate_referral_code()
        user = User(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referral_code=referral_code
        )
        session.add(user)
        session.commit()
    
    # Check if start has referral code
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    if args:
        # Find user who shared the link
        referrer = session.query(User).filter(User.referral_code == args).first()
        
        if referrer and referrer.id != user_id:
            # First, check if the user has joined the channel
            try:
                member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                status = member.status
                if isinstance(status, str):
                    member_status = status
                else:
                    member_status = status.value
                
                # Only process referral if user has joined the channel
                if member_status not in ['left', 'kicked', 'restricted']:
                    # Process the referral if it's valid
                    user.referred_by_id = referrer.id
                    session.commit()
                    
                    # Update referrer's tickets
                    await process_referral(referrer.id, user_id)
                    
                    await message.answer(
                        f"Вітаємо! Ви приєдналися за запрошенням користувача з ID: {referrer.id}\n"
                        f"Тепер ви можете запрошувати друзів і збільшувати свої шанси на виграш!"
                    )
                else:
                    # User hasn't joined the channel yet
                    invite_link = await bot.export_chat_invite_link(CHANNEL_ID)
                    await message.answer(
                        f"Щоб брати участь у розіграші, потрібно бути підписаним на канал.\n"
                        f"Підпишіться на канал: {invite_link}\n"
                        f"Після підписки натисніть /start {args} знову."
                    )
                    return
            except Exception as e:
                print(f"Error checking channel membership: {e}")
                await message.answer("Сталася помилка при перевірці підписки на канал. Спробуйте пізніше.")
                return
        else:
            await message.answer("Вітаємо в нашому розіграші! Запрошуйте друзів та вигравайте призи!")
    else:
        # Check if user is in the channel
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            status = member.status
            if isinstance(status, str):
                member_status = status
            else:
                member_status = status.value
                
            if member_status in ['left', 'kicked', 'restricted']:
                # User hasn't joined the channel yet
                invite_link = await bot.export_chat_invite_link(CHANNEL_ID)
                await message.answer(
                    f"Щоб брати участь у розіграші, потрібно бути підписаним на канал.\n"
                    f"Підпишіться на канал: {invite_link}\n"
                    f"Після підписки натисніть /start знову."
                )
                return
        except Exception as e:
            print(f"Error checking channel membership: {e}")
    
    # Generate and send the referral link - this creates a link to the BOT with start parameter
    referral_link = create_referral_link(user_id)
    
    await message.answer(
        f"Вітаємо в нашому розіграші!\n\n"
        f"Ваше персональне посилання для запрошення друзів:\n"
        f"<code>{referral_link}</code>\n\n"
        f"Поділіться цим посиланням з друзями. За кожного друга, який приєднається до каналу через ваше посилання, ви отримаєте один квиток для розіграшу!\n\n"
        f"Друг має:\n"
        f"1. Перейти за вашим посиланням\n"
        f"2. Натиснути START в боті\n" 
        f"3. Підписатися на канал: https://t.me/{CHANNEL_USERNAME}\n\n"
        f"Тільки тоді вам буде зараховано запрошення!"
    )

@router.message(Command("me"))
async def cmd_me(message: Message):
    """Handle /me command - show user's statistics"""
    user_id = message.from_user.id
    stats = get_referral_stats(user_id)
    
    if not stats:
        await message.answer("Ви ще не зареєстровані у системі. Використайте команду /start")
        return
    
    await message.answer(
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"🎟 Кількість квитків: <b>{stats['tickets']}</b>\n"
        f"👥 Запрошено друзів: <b>{stats['referrals_count']}</b>\n"
        f"🎯 Ваш шанс на перемогу: <b>{stats['win_chance']}%</b>\n"
        f"🏆 Загальна кількість квитків у розіграші: <b>{stats['total_tickets']}</b>"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        f"<b>📱 Invite2Win Bot - Розіграш за друзів</b>\n\n"
        f"🔹 <b>/start</b> — почати участь та отримати реферальне посилання\n"
        f"🔹 <b>/me</b> — переглянути свою статистику\n"
        f"🔹 <b>/top</b> — переглянути лідерів за запрошеннями\n"
        f"🔹 <b>/help</b> — показати цю довідку\n\n"
        f"📊 <b>Як працює розіграш?</b>\n"
        f"1. Запрошуйте друзів за вашим персональним посиланням\n"
        f"2. За кожного друга ви отримуєте 1 квиток\n"
        f"3. Чим більше квитків — тим більший шанс на перемогу\n"
        f"4. Переможець обирається випадково з урахуванням ваги квитків\n\n"
        f"Підпишіться на наш канал: https://t.me/{CHANNEL_USERNAME}"
    )
    
    await message.answer(help_text)

from services.draw_manager import get_active_draws

@router.message(Command("draws"))
async def cmd_user_draws(message: Message):
    """Handle /draws command - show active draws for users"""
    draws = await get_active_draws()
    
    if not draws:
        await message.answer("На даний момент немає активних розіграшів.")
        return
    
    # Build response
    response = "<b>🎮 Активні розіграші:</b>\n\n"
    
    for draw in draws:
        end_date = draw["end_date"].strftime("%d.%m.%Y %H:%M") if draw["end_date"] else "Не вказано"
        days_left = f"{draw['days_left']} днів" if draw["days_left"] is not None else "Не вказано"
        
        response += (
            f"🏆 <b>{draw['name']}</b>\n"
            f"🎁 Приз: {draw['prize']}\n"
            f"⏳ Залишилось: {days_left}\n"
            f"📅 Закінчення: {end_date}\n\n"
        )
    
    response += "Запрошуйте друзів, щоб збільшити свої шанси на перемогу! Використовуйте /me для перегляду своєї статистики."
    
    await message.answer(response)


from aiogram.types import CallbackQuery
@router.callback_query(lambda c: c.data == "check_join")
async def check_join_callback(callback: CallbackQuery):
    is_member = await check_channel_membership(callback.from_user.id)
    if is_member:
        await callback.message.edit_text("✅ Подписка подтверждена! Теперь вы можете пользоваться ботом.")
    else:
        await callback.answer("Вы всё ещё не подписаны на канал.", show_alert=True)