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
    days_menu,
    duration_menu,
    time_first_menu,
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
async def supplements_list_view(message: Message, state: FSMContext):
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
    
    await state.set_state(SupplementStates.viewing_history)
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


def format_supplement_history_lines(sup: dict) -> list[str]:
    """Форматирует историю приёма добавки."""
    history = sup.get("history", [])
    if not history:
        return ["Отметок пока нет."]
    
    def normalize_entry(entry):
        """Нормализует запись истории."""
        if isinstance(entry, dict):
            ts = entry.get("timestamp")
            if isinstance(ts, datetime):
                return ts
            elif isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    return None
        return None
    
    sorted_history = sorted(
        history,
        key=lambda entry: normalize_entry(entry) or datetime.min,
        reverse=True,
    )
    
    lines: list[str] = []
    for entry in sorted_history:
        ts = normalize_entry(entry)
        if not ts:
            continue
        amount = entry.get("amount") if isinstance(entry, dict) else None
        amount_text = f" — {amount}" if amount is not None else ""
        lines.append(f"{ts.strftime('%d.%m.%Y %H:%M')}{amount_text}")
    
    return lines or ["Отметок пока нет."]


async def show_supplement_details(message: Message, sup: dict, index: int):
    """Показывает детали добавки."""
    history_lines = format_supplement_history_lines(sup)
    
    lines = [f"💊 {sup.get('name', 'Добавка')}", "", "Отметки:"]
    lines.extend([f"• {item}" for item in history_lines])
    
    push_menu_stack(message.bot, supplement_details_menu())
    await message.answer("\n".join(lines), reply_markup=supplement_details_menu())


@router.message(SupplementStates.viewing_history)
async def choose_supplement_for_view(message: Message, state: FSMContext):
    """Обрабатывает выбор добавки для просмотра."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    # Проверяем, не является ли это кнопкой меню
    menu_buttons = ["⬅️ Назад", "🏠 Главное меню"]
    if message.text in menu_buttons:
        await state.clear()
        if message.text == "⬅️ Назад":
            await supplements_list_view(message, state)
        return
    
    target_index = next(
        (idx for idx, item in enumerate(supplements_list) if item["name"].lower() == message.text.lower()),
        None,
    )
    
    if target_index is None:
        await message.answer("Не нашёл такую добавку. Выбери название из списка.")
        return
    
    await state.update_data(viewing_index=target_index)
    await show_supplement_details(message, supplements_list[target_index], target_index)
    await state.set_state(SupplementStates.viewing_history)  # Сохраняем состояние просмотра


@router.message(lambda m: m.text == "✏️ Редактировать добавку")
async def edit_supplement_start(message: Message, state: FSMContext):
    """Начинает процесс редактирования добавки."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    # Проверяем, есть ли текущий просмотр
    data = await state.get_data()
    viewing_index = data.get("viewing_index")
    
    if viewing_index is not None and 0 <= viewing_index < len(supplements_list):
        selected = supplements_list[viewing_index]
        await state.update_data(
            supplement_id=selected.get("id"),
            name=selected.get("name", ""),
            times=selected.get("times", []).copy(),
            days=selected.get("days", []).copy(),
            duration=selected.get("duration", "постоянно"),
            notifications_enabled=selected.get("notifications_enabled", True),
            editing_index=viewing_index,
        )
        await state.set_state(SupplementStates.editing_supplement)
        push_menu_stack(message.bot, supplement_edit_menu(show_save=True))
        await message.answer(
            f"Редактирование: {selected.get('name', 'Добавка')}\n\n"
            f"⏰ Время: {', '.join(selected.get('times', [])) or 'не выбрано'}\n"
            f"📅 Дни: {', '.join(selected.get('days', [])) or 'не выбрано'}\n"
            f"⏳ Длительность: {selected.get('duration', 'постоянно')}",
            reply_markup=supplement_edit_menu(show_save=True),
        )
        return
    
    # Если нет текущего просмотра, показываем список для выбора
    if not supplements_list:
        push_menu_stack(message.bot, supplements_main_menu(has_items=False))
        await message.answer(
            "Пока нет добавок для редактирования.",
            reply_markup=supplements_main_menu(has_items=False),
        )
        return
    
    await state.set_state(SupplementStates.editing_supplement)
    push_menu_stack(message.bot, supplements_choice_menu(supplements_list))
    await message.answer(
        "Выбери добавку, которую нужно отредактировать:",
        reply_markup=supplements_choice_menu(supplements_list),
    )


