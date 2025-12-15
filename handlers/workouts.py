"""Обработчики для тренировок."""
import logging
from datetime import date, timedelta, datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.keyboards import (
    training_menu,
    training_date_menu,
    other_day_menu,
    exercise_category_menu,
    bodyweight_exercise_menu,
    weighted_exercise_menu,
    count_menu,
    bodyweight_exercises,
    weighted_exercises,
    push_menu_stack,
    main_menu_button,
)
from states.user_states import WorkoutStates
from database.repositories import WorkoutRepository
from utils.workout_utils import calculate_workout_calories
from utils.validators import parse_date

logger = logging.getLogger(__name__)

router = Router()


def reset_user_state(message: Message, *, keep_supplements: bool = False):
    """Сбрасывает состояние пользователя."""
    # TODO: Заменить на FSM clear
    pass


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


@router.message(lambda m: m.text == "➕ Добавить тренировку")
async def add_training_entry(message: Message, state: FSMContext):
    """Начинает процесс добавления тренировки."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} started adding workout")
    
    # Для тренировок всегда используем сегодняшнюю дату по умолчанию
    await state.update_data(entry_date=date.today().isoformat())
    await state.set_state(WorkoutStates.choosing_category)
    
    push_menu_stack(message.bot, exercise_category_menu)
    await message.answer(
        "Выбери категорию упражнений:",
        reply_markup=exercise_category_menu,
    )


@router.message(WorkoutStates.choosing_category)
async def choose_category(message: Message, state: FSMContext):
    """Обрабатывает выбор категории упражнений."""
    if message.text == "Со своим весом":
        category = "bodyweight"
        await state.update_data(category=category)
        await state.set_state(WorkoutStates.choosing_exercise)
        push_menu_stack(message.bot, bodyweight_exercise_menu)
        await message.answer("Выбери упражнение:", reply_markup=bodyweight_exercise_menu)
    elif message.text == "С утяжелителем":
        category = "weighted"
        await state.update_data(category=category)
        await state.set_state(WorkoutStates.choosing_exercise)
        push_menu_stack(message.bot, weighted_exercise_menu)
        await message.answer("Выбери упражнение:", reply_markup=weighted_exercise_menu)
    else:
        await message.answer("Выбери категорию из меню")


@router.message(WorkoutStates.choosing_exercise)
async def choose_exercise(message: Message, state: FSMContext):
    """Обрабатывает выбор упражнения."""
    data = await state.get_data()
    category = data.get("category")
    
    exercise = message.text
    
    # Определяем категорию по упражнению, если не задана
    if not category:
        if exercise in bodyweight_exercises:
            category = "bodyweight"
        elif exercise in weighted_exercises:
            category = "weighted"
        else:
            await message.answer("Выбери упражнение из меню")
            return
    
    await state.update_data(exercise=exercise, category=category)
    
    # Обрабатываем "Другое"
    if exercise == "Другое":
        await state.set_state(WorkoutStates.entering_custom_exercise)
        await message.answer("Введи название упражнения:")
        return
    
    # Особые случаи с временем
    variant = None
    if exercise == "Шаги":
        variant = "Количество шагов"
        await state.update_data(variant=variant)
        await state.set_state(WorkoutStates.entering_count)
        await message.answer("Сколько шагов сделал? Введи число:")
        return
    elif exercise == "Пробежка":
        variant = "Минуты"
        await state.update_data(variant=variant)
        await state.set_state(WorkoutStates.entering_count)
        await message.answer("Сколько минут пробежал? Введи число:")
        return
    elif exercise == "Скакалка":
        variant = "Количество прыжков"
        await state.update_data(variant=variant)
        await state.set_state(WorkoutStates.entering_count)
        await message.answer("Сколько раз прыгал на скакалке? Введи число:")
        return
    elif exercise == "Йога" or exercise == "Планка":
        variant = "Минуты"
        await state.update_data(variant=variant)
        await state.set_state(WorkoutStates.entering_count)
        await message.answer(f"Сколько минут {'занимался йогой' if exercise == 'Йога' else 'стоял в планке'}? Введи число:")
        return
    
    # Обычные упражнения
    if category == "weighted":
        variant = "С утяжелителем"
    else:
        variant = "Со своим весом"
    
    await state.update_data(variant=variant)
    await state.set_state(WorkoutStates.entering_count)
    push_menu_stack(message.bot, count_menu)
    await message.answer("Выбери количество повторений:", reply_markup=count_menu)


@router.message(WorkoutStates.entering_custom_exercise)
async def handle_custom_exercise(message: Message, state: FSMContext):
    """Обрабатывает ввод названия упражнения."""
    data = await state.get_data()
    category = data.get("category", "bodyweight")
    
    exercise = message.text
    await state.update_data(exercise=exercise)
    
    if category == "weighted":
        variant = "С утяжелителем"
    else:
        variant = "Со своим весом"
    
    await state.update_data(variant=variant)
    await state.set_state(WorkoutStates.entering_count)
    push_menu_stack(message.bot, count_menu)
    await message.answer("Отлично! Теперь введи количество повторений:", reply_markup=count_menu)


@router.message(WorkoutStates.entering_count)
async def handle_count_input(message: Message, state: FSMContext):
    """Обрабатывает ввод количества."""
    user_id = str(message.from_user.id)
    
    # Проверяем, не является ли это кнопкой меню
    if message.text in ["✏️ Ввести вручную", "⬅️ Назад", "🏠 Главное меню"]:
        if message.text == "✏️ Ввести вручную":
            await message.answer("Введи количество повторений числом:")
        return
    
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("⚠️ Введи положительное число")
        return
    
    data = await state.get_data()
    exercise = data.get("exercise")
    variant = data.get("variant")
    entry_date_str = data.get("entry_date", date.today().isoformat())
    
    if isinstance(entry_date_str, str):
        try:
            entry_date = date.fromisoformat(entry_date_str)
        except ValueError:
            parsed = parse_date(entry_date_str)
            entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
    else:
        entry_date = date.today()
    
    # Рассчитываем калории
    calories = calculate_workout_calories(user_id, exercise, variant, count)
    
    # Сохраняем тренировку
    workout = WorkoutRepository.save_workout(
        user_id=user_id,
        exercise=exercise,
        count=count,
        entry_date=entry_date,
        variant=variant,
        calories=calories,
    )
    
    logger.info(f"User {user_id} saved workout: {exercise} x {count} on {entry_date}")
    
    # Формируем ответ
    from utils.formatters import format_count_with_unit
    formatted_count = format_count_with_unit(count, variant)
    
    await state.clear()
    push_menu_stack(message.bot, training_menu)
    await message.answer(
        f"✅ Сохранено!\n\n"
        f"💪 {exercise}\n"
        f"📊 {formatted_count}\n"
        f"🔥 ~{calories:.0f} ккал\n"
        f"📅 {entry_date.strftime('%d.%m.%Y')}",
        reply_markup=training_menu,
    )


@router.message(lambda m: m.text == "✏️ Ввести вручную" and getattr(m.bot, "training_menu_open", False))
async def enter_manual_count(message: Message, state: FSMContext):
    """Обработчик кнопки 'Ввести вручную'."""
    await state.set_state(WorkoutStates.entering_count)
    await message.answer("Введи количество повторений числом:")


# TODO: Добавить обработчики календаря тренировок
# TODO: Добавить обработчики удаления тренировок


def register_workout_handlers(dp):
    """Регистрирует обработчики тренировок."""
    dp.include_router(router)
