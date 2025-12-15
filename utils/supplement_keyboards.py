"""Клавиатуры для добавок."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.keyboards import main_menu_button


def supplements_main_menu(has_items: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню добавок."""
    buttons = [[KeyboardButton(text="➕ Создать добавку")]]
    if has_items:
        buttons.append([KeyboardButton(text="📋 Мои добавки"), KeyboardButton(text="📅 Календарь добавок")])
        buttons.append([KeyboardButton(text="✅ Отметить приём")])
    buttons.append([main_menu_button])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def supplements_choice_menu(supplements: list[dict]) -> ReplyKeyboardMarkup:
    """Меню выбора добавки."""
    rows = [[KeyboardButton(text=item["name"])] for item in supplements]
    rows.append([KeyboardButton(text="⬅️ Назад"), main_menu_button])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def supplements_view_menu(supplements: list[dict]) -> ReplyKeyboardMarkup:
    """Меню просмотра добавок."""
    rows = [[KeyboardButton(text=item["name"])] for item in supplements]
    rows.append([KeyboardButton(text="⬅️ Назад"), main_menu_button])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def supplement_details_menu() -> ReplyKeyboardMarkup:
    """Меню деталей добавки."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Редактировать добавку")],
            [KeyboardButton(text="🗑 Удалить добавку"), KeyboardButton(text="✅ Отметить добавку")],
            [KeyboardButton(text="⬅️ Назад"), main_menu_button],
        ],
        resize_keyboard=True,
    )


def supplement_edit_menu(show_save: bool = False) -> ReplyKeyboardMarkup:
    """Меню редактирования добавки."""
    buttons = [
        [KeyboardButton(text="✏️ Редактировать время"), KeyboardButton(text="📅 Редактировать дни")],
        [KeyboardButton(text="⏳ Длительность приема"), KeyboardButton(text="✏️ Изменить название")],
        [KeyboardButton(text="🔔 Уведомления")],
    ]
    if show_save:
        buttons.append([KeyboardButton(text="💾 Сохранить")])
    buttons.append([KeyboardButton(text="⬅️ Отменить")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def time_edit_menu(times: list[str]) -> ReplyKeyboardMarkup:
    """Меню редактирования времени."""
    buttons: list[list[KeyboardButton]] = []
    for t in times:
        buttons.append([KeyboardButton(text=f"❌ {t}")])
    buttons.append([KeyboardButton(text="➕ Добавить"), KeyboardButton(text="💾 Сохранить")])
    buttons.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
