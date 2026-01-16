"""Обработчики для самочувствия."""
import logging
import random
from datetime import date

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

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

    WellbeingRepository.save_comment_entry(
        user_id=str(message.from_user.id),
        comment=comment,
        entry_date=date.today(),
    )
    await state.clear()
    push_menu_stack(message.bot, wellbeing_menu)
    await message.answer(
        random.choice(COMMENT_FINISH_RESPONSES),
        reply_markup=wellbeing_menu,
    )


async def finalize_quick_entry(message: Message, state: FSMContext, difficulty: str | None):
    """Сохраняет быстрый опрос и отвечает."""
    data = await state.get_data()
    mood = data.get("mood")
    influence = data.get("influence")
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
        entry_date=date.today(),
    )
    await state.clear()
    push_menu_stack(message.bot, wellbeing_menu)
    await message.answer(
        random.choice(QUICK_FINISH_RESPONSES),
        reply_markup=wellbeing_menu,
    )


def register_wellbeing_handlers(dp):
    """Регистрирует обработчики самочувствия."""
    dp.include_router(router)
