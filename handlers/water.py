"""Обработчики для контроля воды."""
import logging
from datetime import date
from collections import defaultdict
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.user_states import WaterStates
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


@router.message(lambda m: m.text == "💧 Контроль воды")
async def water(message: Message):
    """Показывает меню контроля воды."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened water menu")
    
    today = date.today()
    daily_total = WaterRepository.get_daily_total(user_id, today)
    recommended = get_water_recommended(user_id)
    
    progress = round((daily_total / recommended) * 100) if recommended > 0 else 0
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


@router.message(lambda m: m.text == "💧 +250 мл")
async def quick_add_water_250(message: Message, state: FSMContext):
    """Быстро добавляет 250 мл воды одной кнопкой из главного меню."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} used quick water +250 button")
    
    # Сбрасываем состояние, если пользователь был в каком-то другом шаге
    await state.clear()
    
    entry_date = date.today()
    amount = 250.0
    WaterRepository.save_water_entry(user_id, amount, entry_date)
    
    daily_total = WaterRepository.get_daily_total(user_id, entry_date)
    recommended = get_water_recommended(user_id)
    progress = round((daily_total / recommended) * 100) if recommended > 0 else 0
    bar = build_water_progress_bar(daily_total, recommended)
    
    text = (
        f"✅ Добавил {amount:.0f} мл воды\n\n"
        f"💧 Всего за сегодня: {daily_total:.0f} мл\n"
        f"🎯 Норма: {recommended:.0f} мл\n"
        f"📈 Прогресс: {progress}%\n"
        f"{bar}"
    )
    
    await message.answer(text)


@router.callback_query(lambda c: c.data == "quick_water_250")
async def quick_add_water_250_cb(callback: CallbackQuery, state: FSMContext):
    """Быстро добавляет 250 мл воды по inline-кнопке под текстом."""
    await callback.answer()
    message = callback.message
    user_id = str(callback.from_user.id)
    logger.info(f"User {user_id} used quick water +250 inline button")
    
    await state.clear()
    
    entry_date = date.today()
    amount = 250.0
    WaterRepository.save_water_entry(user_id, amount, entry_date)
    
    daily_total = WaterRepository.get_daily_total(user_id, entry_date)
    recommended = get_water_recommended(user_id)
    progress = round((daily_total / recommended) * 100) if recommended > 0 else 0
    bar = build_water_progress_bar(daily_total, recommended)
    
    text = (
        f"✅ Добавил {amount:.0f} мл воды\n\n"
        f"💧 Всего за сегодня: {daily_total:.0f} мл\n"
        f"🎯 Норма: {recommended:.0f} мл\n"
        f"📈 Прогресс: {progress}%\n"
        f"{bar}"
    )
    
    await message.answer(text)


@router.message(lambda m: m.text == "➕ Добавить воду")
async def add_water(message: Message, state: FSMContext):
    """Обработчик добавления воды."""
    reset_user_state(message)
    
    await state.set_state(WaterStates.entering_amount)
    push_menu_stack(message.bot, water_amount_menu)
    await message.answer(
        "💧 Добавление воды\n\n"
        "Напиши количество воды в миллилитрах или выбери из предложенных.",
        reply_markup=water_amount_menu,
    )


@router.message(lambda m: m.text == "📊 Статистика за сегодня")
async def water_today(message: Message):
    """Показывает статистику воды за сегодня."""
    reset_user_state(message)
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
    progress = round((daily_total / recommended) * 100) if recommended > 0 else 0
    lines.append(f"📈 Прогресс: {progress}%")
    
    bar = build_water_progress_bar(daily_total, recommended)
    lines.append(f"\n{bar}")
    
    push_menu_stack(message.bot, water_menu)
    await message.answer("\n".join(lines), reply_markup=water_menu)


@router.message(lambda m: m.text == "📆 История")
async def water_history(message: Message):
    """Показывает историю воды."""
    reset_user_state(message)
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


@router.message(WaterStates.entering_amount)
async def process_water_amount(message: Message, state: FSMContext):
    """Обрабатывает ввод количества воды."""
    user_id = str(message.from_user.id)
    text = message.text.strip()
    
    # Проверяем, не является ли это кнопкой меню
    if text in ["⬅️ Назад", "🏠 Главное меню", "📊 Статистика за сегодня", "📆 История", "➕ Добавить воду"]:
        await state.clear()
        if text == "⬅️ Назад":
            # Возвращаемся в меню воды
            await water(message)
        return
    
    try:
        amount = float(text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer(
            "Пожалуйста, введи число (количество миллилитров) или выбери из предложенных.",
            reply_markup=water_amount_menu,
        )
        return
    
    entry_date = date.today()
    WaterRepository.save_water_entry(user_id, amount, entry_date)
    
    await state.clear()
    
    daily_total = WaterRepository.get_daily_total(user_id, entry_date)
    
    push_menu_stack(message.bot, water_menu)
    await message.answer(
        f"✅ Добавил {amount:.0f} мл воды\n\n"
        f"💧 Всего за сегодня: {daily_total:.0f} мл",
        reply_markup=water_menu,
    )


def register_water_handlers(dp):
    """Регистрирует обработчики воды."""
    dp.include_router(router)
