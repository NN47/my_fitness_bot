"""Общие обработчики (назад, главное меню и т.д.)."""
import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from utils.keyboards import main_menu, push_menu_stack

logger = logging.getLogger(__name__)

router = Router()


@router.message(lambda m: m.text == "🏠 Главное меню")
async def go_main_menu(message: Message):
    """Обработчик кнопки 'Главное меню'."""
    logger.info(f"User {message.from_user.id} navigated to main menu")
    push_menu_stack(message.bot, main_menu)
    await message.answer("🏠 Главное меню", reply_markup=main_menu)


@router.message(lambda m: m.text == "⬅️ Назад")
async def go_back(message: Message):
    """Обработчик кнопки 'Назад' - возвращает в главное меню."""
    logger.info(f"User {message.from_user.id} pressed back button")
    push_menu_stack(message.bot, main_menu)
    await message.answer("🏠 Главное меню", reply_markup=main_menu)


@router.callback_query(lambda c: c.data == "cal_close")
async def close_calendar(callback: CallbackQuery):
    """Закрывает календарь."""
    await callback.answer()
    await callback.message.delete()


@router.callback_query(lambda c: c.data == "noop")
async def ignore_callback(callback: CallbackQuery):
    """Игнорирует callback без действия."""
    await callback.answer()


def register_common_handlers(dp):
    """Регистрирует общие обработчики."""
    dp.include_router(router)
