"""Клавиатуры для бота."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главная кнопка меню
MAIN_MENU_BUTTON_TEXT = "🔄 Главное меню"
LEGACY_MAIN_MENU_BUTTON_TEXT = "🏠 Главное меню"
MAIN_MENU_BUTTON_ALIASES = {MAIN_MENU_BUTTON_TEXT, LEGACY_MAIN_MENU_BUTTON_TEXT}
main_menu_button = KeyboardButton(text=MAIN_MENU_BUTTON_TEXT)

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Тренировка"), KeyboardButton(text="🍱 КБЖУ")],
        [KeyboardButton(text="⚖️ Вес / 📏 Замеры"), KeyboardButton(text="💊 Добавки")],
        [KeyboardButton(text="💆 Процедуры"), KeyboardButton(text="💧 Контроль воды")],
        [KeyboardButton(text="🤖 ИИ анализ деятельности")],
        [KeyboardButton(text="⚙️ Настройки"), main_menu_button],
    ],
    resize_keyboard=True
)

# Inline-кнопки быстрых действий под текстом
quick_actions_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💧 +250 мл", callback_data="quick_water_250"),
            InlineKeyboardButton(text="🍱 Быстрый перекус", callback_data="quick_snack"),
        ],
        [
            InlineKeyboardButton(text="🏋️ Сегодня тренировка", callback_data="quick_today_workout"),
            InlineKeyboardButton(text="😴 Сегодня выходной", callback_data="quick_rest_day"),
        ],
        [
            InlineKeyboardButton(text="💊 Добавки", callback_data="quick_supplements"),
            InlineKeyboardButton(text="⚖️ Вес", callback_data="quick_weight"),
        ],
    ]
)

# Меню тренировок
training_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить тренировку")],
        [KeyboardButton(text="📆 Календарь тренировок")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

count_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=str(n)) for n in range(1, 6)],
        [KeyboardButton(text=str(n)) for n in range(6, 11)],
        [KeyboardButton(text=str(n)) for n in range(11, 16)],
        [KeyboardButton(text=str(n)) for n in range(16, 21)],
        [KeyboardButton(text=str(n)) for n in [25, 30, 35, 40, 50]],
        [KeyboardButton(text="✏️ Ввести вручную")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

# Меню выбора даты тренировки
training_date_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📆 Другой день")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

other_day_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Вчера"), KeyboardButton(text="📆 Позавчера")],
        [KeyboardButton(text="✏️ Ввести дату вручную")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True
)

# Упражнения
bodyweight_exercises = [
    "Подтягивания",
    "Отжимания",
    "Приседания",
    "Пресс",
    "Берпи",
    "Шаги",
    "Пробежка",
    "Скакалка",
    "Становая тяга без утяжелителя",
    "Румынская тяга без утяжелителя",
    "Планка",
    "Йога",
    "Другое",
]

weighted_exercises = [
    "Приседания со штангой",
    "Жим штанги лёжа",
    "Становая тяга с утяжелителем",
    "Румынская тяга с утяжелителем",
    "Тяга штанги в наклоне",
    "Жим гантелей лёжа",
    "Жим гантелей сидя",
    "Подъёмы гантелей на бицепс",
    "Тяга верхнего блока",
    "Тяга нижнего блока",
    "Жим ногами",
    "Разведения гантелей",
    "Тяга горизонтального блока",
    "Сгибание ног в тренажёре",
    "Разгибание ног в тренажёре",
    "Гиперэкстензия с утяжелителем",
    "Другое",
]

exercise_category_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Со своим весом"), KeyboardButton(text="С утяжелителем")],
        [KeyboardButton(text="⬅️ Назад")],
        [main_menu_button],
    ],
    resize_keyboard=True
)

bodyweight_exercise_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=ex)] for ex in bodyweight_exercises] + [[KeyboardButton(text="⬅️ Назад"), main_menu_button]],
    resize_keyboard=True,
)

weighted_exercise_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=ex)] for ex in weighted_exercises] + [[KeyboardButton(text="⬅️ Назад"), main_menu_button]],
    resize_keyboard=True,
)

# Меню КБЖУ
kbju_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить")],
        [KeyboardButton(text="📊 Дневной отчёт"), KeyboardButton(text="📆 Календарь КБЖУ")],
        [KeyboardButton(text="🎯 Цель / Норма КБЖУ")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_goal_view_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✏️ Редактировать")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_intro_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Пройти быстрый тест КБЖУ")],
        [KeyboardButton(text="✏️ Ввести свою норму")],
        [KeyboardButton(text="➡️ Пока без цели")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_gender_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🙋‍♂️ Мужчина"), KeyboardButton(text="🙋‍♀️ Женщина")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_activity_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🪑 Мало движения")],
        [KeyboardButton(text="🚶 Умеренная активность")],
        [KeyboardButton(text="🏋️ Тренировки 3–5 раз/нед")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_goal_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📉 Похудение")],
        [KeyboardButton(text="⚖️ Поддержание")],
        [KeyboardButton(text="💪 Набор массы")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_add_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Ввести приём пищи (анализ ИИ)")],
        [KeyboardButton(text="📷 Анализ еды по фото")],
        [KeyboardButton(text="📋 Анализ этикетки"), KeyboardButton(text="📷 Скан штрих-кода")],
        [KeyboardButton(text="➕ Через CalorieNinjas")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

kbju_after_meal_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Внести ещё приём"),
            KeyboardButton(text="✏️ Редактировать"),
        ],
        [KeyboardButton(text="📊 Дневной отчёт")],
        [
            KeyboardButton(text="⬅️ Назад"),
            main_menu_button,
        ],
    ],
    resize_keyboard=True,
)

# Меню выбора типа редактирования КБЖУ
kbju_edit_type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚖️ Изменить вес продукта")],
        [KeyboardButton(text="📝 Изменить состав продуктов")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

# Меню настроек
settings_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗑 Удалить аккаунт")],
        [KeyboardButton(text="💬 Поддержка")],
        [KeyboardButton(text="🔒 Политика конфиденциальности")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

delete_account_confirm_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Да, удалить аккаунт")],
        [KeyboardButton(text="❌ Отмена")],
        [main_menu_button],
    ],
    resize_keyboard=True,
)

# Меню процедур
procedures_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить процедуру")],
        [KeyboardButton(text="📆 Календарь процедур")],
        [KeyboardButton(text="📊 Сегодня")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

# Меню воды
water_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить воду")],
        [KeyboardButton(text="📊 Статистика за сегодня")],
        [KeyboardButton(text="📆 История")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

water_amount_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="250"), KeyboardButton(text="300"), KeyboardButton(text="330"), KeyboardButton(text="500")],
        [KeyboardButton(text="550"), KeyboardButton(text="600"), KeyboardButton(text="650"), KeyboardButton(text="700")],
        [KeyboardButton(text="750"), KeyboardButton(text="800"), KeyboardButton(text="850"), KeyboardButton(text="900")],
        [KeyboardButton(text="1000"), KeyboardButton(text="1500"), KeyboardButton(text="1750"), KeyboardButton(text="2000")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True,
)

water_quick_add_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="250", callback_data="quick_water_add_250"),
            InlineKeyboardButton(text="300", callback_data="quick_water_add_300"),
            InlineKeyboardButton(text="330", callback_data="quick_water_add_330"),
            InlineKeyboardButton(text="500", callback_data="quick_water_add_500"),
        ],
        [
            InlineKeyboardButton(text="550", callback_data="quick_water_add_550"),
            InlineKeyboardButton(text="600", callback_data="quick_water_add_600"),
            InlineKeyboardButton(text="650", callback_data="quick_water_add_650"),
            InlineKeyboardButton(text="700", callback_data="quick_water_add_700"),
        ],
        [
            InlineKeyboardButton(text="750", callback_data="quick_water_add_750"),
            InlineKeyboardButton(text="800", callback_data="quick_water_add_800"),
            InlineKeyboardButton(text="850", callback_data="quick_water_add_850"),
            InlineKeyboardButton(text="900", callback_data="quick_water_add_900"),
        ],
        [
            InlineKeyboardButton(text="1000", callback_data="quick_water_add_1000"),
            InlineKeyboardButton(text="1500", callback_data="quick_water_add_1500"),
            InlineKeyboardButton(text="1750", callback_data="quick_water_add_1750"),
            InlineKeyboardButton(text="2000", callback_data="quick_water_add_2000"),
        ],
    ]
)

# Меню анализа
activity_analysis_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Анализ за день")],
        [KeyboardButton(text="📆 Анализ за неделю")],
        [KeyboardButton(text="📊 Анализ за месяц")],
        [KeyboardButton(text="📈 Анализ за все время")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)

# Меню для добавления еще подхода
add_another_set_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Да, добавить еще подход")],
        [KeyboardButton(text="❌ Нет, завершить")],
    ],
    resize_keyboard=True,
)

# Меню выбора типа хвата для подтягиваний
grip_type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Прямой хват"), KeyboardButton(text="Обратный хват")],
        [KeyboardButton(text="Нейтральный хват")],
        [KeyboardButton(text="Пропустить")],
        [KeyboardButton(text="⬅️ Назад"), main_menu_button],
    ],
    resize_keyboard=True,
)


def push_menu_stack(bot, reply_markup):
    """Добавляет клавиатуру в стек меню."""
    if not isinstance(reply_markup, ReplyKeyboardMarkup):
        return

    stack = getattr(bot, "menu_stack", [])
    if not stack:
        stack = [main_menu]

    if stack and stack[-1] is not reply_markup:
        stack.append(reply_markup)

    bot.menu_stack = stack
