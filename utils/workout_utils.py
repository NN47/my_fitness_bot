"""Утилиты для работы с тренировками."""
import logging
from typing import Optional
from database.repositories import WeightRepository

logger = logging.getLogger(__name__)


def estimate_met_for_exercise(exercise: str) -> float:
    """
    Оценивает MET (Metabolic Equivalent of Task) для упражнения.
    MET - это единица измерения энергетических затрат.
    """
    met_values = {
        # С собственным весом
        "Подтягивания": 3.0,
        "Отжимания": 3.5,
        "Приседания": 5.0,
        "Пресс": 3.0,
        "Берпи": 8.0,
        "Шаги": 3.0,
        "Пробежка": 7.0,
        "Скакалка": 10.0,
        "Становая тяга без утяжелителя": 4.0,
        "Румынская тяга без утяжелителя": 4.0,
        "Планка": 3.0,
        "Йога": 2.5,
        
        # С утяжелителем
        "Приседания со штангой": 6.0,
        "Жим штанги лёжа": 5.0,
        "Становая тяга с утяжелителем": 6.0,
        "Румынская тяга с утяжелителем": 5.0,
        "Тяга штанги в наклоне": 5.0,
        "Жим гантелей лёжа": 5.0,
        "Жим гантелей сидя": 4.0,
        "Подъёмы гантелей на бицепс": 3.0,
        "Тяга верхнего блока": 4.0,
        "Тяга нижнего блока": 4.0,
        "Жим ногами": 5.0,
        "Разведения гантелей": 3.0,
        "Тяга горизонтального блока": 4.0,
        "Сгибание ног в тренажёре": 3.0,
        "Разгибание ног в тренажёре": 3.0,
        "Гиперэкстензия с утяжелителем": 4.0,
    }
    
    return met_values.get(exercise, 3.0)  # По умолчанию 3.0


def calculate_workout_calories(
    user_id: str,
    exercise: str,
    variant: Optional[str],
    count: int,
) -> float:
    """
    Вычисляет примерные калории, сожжённые на тренировке.
    
    Формула: калории = MET × вес (кг) × время (часы)
    
    Для упражнений с повторениями используется приблизительная оценка.
    """
    weight = WeightRepository.get_last_weight(user_id) or 70.0
    met = estimate_met_for_exercise(exercise)
    
    # Если вариант - время (сек, мин), считаем по времени
    if variant in ("сек", "мин"):
        if variant == "сек":
            duration_hours = count / 3600
        else:  # мин
            duration_hours = count / 60
        calories = met * weight * duration_hours
    else:
        # Для повторений используем приблизительную оценку
        # Примерно 0.1 часа на 100 повторений
        duration_hours = (count / 100) * 0.1
        calories = met * weight * duration_hours
    
    return max(calories, 0.0)


def get_daily_workout_calories(user_id: str, entry_date) -> float:
    """Получает суммарные калории, сожжённые на тренировках за день."""
    from database.repositories import WorkoutRepository
    
    workouts = WorkoutRepository.get_workouts_for_day(user_id, entry_date)
    total = 0.0
    
    for w in workouts:
        if w.calories:
            total += w.calories
        else:
            total += calculate_workout_calories(user_id, w.exercise, w.variant, w.count)
    
    return total