@router.message(SupplementStates.editing_supplement)
async def choose_supplement_to_edit(message: Message, state: FSMContext):
    """Обрабатывает выбор добавки для редактирования."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    # Проверяем, не является ли это кнопкой меню
    menu_buttons = ["⬅️ Назад", "🏠 Главное меню", "💾 Сохранить"]
    if message.text in menu_buttons:
        if message.text == "💾 Сохранить":
            # Сохранение обрабатывается отдельным обработчиком
            return
        await state.clear()
        if message.text == "⬅️ Назад":
            await supplements_list_view(message, state)
        return
    
    target_index = next(
        (idx for idx, item in enumerate(supplements_list) if item["name"].lower() == message.text.lower()),
        None,
    )
    
    if target_index is None:
        await message.answer("Не нашёл такую добавку. Выбери название из списка.")
        return
    
    selected = supplements_list[target_index]
    await state.update_data(
        supplement_id=selected.get("id"),
        name=selected.get("name", ""),
        times=selected.get("times", []).copy(),
        days=selected.get("days", []).copy(),
        duration=selected.get("duration", "постоянно"),
        notifications_enabled=selected.get("notifications_enabled", True),
        editing_index=target_index,
    )
    
    push_menu_stack(message.bot, supplement_edit_menu(show_save=True))
    await message.answer(
        f"Редактирование: {selected.get('name', 'Добавка')}\n\n"
        f"⏰ Время: {', '.join(selected.get('times', [])) or 'не выбрано'}\n"
        f"📅 Дни: {', '.join(selected.get('days', [])) or 'не выбрано'}\n"
        f"⏳ Длительность: {selected.get('duration', 'постоянно')}",
        reply_markup=supplement_edit_menu(show_save=True),
    )


@router.message(lambda m: m.text == "🗑 Удалить добавку")
async def delete_supplement(message: Message, state: FSMContext):
    """Удаляет добавку."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    data = await state.get_data()
    viewing_index = data.get("viewing_index")
    
    if viewing_index is None or viewing_index >= len(supplements_list):
        await message.answer("Сначала выбери добавку в списке 'Мои добавки'.")
        return
    
    target = supplements_list[viewing_index]
    supplement_id = target.get("id")
    
    if supplement_id:
        success = SupplementRepository.delete_supplement(user_id, supplement_id)
        if success:
            await message.answer(f"🗑 Добавка {target.get('name', 'без названия')} удалена.")
            await state.clear()
            await supplements_list_view(message, state)
        else:
            await message.answer("❌ Не удалось удалить добавку. Попробуйте позже.")
    else:
        await message.answer("❌ Не найдена добавка для удаления.")


@router.message(lambda m: m.text == "✅ Отметить добавку")
async def mark_supplement_from_details(message: Message, state: FSMContext):
    """Отмечает приём добавки из деталей."""
    user_id = str(message.from_user.id)
    supplements_list = SupplementRepository.get_supplements(user_id)
    
    data = await state.get_data()
    viewing_index = data.get("viewing_index")
    
    if viewing_index is None or viewing_index >= len(supplements_list):
        push_menu_stack(message.bot, supplements_main_menu(has_items=bool(supplements_list)))
        await message.answer(
            "Сначала выбери добавку в списке 'Мои добавки'.",
            reply_markup=supplements_main_menu(has_items=bool(supplements_list)),
        )
        return
    
    target = supplements_list[viewing_index]
    await state.update_data(supplement_name=target.get("name", ""), supplement_id=target.get("id"))
    await state.set_state(SupplementStates.choosing_date_for_intake)
    
    push_menu_stack(message.bot, training_date_menu)
    await message.answer(
        "За какой день отметить приём?\n\n📅 Сегодня\n📆 Другой день",
        reply_markup=training_date_menu,
    )


