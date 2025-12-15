"""Обработчики для контроля воды."""
import logging
from datetime import date
from collections import defaultdict
from aiogram import Router
from aiogram.types import Message
from utils.keyboards import water_menu, water_amount_menu, push_menu_stack, main_menu_button
from utils.progress_formatters import build_water_progress_bar
from database.repositories import WaterRepository, WeightRepository

logger = logging.getLogger(__name__)

router = Router()


def reset_user_state(message: Message, *, keep_supplements: bool = False):
    """Сбрасывает состояние пользователя (упрощённая версия)."""
    # TODO: Заменить на FSM состояния
    pass


def get_water_recommended(user_id: str) -> float:
    """Получает рекомендуемую норму воды для пользователя."""
    weight = WeightRepository.get_last_weight(user_id)
    if weight and weight > 0:
        # Формула: вес (кг) × 32.5 мл
        return weight * 32.5
    # Стандартное значение, если вес не указан
    return 2000.0


def build_water_progress_bar(current: float, target: float, length: int = 10) -> str:
    """Строит прогресс-бар для воды."""
    if target <= 0:
        return "░" * length
    
    filled = int((current / target) * length)
    filled = min(filled, length)
    return "█" * filled + "░" * (length - filled)


@router.message(lambda m: m.text == "💧 Контроль воды")
async def water(message: Message):
    """Показывает меню контроля воды."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    message.bot.water_menu_open = True
    logger.info(f"User {user_id} opened water menu")
    
    today = date.today()
    daily_total = WaterRepository.get_daily_total(user_id, today)
    recommended = get_water_recommended(user_id)
    
    progress = min(100, int((daily_total / recommended) * 100)) if recommended > 0 else 0
    bar = build_water_progress_bar(daily_total, recommended)
    
    weight = WeightRepository.get_last_weight(user_id)
    norm_info = ""
    if weight and weight > 0:
        norm_info = f"\n📊 Норма рассчитана по твоему весу ({weight:.1f} кг): {weight:.1f} × 32.5 мл = {recommended:.0f} мл"
    else:
        norm_info = "\n📊 Норма рассчитана по среднему значению (2000 мл). Укажи свой вес в разделе «⚖️ Вес и замеры», чтобы получить персональную норму."
    
    intro_text = (
        "💧 Контроль воды\n\n"
        f"Выпито сегодня: {daily_total:.0f} мл\n"
        f"Рекомендуемая норма: {recommended:.0f} мл\n"
        f"Прогресс: {progress}%\n"
        f"{bar}"
        f"{norm_info}\n\n"
        "Отслеживай количество выпитой воды в течение дня."
    )
    
    push_menu_stack(message.bot, water_menu)
    await message.answer(intro_text, reply_markup=water_menu)


@router.message(lambda m: m.text == "➕ Добавить воду" and getattr(m.bot, "water_menu_open", False))
async def add_water(message: Message):
    """Обработчик добавления воды."""
    reset_user_state(message)
    message.bot.water_menu_open = True
    message.bot.expecting_water_amount = True
    
    push_menu_stack(message.bot, water_amount_menu)
    await message.answer(
        "💧 Добавление воды\n\n"
        "Напиши количество воды в миллилитрах или выбери из предложенных.",
        reply_markup=water_amount_menu,
    )


@router.message(lambda m: m.text == "📊 Статистика за сегодня" and getattr(m.bot, "water_menu_open", False))
async def water_today(message: Message):
    """Показывает статистику воды за сегодня."""
    reset_user_state(message)
    message.bot.water_menu_open = True
    user_id = str(message.from_user.id)
    today = date.today()
    entries = WaterRepository.get_entries_for_day(user_id, today)
    daily_total = WaterRepository.get_daily_total(user_id, today)
    recommended = get_water_recommended(user_id)
    
    if not entries:
        push_menu_stack(message.bot, water_menu)
        await message.answer(
            "💧 Сегодня воды ещё не добавлено.\n\n"
            "Используй кнопку «➕ Добавить воду» для записи.",
            reply_markup=water_menu,
        )
        return
    
    lines = [f"💧 Вода за {today.strftime('%d.%m.%Y')}:\n"]
    for i, entry in enumerate(entries, 1):
        time_str = entry.timestamp.strftime("%H:%M") if entry.timestamp else ""
        lines.append(f"{i}. {entry.amount:.0f} мл {time_str}")
    
    lines.append(f"\n📊 Итого: {daily_total:.0f} мл")
    lines.append(f"🎯 Норма: {recommended} мл")
    progress = min(100, int((daily_total / recommended) * 100))
    lines.append(f"📈 Прогресс: {progress}%")
    
    bar = build_water_progress_bar(daily_total, recommended)
    lines.append(f"\n{bar}")
    
    push_menu_stack(message.bot, water_menu)
    await message.answer("\n".join(lines), reply_markup=water_menu)


@router.message(lambda m: m.text == "📆 История" and getattr(m.bot, "water_menu_open", False))
async def water_history(message: Message):
    """Показывает историю воды."""
    reset_user_state(message)
    message.bot.water_menu_open = True
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} viewed water history")
    
    entries = WaterRepository.get_recent_entries(user_id, limit=7)
    
    if not entries:
        push_menu_stack(message.bot, water_menu)
        await message.answer(
            "💧 История пуста.\n\nНачни отслеживать воду прямо сейчас!",
            reply_markup=water_menu,
        )
        return
    
    # Группируем по дням
    daily_totals = defaultdict(float)
    for entry in entries:
        daily_totals[entry.date] += entry.amount
    
    lines = ["💧 История (последние дни):\n"]
    for day, total in sorted(daily_totals.items(), reverse=True):
        day_str = day.strftime("%d.%m.%Y")
        lines.append(f"{day_str}: {total:.0f} мл")
    
    push_menu_stack(message.bot, water_menu)
    await message.answer("\n".join(lines), reply_markup=water_menu)


# TODO: Добавить обработчик для ввода количества воды
# Это будет сделано при полном переносе функционала


def register_water_handlers(dp):
    """Регистрирует обработчики воды."""
    dp.include_router(router)
