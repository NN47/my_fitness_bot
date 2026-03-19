"""Обработчики для анализа деятельности."""
import logging
from datetime import date, timedelta
from aiogram import Router
from aiogram.types import Message
from utils.keyboards import activity_analysis_menu, push_menu_stack
from services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

router = Router()


async def generate_activity_analysis(user_id: str, start_date: date, end_date: date, period_name: str) -> str:
    """Генерирует анализ активности за указанный период через Gemini."""
    from database.repositories import WorkoutRepository, MealRepository, WeightRepository
    from utils.workout_utils import calculate_workout_calories
    from utils.formatters import format_count_with_unit, get_kbju_goal_label
    
    # 🔹 Тренировки за период
    workouts = WorkoutRepository.get_workouts_for_period(user_id, start_date, end_date)
    
    workouts_by_ex = {}
    total_workout_calories = 0.0
    
    for w in workouts:
        key = (w.exercise, w.variant)
        entry = workouts_by_ex.setdefault(key, {"count": 0, "calories": 0.0})
        entry["count"] += w.count
        cals = w.calories or calculate_workout_calories(user_id, w.exercise, w.variant, w.count)
        entry["calories"] += cals
        total_workout_calories += cals
    
    if workouts_by_ex:
        workout_lines = []
        for (exercise, variant), data in workouts_by_ex.items():
            formatted_count = format_count_with_unit(data["count"], variant)
            variant_text = f" ({variant})" if variant else ""
            workout_lines.append(
                f"- {exercise}{variant_text}: {formatted_count}, ~{data['calories']:.0f} ккал"
            )
        workout_summary = "\n".join(workout_lines)
    else:
        workout_summary = f"За {period_name.lower()} тренировки не записаны."
    
    # 🔹 КБЖУ за период
    meals = []
    current_date = start_date
    while current_date <= end_date:
        day_meals = MealRepository.get_meals_for_date(user_id, current_date)
        meals.extend(day_meals)
        current_date += timedelta(days=1)
    
    total_calories = sum(m.calories or 0 for m in meals)
    total_protein = sum(m.protein or 0 for m in meals)
    total_fat = sum(m.fat or 0 for m in meals)
    total_carbs = sum(m.carbs or 0 for m in meals)
    
    meals_summary = (
        f"Калории: {total_calories:.0f} ккал, "
        f"Белки: {total_protein:.1f} г, "
        f"Жиры: {total_fat:.1f} г, "
        f"Углеводы: {total_carbs:.1f} г."
    )
    
    # 🔹 Цель / норма КБЖУ
    settings = MealRepository.get_kbju_settings(user_id)
    if settings:
        goal_label = get_kbju_goal_label(settings.goal)
        days_count = (end_date - start_date).days + 1
        kbju_goal_summary = (
            f"Цель: {goal_label}. "
            f"Норма за период: {settings.calories * days_count:.0f} ккал, "
            f"Б {settings.protein * days_count:.0f} г, "
            f"Ж {settings.fat * days_count:.0f} г, "
            f"У {settings.carbs * days_count:.0f} г."
        )
    else:
        kbju_goal_summary = "Цель по КБЖУ ещё не настроена."
    
    # 🔹 Вес и история веса
    weights = WeightRepository.get_weights_for_date_range(user_id, start_date, end_date)
    
    if weights:
        current_weight = weights[0]
        if len(weights) > 1:
            first_weight = weights[-1]
            change = float(str(current_weight.value).replace(",", ".")) - float(str(first_weight.value).replace(",", "."))
            change_text = f" ({'+' if change >= 0 else ''}{change:.1f} кг)"
        else:
            change_text = ""
        history_lines = [
            f"{w.date.strftime('%d.%m')}: {w.value} кг"
            for w in weights[:10]
        ]
        weight_summary = (
            f"Текущий вес: {current_weight.value} кг (от {current_weight.date.strftime('%d.%m.%Y')}){change_text}. "
            f"История измерений: " + "; ".join(history_lines)
        )
    else:
        # Если нет веса за период, показываем последний известный вес
        all_weights = WeightRepository.get_weights(user_id, limit=1)
        if all_weights:
            w = all_weights[0]
            weight_summary = f"Последний зафиксированный вес: {w.value} кг (от {w.date.strftime('%d.%m.%Y')}). За {period_name.lower()} новых измерений не было."
        else:
            weight_summary = "Записей по весу ещё нет."
    
    # 🔹 Собираем summary для Gemini
    date_range_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
    summary = f"""
Период: {period_name} ({date_range_str}).

Тренировки за период:
{workout_summary}
Всего ориентировочно израсходовано: ~{total_workout_calories:.0f} ккал.

Питание (КБЖУ) за период:
{meals_summary}

Норма / цель КБЖУ:
{kbju_goal_summary}

Вес:
{weight_summary}
"""
    
    # 🔹 Промпт для бота-ассистента
    prompt = f"""
Ты — бот-ассистент 🤖, персональный помощник пользователя по тренировкам и КБЖУ.
Говори дружелюбно, уверенно и по делу.

Очень важно:
- Не считай количество записей тренировок, я уже дал тебе готовый текст по объёму и видам упражнений.
- Цель по КБЖУ уже указана в данных, не используй формулировки вроде "если твоя цель...".
- История веса может включать несколько измерений — используй её для оценки тенденции, не говори, что измерение одно, если в данных есть история.
- Используй HTML-теги <b>текст</b> для выделения важных цифр и фактов жирным шрифтом.

Всегда начинай анализ с приветствия:
"Привет! Вот твой отчёт {period_name.lower()}👇"

Данные пользователя за период:
{summary}

Сделай краткий отчёт по 4 блокам:
1) Тренировки
2) Питание (КБЖУ)
3) Вес
4) Общий прогресс и мотивация

Пиши структурированно, но компактно. Используй <b>жирный шрифт</b> для выделения важных цифр и фактов.
"""
    
    result = gemini_service.analyze(prompt)
    return result


