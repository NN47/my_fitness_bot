"""Обработчики для добавок."""
import logging
import re
import json
from datetime import date, datetime, timedelta
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.keyboards import push_menu_stack, main_menu_button, training_date_menu
from utils.supplement_keyboards import (
    supplements_main_menu,
    supplements_choice_menu,
    supplements_view_menu,
    supplement_details_menu,
    supplement_edit_menu,
    time_edit_menu,
)
from database.repositories import SupplementRepository
from states.user_states import SupplementStates
from utils.validators import parse_date

logger = logging.getLogger(__name__)

router = Router()


def parse_supplement_amount(text: str) -> Optional[float]:
    """Парсит количество добавки из текста."""
    normalized = text.replace(",", ".").strip()
    try:
        return float(normalized)
    except ValueError:
        return None


@router.message(lambda m: m.text == "💊 Добавки")
async def supplements(message: Message):
    """Показывает меню добавок."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened supplements menu")
    
    try:
        supplements_list = SupplementRepository.get_supplements(user_id)
    except Exception as e:
        logger.error(f"Error loading supplements: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке добавок. Попробуйте позже.")
        return
    
    dairi_description = (
        "Привет, это Дайри на связи! 🤖\n\n"
        "💊 Раздел «Добавки»\n\n"
        "Здесь ты можешь записывать свои добавки: лекарства, витамины, БАДы и любые другие препараты. "
        "Я помогу тебе отслеживать их приём, настроить расписание и получать статистику.\n\n"
        "⚠️ Важно: протеин нужно вписывать в раздел КБЖУ, потому что там подсчитывается количество белков "
        "для твоей дневной нормы. Этот раздел предназначен для лекарств и добавок, которые не влияют на калорийность и БЖУ.\n\n"
    )
    
    if not supplements_list:
        push_menu_stack(message.bot, supplements_main_menu(has_items=False))
        await message.answer(
            dairi_description + "Готов начать? Создай свою первую добавку!",
            reply_markup=supplements_main_menu(has_items=False),
        )
        return
    
    # Если добавки есть, показываем описание и список
    lines = [dairi_description + "📋 Твои добавки:\n"]
    for item in supplements_list:
        days = ", ".join(item["days"]) if item["days"] else "не выбрано"
        times = ", ".join(item["times"]) if item["times"] else "не выбрано"
        lines.append(
            f"\n💊 {item['name']} \n⏰ Время приема: {times}\n📅 Дни приема: {days}\n⏳ Длительность: {item['duration']}"
        )
    
    push_menu_stack(message.bot, supplements_main_menu(has_items=True))
    await message.answer("\n".join(lines), reply_markup=supplements_main_menu(has_items=True))


@router.message(lambda m: m.text == "📋 Мои добавки")
async def supplements_list_view(message: Message):
    """Показывает список добавок для просмотра."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    if not supplements_list:
        push_menu_stack(message.bot, supplements_main_menu(has_items=False))
        await message.answer(
            "У тебя пока нет добавок. Создай первую!",
            reply_markup=supplements_main_menu(has_items=False),
        )
        return
    
    push_menu_stack(message.bot, supplements_view_menu(supplements_list))
    await message.answer(
        "Выбери добавку для просмотра:",
        reply_markup=supplements_view_menu(supplements_list),
    )


@router.message(lambda m: m.text == "➕ Создать добавку")
async def start_create_supplement(message: Message, state: FSMContext):
    """Начинает процесс создания добавки."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} started creating supplement")
    
    await state.update_data({
        "supplement_id": None,
        "name": "",
        "times": [],
        "days": [],
        "duration": "постоянно",
        "notifications_enabled": True,
    })
    await state.set_state(SupplementStates.entering_name)
    await message.answer("Введите название добавки.")


@router.message(SupplementStates.entering_name)
async def handle_supplement_name(message: Message, state: FSMContext):
    """Обрабатывает ввод названия добавки."""
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите название добавки.")
        return
    
    await state.update_data(name=name)
    data = await state.get_data()
    
    push_menu_stack(message.bot, supplement_edit_menu(show_save=True))
    await message.answer(
        "Выберите время, дни, длительность приема добавки и уведомления (по желанию):",
        reply_markup=supplement_edit_menu(show_save=True),
    )


@router.message(lambda m: m.text == "✅ Отметить приём")
async def start_log_supplement(message: Message, state: FSMContext):
    """Начинает процесс отметки приёма добавки."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    if not supplements_list:
        push_menu_stack(message.bot, supplements_main_menu(has_items=False))
        await message.answer(
            "Сначала создай добавку, чтобы отмечать приём.",
            reply_markup=supplements_main_menu(has_items=False),
        )
        return
    
    await state.set_state(SupplementStates.logging_intake)
    push_menu_stack(message.bot, supplements_choice_menu(supplements_list))
    await message.answer(
        "Выбери добавку, приём которой нужно отметить:",
        reply_markup=supplements_choice_menu(supplements_list),
    )


