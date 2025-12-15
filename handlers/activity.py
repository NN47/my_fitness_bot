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
    from database.repositories import WorkoutRepository, MealRepository
    from utils.workout_utils import get_daily_workout_calories
    
    # Получаем данные
    workouts = WorkoutRepository.get_workouts_for_period(user_id, start_date, end_date)
    total_workout_calories = 0.0
    
    workouts_by_ex = {}
    for w in workouts:
        key = (w.exercise, w.variant)
        entry = workouts_by_ex.setdefault(key, {"count": 0, "calories": 0.0})
        entry["count"] += w.count
        cals = w.calories or get_daily_workout_calories(user_id, w.date)
        entry["calories"] += cals
        total_workout_calories += cals
    
    # Получаем приёмы пищи
    meals_data = []
    current_date = start_date
    while current_date <= end_date:
        meals = MealRepository.get_meals_for_date(user_id, current_date)
        if meals:
            totals = MealRepository.get_daily_totals(user_id, current_date)
            meals_data.append({
                "date": current_date.isoformat(),
                "meals_count": len(meals),
                "totals": totals,
            })
        current_date += timedelta(days=1)
    
    # Формируем текст для анализа
    analysis_text = f"""
Проанализируй активность пользователя за период: {period_name} ({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}).

Тренировки:
- Всего тренировок: {len(workouts)}
- Сожжено калорий: {total_workout_calories:.0f} ккал
- Упражнения: {dict(workouts_by_ex)}

Питание:
- Дней с приёмами пищи: {len(meals_data)}
- Средние КБЖУ за период: {sum(m['totals'].get('calories', 0) for m in meals_data) / len(meals_data) if meals_data else 0:.0f} ккал

Дай краткий анализ и рекомендации.
"""
    
    # Анализируем через Gemini
    analysis = gemini_service.analyze(analysis_text)
    return analysis


@router.message(lambda m: m.text == "Анализ деятельности")
async def analyze_activity(message: Message):
    """Показывает меню анализа деятельности."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened activity analysis")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(
        "📊 Анализ деятельности\n\nВыбери период:",
        reply_markup=activity_analysis_menu,
    )


@router.message(lambda m: m.text == "📅 Анализ за день")
async def analyze_activity_day(message: Message):
    """Анализ за день."""
    user_id = str(message.from_user.id)
    today = date.today()
    analysis = await generate_activity_analysis(user_id, today, today, "день")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, reply_markup=activity_analysis_menu)


@router.message(lambda m: m.text == "📆 Анализ за неделю")
async def analyze_activity_week(message: Message):
    """Анализ за неделю."""
    user_id = str(message.from_user.id)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    analysis = await generate_activity_analysis(user_id, week_start, today, "неделю")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, reply_markup=activity_analysis_menu)


@router.message(lambda m: m.text == "📊 Анализ за месяц")
async def analyze_activity_month(message: Message):
    """Анализ за месяц."""
    user_id = str(message.from_user.id)
    today = date.today()
    month_start = date(today.year, today.month, 1)
    analysis = await generate_activity_analysis(user_id, month_start, today, "месяц")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, reply_markup=activity_analysis_menu)


@router.message(lambda m: m.text == "📈 Анализ за все время")
async def analyze_activity_all_time(message: Message):
    """Анализ за все время."""
    user_id = str(message.from_user.id)
    today = date.today()
    # Берём последние 365 дней
    all_time_start = today - timedelta(days=365)
    analysis = await generate_activity_analysis(user_id, all_time_start, today, "все время")
    push_menu_stack(message.bot, activity_analysis_menu)
    await message.answer(analysis, reply_markup=activity_analysis_menu)


def register_activity_handlers(dp):
    """Регистрирует обработчики анализа деятельности."""
    dp.include_router(router)