@router.message(lambda m: m.text == "Анализ деятельности")
async def analyze_activity(message: Message):
    """Показывает меню анализа деятельности."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened activity analysis")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(
        "📊 <b>Анализ деятельности</b>\n\nВыбери период для анализа:",
        parse_mode="HTML",
        reply_markup=activity_analysis_menu,
    )


@router.message(lambda m: m.text == "📊 Анализировать день")
async def analyze_activity_day(message: Message):
    """Анализ за день."""
    user_id = str(message.from_user.id)
    today = date.today()
    analysis = await generate_activity_analysis(user_id, today, today, "за день")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, parse_mode="HTML", reply_markup=activity_analysis_menu)


@router.message(lambda m: m.text == "📊 Анализировать неделю")
async def analyze_activity_week(message: Message):
    """Анализ за неделю."""
    user_id = str(message.from_user.id)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    analysis = await generate_activity_analysis(user_id, week_start, today, "за неделю")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, parse_mode="HTML", reply_markup=activity_analysis_menu)


@router.message(lambda m: m.text == "📊 Анализировать месяц")
async def analyze_activity_month(message: Message):
    """Анализ за месяц."""
    user_id = str(message.from_user.id)
    today = date.today()
    month_start = date(today.year, today.month, 1)
    analysis = await generate_activity_analysis(user_id, month_start, today, "за месяц")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, parse_mode="HTML", reply_markup=activity_analysis_menu)


@router.message(lambda m: m.text == "📈 Анализ за все время")
async def analyze_activity_all_time(message: Message):
    """Анализ за все время."""
    user_id = str(message.from_user.id)
    today = date.today()
    # Берём последние 365 дней
    all_time_start = today - timedelta(days=365)
    analysis = await generate_activity_analysis(user_id, all_time_start, today, "за все время")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, parse_mode="HTML", reply_markup=activity_analysis_menu)


def register_activity_handlers(dp):
    """Регистрирует обработчики анализа деятельности."""
    dp.include_router(router)
