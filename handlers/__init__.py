"""Обработчики сообщений бота."""
from .common import register_common_handlers
from .start import register_start_handlers
from .workouts import register_workout_handlers
from .meals import register_meal_handlers
from .weight import register_weight_handlers
from .supplements import register_supplement_handlers
from .water import register_water_handlers
from .settings import register_settings_handlers

__all__ = [
    "register_common_handlers",
    "register_start_handlers",
    "register_workout_handlers",
    "register_meal_handlers",
    "register_weight_handlers",
    "register_supplement_handlers",
    "register_water_handlers",
    "register_settings_handlers",
]
