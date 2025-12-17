"""Обработчики для тренировок."""
import logging
from datetime import date, timedelta, datetime
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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
from utils.formatters import format_count_with_unit
from utils.calendar_utils import build_workout_calendar_keyboard
from utils.workout_formatters import build_day_actions_keyboard

logger = logging.getLogger(__name__)

router = Router()


def reset_user_state(message: Message, *, keep_supplements: bool = False):
    """Сбрасывает состояние пользователя."""
    # TODO: Заменить на FSM clear
    pass


@router.message(lambda m: m.text == "🏋️ Тренировка")
async def show_training_menu(message: Message, state: FSMContext):
    """Показывает меню тренировок."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened training menu")
    await state.clear()  # Очищаем FSM состояние
    
    # Показываем прогресс тренировок
    from utils.progress_formatters import format_today_workouts_block
    workouts_text = format_today_workouts_block(user_id, include_date=False)
    
    push_menu_stack(message.bot, training_menu)
    await message.answer(
        f"🏋️ Тренировки\n\n{workouts_text}\n\nВыбери действие:",
        reply_markup=training_menu,
        parse_mode="HTML",
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


@router.message(lambda m: m.text == "📆 Календарь тренировок")
async def show_training_calendar(message: Message):
    """Показывает календарь тренировок."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened training calendar")
    await show_workout_calendar(message, user_id)


async def show_workout_calendar(message: Message, user_id: str, year: Optional[int] = None, month: Optional[int] = None):
    """Показывает календарь тренировок."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    keyboard = build_workout_calendar_keyboard(user_id, year, month)
    await message.answer(
        "📆 Выбери день, чтобы посмотреть, изменить или удалить тренировку:",
        reply_markup=keyboard,
    )


async def show_day_workouts(message: Message, user_id: str, target_date: date):
    """Показывает тренировки за день."""
    workouts = WorkoutRepository.get_workouts_for_day(user_id, target_date)
    
    if not workouts:
        await message.answer(
            f"{target_date.strftime('%d.%m.%Y')}: нет тренировок.",
            reply_markup=build_day_actions_keyboard([], target_date),
        )
        return
    
    text = [f"📅 {target_date.strftime('%d.%m.%Y')} — тренировки:"]
    total_calories = 0.0
    
    for w in workouts:
        variant_text = f" ({w.variant})" if w.variant else ""
        entry_calories = w.calories or calculate_workout_calories(user_id, w.exercise, w.variant, w.count)
        total_calories += entry_calories
        formatted_count = format_count_with_unit(w.count, w.variant)
        text.append(
            f"• {w.exercise}{variant_text}: {formatted_count} (~{entry_calories:.0f} ккал)"
        )
    
    text.append(f"\n🔥 Итого за день: ~{total_calories:.0f} ккал")
    
    await message.answer(
        "\n".join(text),
        reply_markup=build_day_actions_keyboard(workouts, target_date),
    )


@router.callback_query(lambda c: c.data.startswith("cal_nav:"))
async def navigate_calendar(callback: CallbackQuery):
    """Навигация по календарю тренировок."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = map(int, parts[1].split("-"))
    user_id = str(callback.from_user.id)
    await show_workout_calendar(callback.message, user_id, year, month)


@router.callback_query(lambda c: c.data.startswith("cal_back:"))
async def back_to_calendar(callback: CallbackQuery):
    """Возврат к календарю тренировок."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = map(int, parts[1].split("-"))
    user_id = str(callback.from_user.id)
    await show_workout_calendar(callback.message, user_id, year, month)


@router.callback_query(lambda c: c.data.startswith("cal_day:"))
async def select_calendar_day(callback: CallbackQuery):
    """Выбор дня в календаре тренировок."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    user_id = str(callback.from_user.id)
    await show_day_workouts(callback.message, user_id, target_date)


