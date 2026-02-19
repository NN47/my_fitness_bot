"""Общие обработчики (назад, главное меню и т.д.)."""
import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from utils.keyboards import main_menu, push_menu_stack, quick_actions_inline

logger = logging.getLogger(__name__)

router = Router()


@router.message(lambda m: m.text == "🏠 Главное меню")
async def go_main_menu(message: Message, state: FSMContext):
    """Обработчик кнопки 'Главное меню'."""
    from datetime import date
    from utils.progress_formatters import (
        format_progress_block,
        format_water_progress_block,
        format_today_workouts_block,
    )
    
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} navigated to main menu")
    
    # Очищаем FSM состояние
    await state.clear()
    
    # Формируем сообщение с прогрессом
    progress_text = format_progress_block(user_id)
    water_progress_text = format_water_progress_block(user_id)
    workouts_text = format_today_workouts_block(user_id, include_date=False)
    today_line = f"📅 <b>{date.today().strftime('%d.%m.%Y')}</b>"
    
    welcome_text = f"{today_line}\n\n{progress_text}\n\n{water_progress_text}\n\n{workouts_text}"
    
    push_menu_stack(message.bot, main_menu)
    # Сначала отправляем текст с кратким днёвным статусом и inline-кнопками быстрых действий
    await message.answer(welcome_text, reply_markup=quick_actions_inline, parse_mode="HTML")
    # Затем — отдельное сообщение с основной клавиатурой
    await message.answer("⬇️ Главное меню", reply_markup=main_menu)


@router.message(lambda m: m.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext):
    """Обработчик кнопки 'Назад' - возвращает на шаг назад."""
    logger.info(f"User {message.from_user.id} pressed back button")
    
    stack = getattr(message.bot, "menu_stack", [])
    
    if len(stack) > 1:
        # Убираем текущее меню из стека
        stack.pop()
        prev_menu = stack[-1]  # Берем предыдущее меню
        message.bot.menu_stack = stack
        push_menu_stack(message.bot, prev_menu)
        await message.answer("⬅️ Назад", reply_markup=prev_menu)
    else:
        # Если стек пуст или только главное меню - возвращаемся в главное
        await state.clear()
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


@router.callback_query(lambda c: c.data == "quick_supplements")
async def quick_supplements(callback: CallbackQuery, state: FSMContext):
    """Быстрое открытие меню добавок."""
    await callback.answer()
    # Импортируем обработчик добавок
    from handlers.supplements import supplements
    await supplements(callback.message, state)


@router.callback_query(lambda c: c.data == "quick_weight")
async def quick_weight(callback: CallbackQuery, state: FSMContext):
    """Быстрое открытие меню веса и замеров."""
    await callback.answer()
    # Импортируем обработчик веса
    from handlers.weight import weight_and_measurements
    await weight_and_measurements(callback.message)


@router.callback_query(lambda c: c.data == "quick_recommendations")
async def quick_recommendations(callback: CallbackQuery):
    """Быстрое открытие меню рекомендаций (ИИ анализ)."""
    await callback.answer()
    from handlers.activity import analyze_activity
    await analyze_activity(callback.message)


def register_common_handlers(dp):
    """Регистрирует общие обработчики."""
    dp.include_router(router)
