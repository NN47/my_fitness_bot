"""Обработчики для самочувствия."""
import logging
import random
from datetime import date

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.repositories.wellbeing_repository import WellbeingRepository
from states.user_states import WellbeingStates
from utils.keyboards import (
    WELLBEING_BUTTON_TEXT,
    wellbeing_menu,
    wellbeing_quick_mood_menu,
    wellbeing_quick_influence_menu,
    wellbeing_quick_difficulty_menu,
    wellbeing_comment_menu,
    push_menu_stack,
)
from utils.calendar_utils import build_wellbeing_calendar_keyboard, build_wellbeing_day_actions_keyboard

logger = logging.getLogger(__name__)

router = Router()

QUICK_MOOD_OPTIONS = {"😄 Отлично", "🙂 Нормально", "😐 Так себе", "😣 Плохо"}
QUICK_INFLUENCE_OPTIONS = {
    "Сон",
    "Питание",
    "Нагрузка / тренировка",
    "Стресс",
    "Всё было нормально",
}
QUICK_DIFFICULTY_OPTIONS = {
    "Мало энергии",
    "Голод / тяга к сладкому",
    "Настроение / мотивация",
    "Физический дискомфорт",
    "Всё ок",
}
MOOD_NEEDS_DIFFICULTY = {"😐 Так себе", "😣 Плохо"}

QUICK_FINISH_RESPONSES = [
    "Принял. Учту это в анализе.",
    "Спасибо, это помогает видеть картину точнее.",
    "Отметка сохранена. Двигаемся дальше.",
]

COMMENT_FINISH_RESPONSES = [
    "Сохранил. Я учту это в анализе и рекомендациях.",
    "Спасибо, такие записи помогают находить закономерности.",
]


@router.message(lambda m: m.text == WELLBEING_BUTTON_TEXT)
async def start_wellbeing(message: Message, state: FSMContext):
    """Стартует меню самочувствия."""
    await state.clear()
    text = (
        "<b>Самочувствие</b>\n"
        "Как хочешь отметить состояние сегодня?\n\n"
        "<i>Оба варианта учитываются в анализе.</i>"
    )
    push_menu_stack(message.bot, wellbeing_menu)
    await state.set_state(WellbeingStates.choosing_mode)
    await message.answer(text, reply_markup=wellbeing_menu)


@router.message(lambda m: m.text == "📆 Календарь самочувствия")
async def show_wellbeing_calendar(message: Message, state: FSMContext):
    """Показывает календарь самочувствия."""
    await state.clear()
    user_id = str(message.from_user.id)
    await show_wellbeing_calendar_view(message, user_id)


async def show_wellbeing_calendar_view(
    message: Message,
    user_id: str,
    year: int | None = None,
    month: int | None = None,
):
    """Показывает календарь самочувствия."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    keyboard = build_wellbeing_calendar_keyboard(user_id, year, month)
    await message.answer(
        "📆 Календарь самочувствия\n\nВыбери день, чтобы посмотреть, добавить, изменить или удалить запись:",
        reply_markup=keyboard,
    )


@router.callback_query(lambda c: c.data.startswith("well_cal_nav:"))
async def navigate_wellbeing_calendar(callback: CallbackQuery):
    """Навигация по календарю самочувствия."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = map(int, parts[1].split("-"))
    user_id = str(callback.from_user.id)
    await show_wellbeing_calendar_view(callback.message, user_id, year, month)


@router.callback_query(lambda c: c.data.startswith("well_cal_back:"))
async def back_to_wellbeing_calendar(callback: CallbackQuery):
    """Возврат к календарю самочувствия."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = map(int, parts[1].split("-"))
    user_id = str(callback.from_user.id)
    await show_wellbeing_calendar_view(callback.message, user_id, year, month)


@router.callback_query(lambda c: c.data.startswith("well_cal_day:"))
async def select_wellbeing_calendar_day(callback: CallbackQuery):
    """Выбор дня в календаре самочувствия."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    user_id = str(callback.from_user.id)
    await show_wellbeing_day(callback.message, user_id, target_date)


