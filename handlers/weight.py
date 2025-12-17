"""Обработчики для веса и замеров."""
import logging
from datetime import date, timedelta, datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.keyboards import push_menu_stack, main_menu_button
from database.repositories import WeightRepository
from states.user_states import WeightStates
from utils.validators import parse_weight, parse_date

logger = logging.getLogger(__name__)

router = Router()

# Меню для веса и замеров
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

weight_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить вес")],
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


@router.message(lambda m: m.text == "➕ Добавить вес")
async def add_weight_start(message: Message, state: FSMContext):
    """Начинает процесс добавления веса."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} started adding weight")
    
    await state.set_state(WeightStates.choosing_date_for_weight)
    
    push_menu_stack(message.bot, training_date_menu)
    await message.answer(
        "За какой день добавить вес?\n\n"
        "📅 Сегодня\n"
        "📆 Другой день",
        reply_markup=training_date_menu,
    )


@router.message(WeightStates.choosing_date_for_weight)
async def handle_weight_date_choice(message: Message, state: FSMContext):
    """Обрабатывает выбор даты для веса."""
    if message.text == "📅 Сегодня":
        target_date = date.today()
    elif message.text == "📆 Другой день":
        from utils.keyboards import other_day_menu
        push_menu_stack(message.bot, other_day_menu)
        await message.answer(
            "Выбери день или введи дату вручную:",
            reply_markup=other_day_menu,
        )
        return
    elif message.text == "📅 Вчера":
        target_date = date.today() - timedelta(days=1)
    elif message.text == "📆 Позавчера":
        target_date = date.today() - timedelta(days=2)
    elif message.text == "✏️ Ввести дату вручную":
        await state.set_state(WeightStates.entering_weight)
        await message.answer("Введи дату в формате ДД.ММ.ГГГГ:")
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
    await state.set_state(WeightStates.entering_weight)
    await message.answer(f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n\nВведи свой вес в килограммах (например: 72.5):")


@router.message(WeightStates.entering_weight)
async def handle_weight_input(message: Message, state: FSMContext):
    """Обрабатывает ввод веса."""
    user_id = str(message.from_user.id)
    
    weight_value = parse_weight(message.text)
    if weight_value is None or weight_value <= 0:
        await message.answer("⚠️ Введи положительное число (например: 72.5 или 72,5)")
        return
    
    data = await state.get_data()
    entry_date_str = data.get("entry_date", date.today().isoformat())
    
    if isinstance(entry_date_str, str):
        try:
            entry_date = date.fromisoformat(entry_date_str)
        except ValueError:
            parsed = parse_date(entry_date_str)
            entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
    else:
        entry_date = date.today()
    
    # Сохраняем вес
    WeightRepository.save_weight(user_id, str(weight_value), entry_date)
    logger.info(f"User {user_id} saved weight: {weight_value} kg on {entry_date}")
    
    await state.clear()
    push_menu_stack(message.bot, weight_menu)
    await message.answer(
        f"✅ Вес сохранён!\n\n"
        f"⚖️ {weight_value:.1f} кг\n"
        f"📅 {entry_date.strftime('%d.%m.%Y')}",
        reply_markup=weight_menu,
    )


@router.message(lambda m: m.text == "🗑 Удалить вес")
async def delete_weight_start(message: Message, state: FSMContext):
    """Начинает процесс удаления веса."""
    user_id = str(message.from_user.id)
    weights = WeightRepository.get_weights(user_id)
    
    if not weights:
        push_menu_stack(message.bot, weight_menu)
        await message.answer("⚖️ У тебя нет записей веса для удаления.", reply_markup=weight_menu)
        return
    
    # Сохраняем веса в FSM для выбора
    await state.update_data(weights_to_delete=[{"id": w.id, "date": w.date.isoformat(), "value": w.value} for w in weights])
    await state.set_state(WeightStates.choosing_period)
    
    text = "Выбери номер веса для удаления:\n\n"
    for i, w in enumerate(weights, 1):
        text += f"{i}. {w.date.strftime('%d.%m.%Y')} — {w.value} кг\n"
    
    await message.answer(text)


@router.message(WeightStates.choosing_period)
async def handle_weight_delete_choice(message: Message, state: FSMContext):
    """Обрабатывает выбор веса для удаления."""
    user_id = str(message.from_user.id)
    
    try:
        index = int(message.text) - 1
        data = await state.get_data()
        weights_list = data.get("weights_to_delete", [])
        
        if 0 <= index < len(weights_list):
            weight_data = weights_list[index]
            weight_id = weight_data["id"]
            
            success = WeightRepository.delete_weight(weight_id, user_id)
            if success:
                await message.answer(
                    f"✅ Удалил запись: {weight_data['date']} — {weight_data['value']} кг"
                )
            else:
                await message.answer("❌ Не нашёл такую запись в базе.")
        else:
            await message.answer("⚠️ Нет такой записи.")
    except (ValueError, KeyError):
        await message.answer("⚠️ Введи номер записи")
    
    await state.clear()
    push_menu_stack(message.bot, weight_menu)
    await message.answer("Выбери действие:", reply_markup=weight_menu)


@router.message(lambda m: m.text == "➕ Добавить замеры")
async def add_measurements_start(message: Message, state: FSMContext):
    """Начинает процесс добавления замеров."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} started adding measurements")
    
    await state.update_data(entry_date=date.today().isoformat())
    await state.set_state(WeightStates.choosing_date_for_measurements)
    
    push_menu_stack(message.bot, training_date_menu)
    await message.answer(
        "За какой день добавить замеры?\n\n"
        "📅 Сегодня\n"
        "📆 Другой день",
        reply_markup=training_date_menu,
    )