@router.callback_query(lambda c: c.data.startswith("wrk_add:"))
async def add_workout_from_calendar(callback: CallbackQuery, state: FSMContext):
    """Добавляет тренировку из календаря."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    
    await state.update_data(entry_date=target_date.isoformat())
    await state.set_state(WorkoutStates.choosing_category)
    
    push_menu_stack(callback.message.bot, exercise_category_menu)
    await callback.message.answer(
        f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n\nВыбери категорию упражнений:",
        reply_markup=exercise_category_menu,
    )


@router.callback_query(lambda c: c.data.startswith("wrk_edit:"))
async def edit_workout(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование тренировки."""
    await callback.answer()
    parts = callback.data.split(":")
    workout_id = int(parts[1])
    target_date = date.fromisoformat(parts[2]) if len(parts) > 2 else date.today()
    user_id = str(callback.from_user.id)
    
    workout = WorkoutRepository.get_workout_by_id(workout_id, user_id)
    if not workout:
        await callback.message.answer("❌ Не нашёл тренировку для изменения.")
        return
    
    await state.update_data(
        workout_id=workout_id,
        workout_exercise=workout.exercise,
        workout_variant=workout.variant,
        workout_date=workout.date.isoformat(),
        target_date=target_date.isoformat(),
    )
    await state.set_state(WorkoutStates.editing_count)
    
    await callback.message.answer(
        f"✏️ Редактирование тренировки\n\n"
        f"💪 {workout.exercise}\n"
        f"📅 {workout.date.strftime('%d.%m.%Y')}\n"
        f"📊 Текущее количество: {workout.count}\n\n"
        f"Введи новое количество:"
    )


@router.message(WorkoutStates.editing_count)
async def handle_workout_edit_count(message: Message, state: FSMContext):
    """Обрабатывает ввод нового количества при редактировании тренировки."""
    user_id = str(message.from_user.id)
    
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("⚠️ Введи положительное число")
        return
    
    data = await state.get_data()
    workout_id = data.get("workout_id")
    exercise = data.get("workout_exercise")
    variant = data.get("workout_variant")
    target_date_str = data.get("target_date", date.today().isoformat())
    
    if not workout_id:
        await message.answer("❌ Ошибка: не найдена тренировка для обновления.")
        await state.clear()
        return
    
    # Пересчитываем калории
    calories = calculate_workout_calories(user_id, exercise, variant, count)
    
    # Обновляем тренировку
    success = WorkoutRepository.update_workout(workout_id, user_id, count, calories)
    
    if success:
        if isinstance(target_date_str, str):
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()
        
        await state.clear()
        formatted_count = format_count_with_unit(count, variant)
        await message.answer(
            f"✅ Обновлено!\n\n"
            f"💪 {exercise}\n"
            f"📊 {formatted_count}\n"
            f"🔥 ~{calories:.0f} ккал"
        )
        await show_day_workouts(message, user_id, target_date)
    else:
        await message.answer("❌ Не удалось обновить тренировку. Попробуйте позже.")
        await state.clear()


@router.callback_query(lambda c: c.data.startswith("wrk_del:"))
async def delete_workout_from_calendar(callback: CallbackQuery):
    """Удаляет тренировку из календаря."""
    await callback.answer()
    parts = callback.data.split(":")
    workout_id = int(parts[1])
    target_date = date.fromisoformat(parts[2]) if len(parts) > 2 else date.today()
    user_id = str(callback.from_user.id)
    
    success = WorkoutRepository.delete_workout(workout_id, user_id)
    if success:
        await callback.message.answer("✅ Тренировка удалена")
        await show_day_workouts(callback.message, user_id, target_date)
    else:
        await callback.message.answer("❌ Не удалось удалить тренировку")


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


@router.message(lambda m: m.text == "✏️ Ввести вручную")
async def enter_manual_count(message: Message, state: FSMContext):
    """Обработчик кнопки 'Ввести вручную'."""
    await state.set_state(WorkoutStates.entering_count)
    await message.answer("Введи количество повторений числом:")


def register_workout_handlers(dp):
    """Регистрирует обработчики тренировок."""
    dp.include_router(router)