@router.message(lambda m: m.text == "💾 Сохранить")
async def save_supplement(message: Message, state: FSMContext):
    """Сохраняет добавку."""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    
    name = data.get("name", "").strip()
    if not name:
        await message.answer("Пожалуйста, укажите название добавки перед сохранением.")
        return
    
    supplement_payload = {
        "name": name,
        "times": data.get("times", []).copy(),
        "days": data.get("days", []).copy(),
        "duration": data.get("duration", "постоянно"),
        "notifications_enabled": data.get("notifications_enabled", True),
    }
    
    supplement_id = data.get("supplement_id")
    saved_id = SupplementRepository.save_supplement(user_id, supplement_payload, supplement_id)
    
    if saved_id:
        await state.clear()
        notifications_status = "включены" if supplement_payload.get("notifications_enabled", True) else "выключены"
        push_menu_stack(message.bot, supplements_main_menu(has_items=True))
        await message.answer(
            "✅ Добавка сохранена!\n\n"
            f"💊 {supplement_payload['name']} \n"
            f"⏰ Время приема: {', '.join(supplement_payload['times']) or 'не выбрано'}\n"
            f"📅 Дни приема: {', '.join(supplement_payload['days']) or 'не выбрано'}\n"
            f"⏳ Длительность: {supplement_payload['duration']}\n"
            f"🔔 Уведомления: {notifications_status}",
            reply_markup=supplements_main_menu(has_items=True),
        )
    else:
        await message.answer("❌ Не удалось сохранить добавку. Попробуйте позже.")


@router.message(lambda m: m.text == "✏️ Редактировать время")
async def edit_supplement_time(message: Message, state: FSMContext):
    """Начинает редактирование времени приёма."""
    data = await state.get_data()
    times = data.get("times", [])
    
    await state.set_state(SupplementStates.entering_time)
    if times:
        push_menu_stack(message.bot, time_edit_menu(times))
        times_list = "\n".join(times)
        await message.answer(
            f"Текущее расписание:\n{times_list}\n\nℹ️ Нажмите ❌ чтобы удалить время",
            reply_markup=time_edit_menu(times),
        )
    else:
        push_menu_stack(message.bot, time_first_menu())
        await message.answer(
            f"ℹ️ Добавьте первое время приема",
            reply_markup=time_first_menu(),
        )


@router.message(SupplementStates.entering_time)
async def handle_time_value(message: Message, state: FSMContext):
    """Обрабатывает ввод времени."""
    text = message.text.strip()
    
    # Проверяем, не является ли это кнопкой меню
    menu_buttons = ["⬅️ Назад", "💾 Сохранить", "➕ Добавить"]
    if any(text.startswith(btn) for btn in menu_buttons) or text.startswith("❌"):
        if text.startswith("❌"):
            # Удаление времени
            time_value = text.replace("❌ ", "").strip()
            data = await state.get_data()
            times = data.get("times", []).copy()
            if time_value in times:
                times.remove(time_value)
            await state.update_data(times=times)
            if times:
                push_menu_stack(message.bot, time_edit_menu(times))
                times_list = "\n".join(times)
                await message.answer(
                    f"Обновленное расписание:\n{times_list}",
                    reply_markup=time_edit_menu(times),
                )
            else:
                push_menu_stack(message.bot, time_first_menu())
                await message.answer(
                    "Расписание очищено. Добавьте время.",
                    reply_markup=time_first_menu(),
                )
        return
    
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", text):
        await message.answer("Пожалуйста, укажите время в формате ЧЧ:ММ. Например: 09:00")
        return
    
    data = await state.get_data()
    times = data.get("times", []).copy()
    if text not in times:
        times.append(text)
    times.sort()
    
    await state.update_data(times=times)
    push_menu_stack(message.bot, time_edit_menu(times))
    times_list = "\n".join(times)
    await message.answer(
        f"💊 {data.get('name', 'Добавка')}\n\nРасписание приема:\n{times_list}\n\nℹ️ Нажмите ❌ чтобы удалить время",
        reply_markup=time_edit_menu(times),
    )