@router.message(WeightStates.choosing_date_for_measurements)
async def handle_measurements_date_choice(message: Message, state: FSMContext):
    """Обрабатывает выбор даты для замеров."""
    if message.text == "📅 Сегодня":
        target_date = date.today()
    elif message.text == "📅 Вчера":
        target_date = date.today() - timedelta(days=1)
    elif message.text == "📆 Позавчера":
        target_date = date.today() - timedelta(days=2)
    elif message.text == "✏️ Ввести дату вручную":
        await state.set_state(WeightStates.entering_measurements)
        await message.answer("Введи дату в формате ДД.ММ.ГГГГ:")
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
    await state.set_state(WeightStates.entering_measurements)
    await message.answer(
        f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n\n"
        "Введи замеры в формате:\n\n"
        "грудь=100, талия=80, руки=35\n\n"
        "Можно указать только нужные параметры."
    )


@router.message(WeightStates.entering_measurements)
async def handle_measurements_input(message: Message, state: FSMContext):
    """Обрабатывает ввод замеров."""
    user_id = str(message.from_user.id)
    raw = message.text
    
    # Проверяем, не дата ли это
    parsed = parse_date(raw)
    if parsed:
        target_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        await state.update_data(entry_date=target_date.isoformat())
        await message.answer(
            f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n\n"
            "Введи замеры в формате:\n\n"
            "грудь=100, талия=80, руки=35"
        )
        return
    
    try:
        # Разбиваем на части: "грудь=100, талия=80, руки=35"
        parts = [p.strip() for p in raw.replace(",", " ").split()]
        if not parts:
            raise ValueError
        
        # Нормализация и маппинг ключей к полям модели
        key_map = {
            "грудь": "chest", "груд": "chest",
            "талия": "waist", "талияю": "waist",
            "бёдра": "hips", "бедра": "hips", "бёдро": "thigh", "бедро": "thigh",
            "руки": "biceps", "бицепс": "biceps", "бицепсы": "biceps",
            "бедро": "thigh"
        }
        
        measurements_mapped = {}
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if not v:
                    continue
                # Заменить запятую на точку для чисел
                val = float(v.replace(",", "."))
                field = key_map.get(k, None)
                if field:
                    measurements_mapped[field] = val
        
        if not measurements_mapped:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("⚠️ Неверный формат. Попробуй так: грудь=100, талия=80, руки=35")
        return
    
    # Сохраняем в базу
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
        WeightRepository.save_measurements(user_id, measurements_mapped, entry_date)
        logger.info(f"User {user_id} saved measurements on {entry_date}")
        
        await state.clear()
        push_menu_stack(message.bot, measurements_menu)
        await message.answer(
            f"✅ Замеры сохранены: {measurements_mapped} ({entry_date.strftime('%d.%m.%Y')})",
            reply_markup=measurements_menu,
        )
    except Exception as e:
        logger.error(f"Error saving measurements: {e}", exc_info=True)
        await message.answer("⚠️ Ошибка при сохранении. Повтори попытку позже.")
        await state.clear()


@router.message(lambda m: m.text == "🗑 Удалить замеры")
async def delete_measurements_start(message: Message, state: FSMContext):
    """Начинает процесс удаления замеров."""
    user_id = str(message.from_user.id)
    measurements = WeightRepository.get_measurements(user_id)
    
    if not measurements:
        push_menu_stack(message.bot, measurements_menu)
        await message.answer("📏 У тебя нет замеров для удаления.", reply_markup=measurements_menu)
        return
    
    # Сохраняем замеры в FSM
    await state.update_data(
        measurements_to_delete=[
            {"id": m.id, "date": m.date.isoformat()} for m in measurements
        ]
    )
    await state.set_state(WeightStates.choosing_period)
    
    text = "Выбери номер замеров для удаления:\n\n"
    for i, m in enumerate(measurements, 1):
        parts = []
        if m.chest:
            parts.append(f"Грудь: {m.chest}")
        if m.waist:
            parts.append(f"Талия: {m.waist}")
        if m.hips:
            parts.append(f"Бёдра: {m.hips}")
        if m.biceps:
            parts.append(f"Бицепс: {m.biceps}")
        if m.thigh:
            parts.append(f"Бедро: {m.thigh}")
        
        summary = ", ".join(parts) if parts else "нет данных"
        text += f"{i}. {m.date.strftime('%d.%m.%Y')} — {summary}\n"
    
    await message.answer(text)


@router.message(WeightStates.choosing_period)
async def handle_measurements_delete_choice(message: Message, state: FSMContext):
    """Обрабатывает выбор замеров для удаления."""
    user_id = str(message.from_user.id)
    
    try:
        index = int(message.text) - 1
        data = await state.get_data()
        measurements_list = data.get("measurements_to_delete", [])
        
        if 0 <= index < len(measurements_list):
            measurement_data = measurements_list[index]
            measurement_id = measurement_data["id"]
            
            success = WeightRepository.delete_measurement(measurement_id, user_id)
            if success:
                await message.answer(
                    f"✅ Удалил замеры от {measurement_data['date']}"
                )
            else:
                await message.answer("❌ Не нашёл такие замеры в базе.")
        else:
            await message.answer("⚠️ Нет такой записи.")
    except (ValueError, KeyError):
        # Если это не число, возможно это выбор веса для удаления
        data = await state.get_data()
        if "weights_to_delete" in data:
            await handle_weight_delete_choice(message, state)
            return
        await message.answer("⚠️ Введи номер записи")
    
    await state.clear()
    push_menu_stack(message.bot, measurements_menu)
    await message.answer("Выбери действие:", reply_markup=measurements_menu)


def register_weight_handlers(dp):
    """Регистрирует обработчики веса и замеров."""
    dp.include_router(router)
