"""Обработчики для веса и замеров."""
import logging
from datetime import date, timedelta
from aiogram import Router
from aiogram.types import Message
from utils.keyboards import push_menu_stack
from database.repositories import WeightRepository

logger = logging.getLogger(__name__)

router = Router()

# Меню для веса и замеров (временно здесь, потом перенесём в keyboards.py)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.keyboards import main_menu_button

weight_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить вес")],
        [KeyboardButton(text="📊 График")],
        [KeyboardButton(text="🗑 Удалить вес")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

measurements_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить замеры")],
        [KeyboardButton(text="🗑 Удалить замеры")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

weight_and_measurements_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚖️ Вес"), KeyboardButton(text="📏 Замеры")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)


@router.message(lambda m: m.text == "⚖️ Вес / 📏 Замеры")
async def weight_and_measurements(message: Message):
    """Показывает меню веса и замеров."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened weight and measurements menu")
    push_menu_stack(message.bot, weight_and_measurements_menu)
    await message.answer(
        "⚖️ Вес / 📏 Замеры\n\nВыбери действие:",
        reply_markup=weight_and_measurements_menu,
    )


@router.message(lambda m: m.text == "⚖️ Вес")
async def my_weight(message: Message):
    """Показывает историю веса пользователя."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} viewed weight history")
    
    weights = WeightRepository.get_weights(user_id)
    
    if not weights:
        push_menu_stack(message.bot, weight_menu)
        await message.answer("⚖️ У тебя пока нет записей веса.", reply_markup=weight_menu)
        return
    
    text = "📊 История твоего веса:\n\n"
    for i, w in enumerate(weights, 1):
        text += f"{i}. {w.date.strftime('%d.%m.%Y')} — {w.value} кг\n"
    
    push_menu_stack(message.bot, weight_menu)
    await message.answer(text, reply_markup=weight_menu)


@router.message(lambda m: m.text == "📏 Замеры")
async def my_measurements(message: Message):
    """Показывает историю замеров пользователя."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} viewed measurements history")
    
    measurements = WeightRepository.get_measurements(user_id)
    
    if not measurements:
        push_menu_stack(message.bot, measurements_menu)
        await message.answer("📐 У тебя пока нет замеров.", reply_markup=measurements_menu)
        return
    
    text = "📊 История замеров:\n\n"
    for i, m in enumerate(measurements, 1):
        parts = []
        if m.chest:
            parts.append(f"Грудь: {m.chest} см")
        if m.waist:
            parts.append(f"Талия: {m.waist} см")
        if m.hips:
            parts.append(f"Бёдра: {m.hips} см")
        if m.biceps:
            parts.append(f"Бицепс: {m.biceps} см")
        if m.thigh:
            parts.append(f"Бедро: {m.thigh} см")
        
        text += f"{i}. {m.date.strftime('%d.%m.%Y')} — {', '.join(parts)}\n"
    
    push_menu_stack(message.bot, measurements_menu)
    await message.answer(text, reply_markup=measurements_menu)


# TODO: Добавить остальные обработчики (добавление веса, графики, удаление и т.д.)
# Это будет сделано при полном переносе функционала из bot.py


def register_weight_handlers(dp):
    """Регистрирует обработчики веса и замеров."""
    dp.include_router(router)
