"""Обработчики сообщений бота."""
from .common import register_common_handlers
from .start import register_start_handlers
from .workouts import register_workout_handlers
from .meals import register_meal_handlers

__all__ = [
    "register_common_handlers",
    "register_start_handlers",
    "register_workout_handlers",
    "register_meal_handlers",
]
