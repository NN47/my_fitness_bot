"""Обработчики для тренировок."""
import logging
from aiogram import Router
from aiogram.types import Message
from utils.keyboards import training_menu, push_menu_stack

logger = logging.getLogger(__name__)

router = Router()


@router.message(lambda m: m.text == "🏋️ Тренировка")
async def show_training_menu(message: Message):
    """Показывает меню тренировок."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened training menu")
    push_menu_stack(message.bot, training_menu)
    await message.answer(
        "🏋️ Тренировки\n\nВыбери действие:",
        reply_markup=training_menu,
    )


# TODO: Добавить остальные обработчики тренировок
# Это будет сделано при полном переносе функционала


def register_workout_handlers(dp):
    """Регистрирует обработчики тренировок."""
    dp.include_router(router)
