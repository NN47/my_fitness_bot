"""Обработчики команды /start и главного меню."""
import logging
from datetime import date
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from utils.keyboards import main_menu, push_menu_stack
from database.session import get_db_session
from database.models import User

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def start(message: Message):
    """Обработчик команды /start."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} started the bot")
    
    # Создаём или обновляем пользователя в БД
    with get_db_session() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id)
            session.add(user)
            session.commit()
            logger.info(f"New user {user_id} registered")
    
    # TODO: Добавить форматирование прогресса (пока упрощённо)
    welcome_text = (
        f"👋 Привет!\n\n"
        f"📅 <b>{date.today().strftime('%d.%m.%Y')}</b>\n\n"
        f"Добро пожаловать в Fitness Bot! 🏋️\n\n"
        f"Выбери действие из меню:"
    )
    
    push_menu_stack(message.bot, main_menu)
    await message.answer(welcome_text, reply_markup=main_menu, parse_mode="HTML")


def register_start_handlers(dp):
    """Регистрирует обработчики команды /start."""
    dp.include_router(router)
