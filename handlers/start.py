"""Обработчики команды /start и главного меню."""
import logging
from datetime import date
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from utils.keyboards import main_menu, push_menu_stack, quick_actions_inline
from utils.progress_formatters import (
    format_progress_block,
    format_water_progress_block,
    format_today_workouts_block,
    get_today_summary_text,
)
from database.session import get_db_session
from database.models import User

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def start(message: Message):
    """Обработчик команды /start."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} started the bot")
    is_new_user = False
    
    # Создаём или обновляем пользователя в БД
    with get_db_session() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id)
            session.add(user)
            session.commit()
            logger.info(f"New user {user_id} registered")
            is_new_user = True
    
    # Формируем приветствие с прогрессом
    progress_text = format_progress_block(user_id)
    water_progress_text = format_water_progress_block(user_id)
    workouts_text = format_today_workouts_block(user_id, include_date=False)
    today_line = f"📅 <b>{date.today().strftime('%d.%m.%Y')}</b>"
    
    if is_new_user:
        # Мини-онбординг для новых пользователей
        welcome_intro = (
            "👋 Привет! Я твой фитнес-бот-помощник.\n\n"
            "Что я умею:\n"
            "• следить за КБЖУ и приёмами пищи\n"
            "• учитывать тренировки и расход калорий\n"
            "• помогать контролировать воду и вес\n"
            "• анализировать твою активность с помощью ИИ\n\n"
            "С чего начать прямо сейчас:\n"
            "1️⃣ В разделе «🍱 КБЖУ» задай цель или просто добавь первый приём пищи\n"
            "2️⃣ В «💧 Контроль воды» начни отмечать выпитую воду\n"
            "3️⃣ В «⚖️ Вес / 📏 Замеры» укажи текущий вес для более точных рекомендаций\n"
        )
        welcome_text = (
            f"{today_line}\n\n"
            f"{welcome_intro}\n"
            f"{progress_text}\n\n{water_progress_text}\n\n{workouts_text}"
        )
    else:
        # Для существующих пользователей показываем краткий дайджест
        try:
            summary_text = get_today_summary_text(user_id)
        except Exception:
            summary_text = ""
        if summary_text:
            welcome_text = (
                f"{today_line}\n\n"
                f"{summary_text}\n\n"
                f"{progress_text}\n\n{water_progress_text}\n\n{workouts_text}"
            )
        else:
            welcome_text = (
                f"{today_line}\n\n"
                f"{progress_text}\n\n{water_progress_text}\n\n{workouts_text}"
            )
    
    push_menu_stack(message.bot, main_menu)
    # Сначала отправляем основной текст с inline-кнопками быстрых действий
    try:
        await message.answer(welcome_text, reply_markup=quick_actions_inline, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to send start summary for user %s", user_id)
    # Отдельным сообщением показываем главное меню (reply-клавиатура) без уведомления
    await message.answer("⬇️ Главное меню", reply_markup=main_menu, disable_notification=True)


def register_start_handlers(dp):
    """Регистрирует обработчики команды /start."""
    dp.include_router(router)
