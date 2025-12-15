"""Обработчики для КБЖУ и питания."""
import logging
from aiogram import Router
from aiogram.types import Message
from utils.keyboards import kbju_menu, push_menu_stack

logger = logging.getLogger(__name__)

router = Router()


@router.message(lambda m: m.text == "🍱 КБЖУ")
async def calories(message: Message):
    """Показывает меню КБЖУ."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened KBJU menu")
    
    # Устанавливаем флаг, что меню КБЖУ открыто
    message.bot.kbju_menu_open = True
    
    push_menu_stack(message.bot, kbju_menu)
    await message.answer(
        "🍱 КБЖУ\n\nВыбери действие:",
        reply_markup=kbju_menu,
    )


# TODO: Добавить остальные обработчики КБЖУ
# Это будет сделано при полном переносе функционала


def register_meal_handlers(dp):
    """Регистрирует обработчики КБЖУ."""
    dp.include_router(router)