@router.message(lambda m: m.text == "📅 Редактировать дни")
async def edit_days(message: Message, state: FSMContext):
    """Начинает редактирование дней приёма."""
    data = await state.get_data()
    days = data.get("days", [])
    
    await state.set_state(SupplementStates.selecting_days)
    push_menu_stack(message.bot, days_menu(days))
    await message.answer(
        "Выберите дни приема:\nНажмите на день для выбора",
        reply_markup=days_menu(days),
    )


@router.message(SupplementStates.selecting_days)
async def toggle_day(message: Message, state: FSMContext):
    """Переключает выбор дня."""
    if message.text == "Выбрать все":
        await state.update_data(days=["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"])
        data = await state.get_data()
        push_menu_stack(message.bot, days_menu(data.get("days", [])))
        await message.answer("Все дни выбраны", reply_markup=days_menu(data.get("days", [])))
        return
    
    day = message.text.replace("✅ ", "")
    if day not in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        return
    
    data = await state.get_data()
    days = data.get("days", []).copy()
    if day in days:
        days.remove(day)
    else:
        days.append(day)
    
    await state.update_data(days=days)
    push_menu_stack(message.bot, days_menu(days))
    await message.answer("Дни обновлены", reply_markup=days_menu(days))


@router.message(lambda m: m.text == "⏳ Длительность приема")
async def choose_duration(message: Message, state: FSMContext):
    """Показывает меню выбора длительности."""
    push_menu_stack(message.bot, duration_menu())
    await message.answer("Выберите длительность приема", reply_markup=duration_menu())


@router.message(lambda m: m.text in {"Постоянно", "14 дней", "30 дней"})
async def set_duration(message: Message, state: FSMContext):
    """Устанавливает длительность приёма."""
    duration = message.text.lower()
    await state.update_data(duration=duration)
    
    data = await state.get_data()
    push_menu_stack(message.bot, supplement_edit_menu(show_save=True))
    await message.answer(
        f"Длительность установлена: {message.text}\n\n"
        f"💊 {data.get('name', 'Добавка')}\n"
        f"⏰ Время: {', '.join(data.get('times', [])) or 'не выбрано'}\n"
        f"📅 Дни: {', '.join(data.get('days', [])) or 'не выбрано'}\n"
        f"⏳ Длительность: {duration}",
        reply_markup=supplement_edit_menu(show_save=True),
    )


@router.message(lambda m: m.text == "🔔 Уведомления")
async def toggle_notifications(message: Message, state: FSMContext):
    """Переключает уведомления."""
    data = await state.get_data()
    current_status = data.get("notifications_enabled", True)
    new_status = not current_status
    
    await state.update_data(notifications_enabled=new_status)
    
    status_text = "включены" if new_status else "выключены"
    push_menu_stack(message.bot, supplement_edit_menu(show_save=True))
    await message.answer(
        f"🔔 Уведомления {status_text}\n\n"
        f"Уведомления будут приходить в указанное время приема добавки.",
        reply_markup=supplement_edit_menu(show_save=True),
    )


@router.message(lambda m: m.text == "✏️ Изменить название")
async def rename_supplement(message: Message, state: FSMContext):
    """Начинает изменение названия добавки."""
    await state.set_state(SupplementStates.entering_name)
    await message.answer("Введите новое название добавки.")


@router.message(lambda m: m.text == "⬅️ Отменить")
async def cancel_supplement(message: Message, state: FSMContext):
    """Отменяет создание/редактирование добавки."""
    await state.clear()
    await supplements(message)


def register_supplement_handlers(dp):
    """Регистрирует обработчики добавок."""
    dp.include_router(router)
