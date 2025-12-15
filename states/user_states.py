"""FSM состояния для пользователей."""
from aiogram.fsm.state import State, StatesGroup


class MealEntryStates(StatesGroup):
    """Состояния для добавления приёма пищи."""
    waiting_for_food_input = State()
    waiting_for_photo = State()
    waiting_for_label_photo = State()
    waiting_for_barcode_photo = State()
    waiting_for_weight_input = State()
    editing_meal = State()


class WorkoutStates(StatesGroup):
    """Состояния для добавления тренировки."""
    choosing_category = State()
    choosing_exercise = State()
    entering_custom_exercise = State()
    entering_count = State()
    choosing_date = State()
    entering_custom_date = State()


class WeightStates(StatesGroup):
    """Состояния для работы с весом."""
    entering_weight = State()
    choosing_period = State()


class SupplementStates(StatesGroup):
    """Состояния для работы с добавками."""
    entering_name = State()
    entering_time = State()
    selecting_days = State()
    choosing_duration = State()
    logging_intake = State()
    entering_amount = State()
    editing_supplement = State()
    viewing_history = State()
    entering_history_time = State()
    entering_history_amount = State()


class WaterStates(StatesGroup):
    """Состояния для работы с водой."""
    entering_amount = State()


class KbjuTestStates(StatesGroup):
    """Состояния для теста КБЖУ."""
    entering_gender = State()
    entering_age = State()
    entering_height = State()
    entering_weight = State()
    entering_activity = State()
    entering_goal = State()