@router.callback_query(lambda c: c.data.startswith("well_cal_add:"))
async def add_wellbeing_from_calendar(callback: CallbackQuery, state: FSMContext):
    """Добавляет запись самочувствия из календаря."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    await state.clear()
    await state.update_data(entry_date=target_date.isoformat(), return_to_calendar=True)
    await state.set_state(WellbeingStates.choosing_mode)
    push_menu_stack(callback.message.bot, wellbeing_menu)
    await callback.message.answer(
        f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n\nКак хочешь отметить самочувствие?",
        reply_markup=wellbeing_menu,
    )


@router.callback_query(lambda c: c.data.startswith("well_cal_edit:"))
async def edit_wellbeing_from_calendar(callback: CallbackQuery, state: FSMContext):
    """Редактирует запись самочувствия из календаря."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    entry_id = int(parts[2])
    user_id = str(callback.from_user.id)

    entry = WellbeingRepository.get_entry_by_id(entry_id, user_id)
    if not entry:
        await callback.message.answer("❌ Не нашёл запись для редактирования.")
        return

    await state.clear()
    await state.update_data(
        entry_date=target_date.isoformat(),
        entry_id=entry_id,
        return_to_calendar=True,
    )

    if entry.entry_type == "comment":
        await state.set_state(WellbeingStates.editing_comment)
        push_menu_stack(callback.message.bot, wellbeing_comment_menu)
        await callback.message.answer(
            f"✏️ Редактирование комментария\n\n"
            f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n"
            f"Текущий комментарий: {entry.comment or '—'}\n\n"
            "Напиши новый комментарий:",
            reply_markup=wellbeing_comment_menu,
        )
        return

    await state.update_data(
        mood=entry.mood,
        influence=entry.influence,
        difficulty=entry.difficulty,
    )
    await state.set_state(WellbeingStates.editing_quick_mood)
    push_menu_stack(callback.message.bot, wellbeing_quick_mood_menu)
    await callback.message.answer(
        f"✏️ Редактирование самочувствия\n\n"
        f"📅 Дата: {target_date.strftime('%d.%m.%Y')}\n"
        f"Текущее настроение: {entry.mood}\n\n"
        "Выбери настроение:",
        reply_markup=wellbeing_quick_mood_menu,
    )