@router.message(SupplementStates.logging_intake)
async def log_supplement_intake(message: Message, state: FSMContext):
    """Обрабатывает выбор добавки для отметки приёма."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    target = next(
        (item for item in supplements_list if item["name"].lower() == message.text.lower()),
        None,
    )
    
    if not target:
        await message.answer("Не нашёл такую добавку. Выбери название из списка или вернись назад.")
        return
    
    await state.update_data(supplement_name=target["name"], supplement_id=target["id"])
    await state.set_state(SupplementStates.choosing_date_for_intake)
    
    push_menu_stack(message.bot, training_date_menu)
    await message.answer(
        "За какой день отметить приём?\n\n📅 Сегодня\n📆 Другой день",
        reply_markup=training_date_menu,
    )


@router.message(SupplementStates.choosing_date_for_intake)
async def handle_intake_date_choice(message: Message, state: FSMContext):
    """Обрабатывает выбор даты для приёма добавки."""
    if message.text == "📅 Сегодня":
        target_date = date.today()
    elif message.text == "📅 Вчера":
        target_date = date.today() - timedelta(days=1)
    elif message.text == "📆 Позавчера":
        target_date = date.today() - timedelta(days=2)
    elif message.text == "✏️ Ввести дату вручную":
        await message.answer("Введи дату в формате ДД.ММ.ГГГГ:")
        return
    elif message.text == "📆 Другой день":
        from utils.keyboards import other_day_menu
        push_menu_stack(message.bot, other_day_menu)
        await message.answer(
            "Выбери день или введи дату вручную:",
            reply_markup=other_day_menu,
        )
        return
    else:
        # Проверяем, не дата ли это
        parsed = parse_date(message.text)
        if parsed:
            target_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            await message.answer("Выбери дату из меню или введи в формате ДД.ММ.ГГГГ")
            return
    
    await state.update_data(entry_date=target_date.isoformat())
    await state.set_state(SupplementStates.entering_history_time)
    await message.answer(
        f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n\n"
        "Укажи время приёма в формате ЧЧ:ММ. Например: 09:30"
    )


@router.message(SupplementStates.entering_history_time)
async def handle_history_time(message: Message, state: FSMContext):
    """Обрабатывает ввод времени приёма добавки."""
    time_text = message.text.strip()
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time_text):
        await message.answer("Пожалуйста, укажи время в формате ЧЧ:ММ (например, 08:15)")
        return
    
    data = await state.get_data()
    entry_date_str = data.get("entry_date", date.today().isoformat())
    
    if isinstance(entry_date_str, str):
        try:
            entry_date = date.fromisoformat(entry_date_str)
        except ValueError:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    try:
        time_obj = datetime.strptime(time_text, "%H:%M").time()
        timestamp = datetime.combine(entry_date, time_obj)
        await state.update_data(timestamp=timestamp.isoformat())
        await state.set_state(SupplementStates.entering_history_amount)
        await message.answer("Укажи количество для приёма (например: 1 или 2.5):")
    except ValueError:
        await message.answer("Неверный формат времени. Используй ЧЧ:ММ (например, 09:30)")


@router.message(SupplementStates.entering_history_amount)
async def handle_history_amount(message: Message, state: FSMContext):
    """Обрабатывает ввод количества добавки и сохраняет запись."""
    user_id = str(message.from_user.id)
    amount = parse_supplement_amount(message.text)
    
    if amount is None:
        await message.answer("Пожалуйста, укажи количество числом, например: 1 или 2.5")
        return
    
    data = await state.get_data()
    supplement_id = data.get("supplement_id")
    supplement_name = data.get("supplement_name")
    timestamp_str = data.get("timestamp")
    
    if not supplement_id or not timestamp_str:
        await message.answer("Ошибка: не найдены данные о добавке или времени.")
        await state.clear()
        return
    
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        await message.answer("Ошибка: неверный формат времени.")
        await state.clear()
        return
    
    # Сохраняем запись
    entry_id = SupplementRepository.save_entry(user_id, supplement_id, timestamp, amount)
    
    if entry_id:
        await state.clear()
        push_menu_stack(message.bot, supplements_main_menu(has_items=True))
        await message.answer(
            f"✅ Записал приём {supplement_name} ({amount}) на {timestamp.strftime('%d.%m.%Y %H:%M')}.",
            reply_markup=supplements_main_menu(has_items=True),
        )
    else:
        await message.answer("❌ Не удалось сохранить запись. Попробуйте позже.")
        await state.clear()


def register_supplement_handlers(dp):
    """Регистрирует обработчики добавок."""
    dp.include_router(router)