@router.callback_query(lambda c: c.data.startswith("well_cal_del:"))
async def delete_wellbeing_from_calendar(callback: CallbackQuery):
    """Удаляет запись самочувствия из календаря."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    entry_id = int(parts[2])
    user_id = str(callback.from_user.id)

    success = WellbeingRepository.delete_entry(entry_id, user_id)
    if success:
        await callback.message.answer("✅ Запись удалена")
        await show_wellbeing_day(callback.message, user_id, target_date)
    else:
        await callback.message.answer("❌ Не удалось удалить запись")


async def show_wellbeing_day(message: Message, user_id: str, target_date: date):
    """Показывает записи самочувствия за день."""
    entries = WellbeingRepository.get_entries_for_date(user_id, target_date)

    if not entries:
        await message.answer(
            f"{target_date.strftime('%d.%m.%Y')}: нет записей самочувствия.",
            reply_markup=build_wellbeing_day_actions_keyboard([], target_date),
        )
        return

    text_lines = [f"📅 {target_date.strftime('%d.%m.%Y')}\n\nЗаписи самочувствия:"]
    for idx, entry in enumerate(entries, start=1):
        if entry.entry_type == "comment":
            text_lines.append(f"{idx}. ✍️ {entry.comment or '—'}")
        else:
            difficulty_text = f", {entry.difficulty}" if entry.difficulty else ""
            text_lines.append(
                f"{idx}. {entry.mood} / {entry.influence}{difficulty_text}"
            )

    await message.answer(
        "\n".join(text_lines),
        reply_markup=build_wellbeing_day_actions_keyboard(entries, target_date),
    )


@router.message(WellbeingStates.choosing_mode, lambda m: m.text == "🟢 Быстрый опрос (20 секунд)")
async def start_quick_survey(message: Message, state: FSMContext):
    """Запуск быстрого опроса."""
    await state.set_state(WellbeingStates.quick_mood)
    push_menu_stack(message.bot, wellbeing_quick_mood_menu)
    await message.answer(
        "<b>Шаг 1</b>\n\nКак ты себя чувствуешь сегодня?",
        reply_markup=wellbeing_quick_mood_menu,
    )


@router.message(WellbeingStates.choosing_mode, lambda m: m.text == "✍️ Оставить комментарий")
async def start_comment(message: Message, state: FSMContext):
    """Запуск свободного комментария."""
    await state.set_state(WellbeingStates.comment)
    push_menu_stack(message.bot, wellbeing_comment_menu)
    await message.answer(
        "<b>Комментарий о самочувствии</b>\n"
        "Напиши пару слов, если хочется зафиксировать день или состояние.\n"
        "Можно коротко. Можно как есть.",
        reply_markup=wellbeing_comment_menu,
    )


@router.message(WellbeingStates.quick_mood)
async def handle_quick_mood(message: Message, state: FSMContext):
    """Шаг 1: настроение."""
    if message.text not in QUICK_MOOD_OPTIONS:
        await message.answer("Пожалуйста, выбери вариант из списка.")
        return

    await state.update_data(mood=message.text)
    await state.set_state(WellbeingStates.quick_influence)
    push_menu_stack(message.bot, wellbeing_quick_influence_menu)
    await message.answer(
        "<b>Шаг 2</b>\n\nЧто больше всего повлияло на самочувствие?",
        reply_markup=wellbeing_quick_influence_menu,
    )


@router.message(WellbeingStates.quick_influence)
async def handle_quick_influence(message: Message, state: FSMContext):
    """Шаг 2: влияние."""
    if message.text not in QUICK_INFLUENCE_OPTIONS:
        await message.answer("Пожалуйста, выбери один вариант.")
        return

    data = await state.update_data(influence=message.text)
    mood = data.get("mood")

    if mood in MOOD_NEEDS_DIFFICULTY:
        await state.set_state(WellbeingStates.quick_difficulty)
        push_menu_stack(message.bot, wellbeing_quick_difficulty_menu)
        await message.answer(
            "<b>Шаг 3</b>\n\nГде сегодня было сложнее всего?",
            reply_markup=wellbeing_quick_difficulty_menu,
        )
        return

    await finalize_quick_entry(message, state, difficulty=None)


@router.message(WellbeingStates.quick_difficulty)
async def handle_quick_difficulty(message: Message, state: FSMContext):
    """Шаг 3: сложность дня."""
    if message.text not in QUICK_DIFFICULTY_OPTIONS:
        await message.answer("Пожалуйста, выбери один вариант.")
        return

    await finalize_quick_entry(message, state, difficulty=message.text)


@router.message(WellbeingStates.comment)
async def handle_comment(message: Message, state: FSMContext):
    """Сохраняет комментарий."""
    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий пустой. Если хочешь, напиши пару слов.")
        return

    data = await state.get_data()
    entry_date_raw = data.get("entry_date")
    return_to_calendar = data.get("return_to_calendar", False)
    entry_date = date.fromisoformat(entry_date_raw) if entry_date_raw else date.today()

    WellbeingRepository.save_comment_entry(
        user_id=str(message.from_user.id),
        comment=comment,
        entry_date=entry_date,
    )
    await state.clear()

    if return_to_calendar:
        await show_wellbeing_day(message, str(message.from_user.id), entry_date)
        return

    push_menu_stack(message.bot, wellbeing_menu)
    await message.answer(
        random.choice(COMMENT_FINISH_RESPONSES),
        reply_markup=wellbeing_menu,
    )


@router.message(WellbeingStates.editing_comment)
async def handle_edit_comment(message: Message, state: FSMContext):
    """Редактирует комментарий о самочувствии."""
    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий пустой. Если хочешь, напиши пару слов.")
        return

    data = await state.get_data()
    entry_id = data.get("entry_id")
    entry_date_raw = data.get("entry_date")
    return_to_calendar = data.get("return_to_calendar", False)
    entry_date = date.fromisoformat(entry_date_raw) if entry_date_raw else date.today()

    if not entry_id:
        await message.answer("❌ Не удалось найти запись для обновления.")
        await state.clear()
        return

    updated = WellbeingRepository.update_comment_entry(
        entry_id=entry_id,
        user_id=str(message.from_user.id),
        comment=comment,
        entry_date=entry_date,
    )
    await state.clear()

    if not updated:
        await message.answer("❌ Не удалось обновить запись.")
        return

    if return_to_calendar:
        await show_wellbeing_day(message, str(message.from_user.id), entry_date)
        return

    push_menu_stack(message.bot, wellbeing_menu)
    await message.answer("✅ Запись обновлена.", reply_markup=wellbeing_menu)


async def finalize_quick_entry(message: Message, state: FSMContext, difficulty: str | None):
    """Сохраняет быстрый опрос и отвечает."""
    data = await state.get_data()
    mood = data.get("mood")
    influence = data.get("influence")
    entry_date_raw = data.get("entry_date")
    return_to_calendar = data.get("return_to_calendar", False)
    entry_date = date.fromisoformat(entry_date_raw) if entry_date_raw else date.today()
    if not mood or not influence:
        logger.warning("Incomplete wellbeing quick survey data")
        await message.answer("Не удалось сохранить ответ. Попробуй ещё раз.")
        await state.clear()
        push_menu_stack(message.bot, wellbeing_menu)
        await message.answer("Возвращаю в меню самочувствия.", reply_markup=wellbeing_menu)
        return

    WellbeingRepository.save_quick_entry(
        user_id=str(message.from_user.id),
        mood=mood,
        influence=influence,
        difficulty=difficulty,
        entry_date=entry_date,
    )
    await state.clear()
    if return_to_calendar:
        await show_wellbeing_day(message, str(message.from_user.id), entry_date)
        return

    push_menu_stack(message.bot, wellbeing_menu)
    await message.answer(
        random.choice(QUICK_FINISH_RESPONSES),
        reply_markup=wellbeing_menu,
    )


@router.message(WellbeingStates.editing_quick_mood)
async def handle_edit_quick_mood(message: Message, state: FSMContext):
    """Шаг 1 редактирования: настроение."""
    if message.text not in QUICK_MOOD_OPTIONS:
        await message.answer("Пожалуйста, выбери вариант из списка.")
        return

    await state.update_data(mood=message.text)
    await state.set_state(WellbeingStates.editing_quick_influence)
    push_menu_stack(message.bot, wellbeing_quick_influence_menu)
    await message.answer(
        "<b>Шаг 2</b>\n\nЧто больше всего повлияло на самочувствие?",
        reply_markup=wellbeing_quick_influence_menu,
    )


@router.message(WellbeingStates.editing_quick_influence)
async def handle_edit_quick_influence(message: Message, state: FSMContext):
    """Шаг 2 редактирования: влияние."""
    if message.text not in QUICK_INFLUENCE_OPTIONS:
        await message.answer("Пожалуйста, выбери один вариант.")
        return

    data = await state.update_data(influence=message.text)
    mood = data.get("mood")

    if mood in MOOD_NEEDS_DIFFICULTY:
        await state.set_state(WellbeingStates.editing_quick_difficulty)
        push_menu_stack(message.bot, wellbeing_quick_difficulty_menu)
        await message.answer(
            "<b>Шаг 3</b>\n\nГде сегодня было сложнее всего?",
            reply_markup=wellbeing_quick_difficulty_menu,
        )
        return

    await finalize_quick_edit(message, state, difficulty=None)


@router.message(WellbeingStates.editing_quick_difficulty)
async def handle_edit_quick_difficulty(message: Message, state: FSMContext):
    """Шаг 3 редактирования: сложность дня."""
    if message.text not in QUICK_DIFFICULTY_OPTIONS:
        await message.answer("Пожалуйста, выбери один вариант.")
        return

    await finalize_quick_edit(message, state, difficulty=message.text)


async def finalize_quick_edit(message: Message, state: FSMContext, difficulty: str | None):
    """Сохраняет обновлённый быстрый опрос."""
    data = await state.get_data()
    mood = data.get("mood")
    influence = data.get("influence")
    entry_id = data.get("entry_id")
    entry_date_raw = data.get("entry_date")
    return_to_calendar = data.get("return_to_calendar", False)
    entry_date = date.fromisoformat(entry_date_raw) if entry_date_raw else date.today()

    if not entry_id or not mood or not influence:
        await message.answer("❌ Не удалось обновить запись.")
        await state.clear()
        return

    updated = WellbeingRepository.update_quick_entry(
        entry_id=entry_id,
        user_id=str(message.from_user.id),
        mood=mood,
        influence=influence,
        difficulty=difficulty,
        entry_date=entry_date,
    )
    await state.clear()

    if not updated:
        await message.answer("❌ Не удалось обновить запись.")
        return

    if return_to_calendar:
        await show_wellbeing_day(message, str(message.from_user.id), entry_date)
        return

    push_menu_stack(message.bot, wellbeing_menu)
    await message.answer("✅ Запись обновлена.", reply_markup=wellbeing_menu)


def register_wellbeing_handlers(dp):
    """Регистрирует обработчики самочувствия."""
    dp.include_router(router)
