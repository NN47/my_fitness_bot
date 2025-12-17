"""Обработчики для КБЖУ и питания."""
import logging
import json
import re
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from typing import Optional
from aiogram.fsm.context import FSMContext
from states.user_states import MealEntryStates
from utils.keyboards import (
    kbju_menu,
    kbju_add_menu,
    kbju_after_meal_menu,
    push_menu_stack,
)
from database.repositories import MealRepository
from services.nutrition_service import nutrition_service
from services.gemini_service import gemini_service
from utils.validators import parse_date
from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()


def reset_user_state(message: Message, *, keep_supplements: bool = False):
    """Сбрасывает состояние пользователя."""
    # TODO: Заменить на FSM clear
    pass


def translate_text(text: str, source_lang: str = "ru", target_lang: str = "en") -> str:
    """Переводит текст через публичное API MyMemory."""
    if not text:
        return text
    
    try:
        import requests
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{source_lang}|{target_lang}"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        translated = (
            data.get("responseData", {}).get("translatedText")
            or data.get("matches", [{}])[0].get("translation")
        )
        return translated or text
    except Exception as e:
        logger.warning(f"Translation error: {e}")
        return text


@router.message(lambda m: m.text == "🍱 КБЖУ")
async def calories(message: Message, state: FSMContext):
    """Показывает меню КБЖУ."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened KBJU menu")
    await state.clear()  # Очищаем FSM состояние
    
    # Показываем прогресс КБЖУ
    from utils.progress_formatters import format_progress_block
    progress_text = format_progress_block(user_id)
    
    push_menu_stack(message.bot, kbju_menu)
    await message.answer(
        f"🍱 КБЖУ\n\n{progress_text}\n\nВыбери действие:",
        reply_markup=kbju_menu,
        parse_mode="HTML",
    )


@router.message(lambda m: m.text == "🎯 Цель / Норма КБЖУ")
async def show_kbju_goal(message: Message, state: FSMContext):
    """Показывает текущую цель КБЖУ или предлагает пройти тест."""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened KBJU goal settings")
    
    # Очищаем FSM состояние
    await state.clear()
    
    # Получаем текущие настройки
    settings = MealRepository.get_kbju_settings(user_id)
    
    if settings:
        # Показываем текущие настройки
        goal_labels = {
            "loss": "📉 Похудение",
            "maintain": "⚖️ Поддержание веса",
            "gain": "💪 Набор массы"
        }
        goal_label = goal_labels.get(settings.goal, "Не указана")
        
        from utils.formatters import format_kbju_goal_text
        text = format_kbju_goal_text(
            settings.calories,
            settings.protein,
            settings.fat,
            settings.carbs,
            goal_label
        )
        text += "\n\n💡 Хочешь изменить цель?"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Пройти тест заново", callback_data="kbju_test_start")]
        ])
        
        push_menu_stack(message.bot, kbju_menu)
        await message.answer(text, parse_mode="HTML", reply_markup=kbju_menu)
        await message.answer("Нажми кнопку ниже, чтобы изменить цель:", reply_markup=inline_kb)
    else:
        # Предлагаем пройти тест
        from utils.keyboards import kbju_gender_menu
        from states.user_states import KbjuTestStates
        
        await state.clear()
        await state.set_state(KbjuTestStates.entering_gender)
        
        push_menu_stack(message.bot, kbju_gender_menu)
        await message.answer(
            "Окей, пройдём небольшой тест 💪\n\n"
            "Для начала — укажи пол:",
            reply_markup=kbju_gender_menu,
        )


@router.message(lambda m: m.text == "➕ Добавить")
async def calories_add(message: Message, state: FSMContext):
    """Начинает процесс добавления приёма пищи."""
    reset_user_state(message)
    await start_kbju_add_flow(message, date.today(), state)


async def start_kbju_add_flow(message: Message, entry_date: date, state: FSMContext):
    """Запускает поток добавления приёма пищи."""
    user_id = str(message.from_user.id)
    
    # Сохраняем дату в FSM
    await state.update_data(entry_date=entry_date.isoformat())
    
    text = (
        "🍱 Раздел КБЖУ\n\n"
        "Выбери, как добавить приём пищи:\n"
        "• 📝 Ввести приём пищи (анализ ИИ) — умный анализ на основе типичных значений (рекомендуется)\n"
        "• 📷 Анализ еды по фото — отправь фото еды\n"
        "• 📋 Анализ этикетки — отправь фото этикетки/упаковки\n"
        "• 📷 Скан штрих-кода — отправь фото штрих-кода\n"
        "• ➕ Через CalorieNinjas — альтернативный вариант"
    )
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer(text, reply_markup=kbju_add_menu)


@router.message(lambda m: m.text == "➕ Через CalorieNinjas")
async def kbju_add_via_calorieninjas(message: Message, state: FSMContext):
    """Обработчик добавления через CalorieNinjas."""
    await state.set_state(MealEntryStates.waiting_for_food_input)
    
    text = (
        "🍱 Раздел КБЖУ\n\n"
        "Напиши, что ты съел(а) одним сообщением.\n\n"
        "Например:\n"
        "• 100 г овсянки, 2 яйца, 1 банан\n"
        "• 150 г куриной грудки и 200 г риса\n\n"
        "Важно: сначала указывай количество (например: 100 г или 2 шт), "
        "а после — сам продукт."
    )
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer(text, reply_markup=kbju_add_menu)


@router.message(lambda m: m.text == "📝 Ввести приём пищи (анализ ИИ)")
async def kbju_add_via_ai(message: Message, state: FSMContext):
    """Обработчик добавления через Gemini AI."""
    await state.set_state(MealEntryStates.waiting_for_ai_food_input)
    
    text = (
        "🍱 Раздел КБЖУ\n\n"
        "📝 Ввести приём пищи (анализ ИИ)\n\n"
        "Напиши, что ты съел, с примерным весом в одном сообщении.\n\n"
        "Например: 200 г курицы, 100 г йогурта, 30 г орехов.\n\n"
        "ИИ автоматически определит КБЖУ на основе типичных значений продуктов."
    )
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer(text, reply_markup=kbju_add_menu)


@router.message(lambda m: m.text == "📷 Анализ еды по фото")
async def kbju_add_via_photo(message: Message, state: FSMContext):
    """Обработчик анализа еды по фото."""
    reset_user_state(message)
    await state.set_state(MealEntryStates.waiting_for_photo)
    
    text = (
        "🍱 Раздел КБЖУ\n\n"
        "📷 Анализ еды по фото\n\n"
        "Отправь мне фото еды, и я определю КБЖУ с помощью ИИ! 🤖\n\n"
        "Сделай фото так, чтобы еда была хорошо видна на изображении."
    )
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer(text, reply_markup=kbju_add_menu)


@router.message(MealEntryStates.waiting_for_food_input)
async def handle_food_input(message: Message, state: FSMContext):
    """Обрабатывает ввод текста для CalorieNinjas."""
    user_text = message.text.strip()
    if not user_text:
        await message.answer("Напиши, пожалуйста, что ты съел(а) 🙏")
        return
    
    user_id = str(message.from_user.id)
    data = await state.get_data()
    entry_date_str = data.get("entry_date")
    if entry_date_str:
        if isinstance(entry_date_str, str):
            try:
                entry_date = date.fromisoformat(entry_date_str)
            except ValueError:
                parsed = parse_date(entry_date_str)
                entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    translated_query = translate_text(user_text, source_lang="ru", target_lang="en")
    logger.info(f"🍱 Перевод запроса для API: {translated_query}")
    
    try:
        items, totals = nutrition_service.get_nutrition_from_api(translated_query)
    except Exception as e:
        logger.error(f"Nutrition API error: {e}")
        await message.answer(
            "⚠️ Не получилось получить КБЖУ из сервиса.\n"
            "Попробуй ещё раз чуть позже или измени формулировку."
        )
        return
    
    if not items:
        await message.answer(
            "Я не нашёл продукты в этом описании 🤔\n"
            "Попробуй написать чуть по-другому: добавь количество или уточни продукт."
        )
        return
    
    # Формируем детали для сохранения
    lines = ["🍱 Оценка по КБЖУ для этого приёма пищи:\n"]
    api_details_lines = []
    
    for item in items:
        name_en = (item.get("name") or "item").title()
        name = translate_text(name_en, source_lang="en", target_lang="ru")
        
        cal = float(item.get("_calories", 0.0))
        p = float(item.get("_protein_g", 0.0))
        f = float(item.get("_fat_total_g", 0.0))
        c = float(item.get("_carbohydrates_total_g", 0.0))
        
        line = f"• {name} — {cal:.0f} ккал (Б {p:.1f} / Ж {f:.1f} / У {c:.1f})"
        lines.append(line)
        api_details_lines.append(line)
    
    lines.append("\nИТОГО:")
    lines.append(
        f"🔥 Калории: {float(totals['calories']):.0f} ккал\n"
        f"💪 Белки: {float(totals['protein_g']):.1f} г\n"
        f"🥑 Жиры: {float(totals['fat_total_g']):.1f} г\n"
        f"🍩 Углеводы: {float(totals['carbohydrates_total_g']):.1f} г"
    )
    
    api_details = "\n".join(api_details_lines)
    
    # Сохраняем в БД
    saved_meal = MealRepository.save_meal(
        user_id=user_id,
        raw_query=user_text,
        calories=float(totals['calories']),
        protein=float(totals['protein_g']),
        fat=float(totals['fat_total_g']),
        carbs=float(totals['carbohydrates_total_g']),
        entry_date=entry_date,
        api_details=api_details,
        products_json=json.dumps(items),
    )
    
    # Сохраняем ID последнего приёма для редактирования
    if not hasattr(message.bot, "last_meal_ids"):
        message.bot.last_meal_ids = {}
    message.bot.last_meal_ids[user_id] = saved_meal.id
    
    # Показываем суммарные данные за день
    daily_totals = MealRepository.get_daily_totals(user_id, entry_date)
    lines.append("\nСУММА ЗА СЕГОДНЯ:")
    lines.append(
        f"🔥 Калории: {daily_totals['calories']:.0f} ккал\n"
        f"💪 Белки: {daily_totals.get('protein_g', daily_totals.get('protein', 0)):.1f} г\n"
        f"🥑 Жиры: {daily_totals.get('fat_total_g', daily_totals.get('fat', 0)):.1f} г\n"
        f"🍩 Углеводы: {daily_totals.get('carbohydrates_total_g', daily_totals.get('carbs', 0)):.1f} г"
    )
    
    await state.clear()
    push_menu_stack(message.bot, kbju_after_meal_menu)
    await message.answer("\n".join(lines), reply_markup=kbju_after_meal_menu)


@router.message(MealEntryStates.waiting_for_ai_food_input)
async def handle_ai_food_input(message: Message, state: FSMContext):
    """Обрабатывает ввод текста для Gemini AI."""
    user_text = message.text.strip()
    if not user_text:
        await message.answer("Напиши, пожалуйста, что ты съел(а) 🙏")
        return
    
    user_id = str(message.from_user.id)
    data = await state.get_data()
    entry_date_str = data.get("entry_date")
    if entry_date_str:
        if isinstance(entry_date_str, str):
            try:
                entry_date = date.fromisoformat(entry_date_str)
            except ValueError:
                parsed = parse_date(entry_date_str)
                entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    # Показываем сообщение об анализе
    await message.answer("🤖 Считаю КБЖУ с помощью ИИ, секунду...")
    
    # Получаем КБЖУ через Gemini
    kbju_data = gemini_service.estimate_kbju(user_text)
    
    if not kbju_data or "total" not in kbju_data:
        await message.answer(
            "⚠️ Не получилось определить КБЖУ.\n"
            "Попробуй ещё раз или используй другой способ добавления."
        )
        return
    
    items = kbju_data.get("items", [])
    total = kbju_data.get("total", {})
    
    # Безопасное преобразование значений
    def safe_float(value) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    # Формируем детальный ответ
    lines = ["🤖 Оценка по ИИ для этого приёма пищи:\n"]
    
    totals_for_db = {
        "calories": safe_float(total.get("kcal")),
        "protein": safe_float(total.get("protein")),
        "fat": safe_float(total.get("fat")),
        "carbs": safe_float(total.get("carbs")),
    }
    
    # Показываем каждый продукт
    for item in items:
        name = item.get("name") or "продукт"
        grams = safe_float(item.get("grams"))
        cal = safe_float(item.get("kcal"))
        p = safe_float(item.get("protein"))
        f = safe_float(item.get("fat"))
        c = safe_float(item.get("carbs"))
        
        lines.append(
            f"• {name} ({grams:.0f} г) — {cal:.0f} ккал (Б {p:.1f} / Ж {f:.1f} / У {c:.1f})"
        )
    
    lines.append("\nИТОГО:")
    lines.append(
        f"🔥 Калории: {totals_for_db['calories']:.0f} ккал\n"
        f"💪 Белки: {totals_for_db['protein']:.1f} г\n"
        f"🥑 Жиры: {totals_for_db['fat']:.1f} г\n"
        f"🍩 Углеводы: {totals_for_db['carbs']:.1f} г"
    )
    
    # Сохраняем в БД
    saved_meal = MealRepository.save_meal(
        user_id=user_id,
        raw_query=user_text,
        calories=totals_for_db["calories"],
        protein=totals_for_db["protein"],
        fat=totals_for_db["fat"],
        carbs=totals_for_db["carbs"],
        entry_date=entry_date,
        products_json=json.dumps(items),
    )
    
    # Сохраняем ID последнего приёма для редактирования
    if not hasattr(message.bot, "last_meal_ids"):
        message.bot.last_meal_ids = {}
    message.bot.last_meal_ids[user_id] = saved_meal.id
    
    # Показываем суммарные данные за день
    daily_totals = MealRepository.get_daily_totals(user_id, entry_date)
    lines.append("\nСУММА ЗА СЕГОДНЯ:")
    lines.append(
        f"🔥 Калории: {daily_totals.get('calories', 0):.0f} ккал\n"
        f"💪 Белки: {daily_totals.get('protein', 0):.1f} г\n"
        f"🥑 Жиры: {daily_totals.get('fat', 0):.1f} г\n"
        f"🍩 Углеводы: {daily_totals.get('carbs', 0):.1f} г"
    )
    
    await state.clear()
    push_menu_stack(message.bot, kbju_after_meal_menu)
    await message.answer("\n".join(lines), reply_markup=kbju_after_meal_menu)


@router.message(lambda m: m.text == "📋 Анализ этикетки")
async def kbju_add_via_label(message: Message, state: FSMContext):
    """Обработчик анализа этикетки."""
    reset_user_state(message)
    await state.set_state(MealEntryStates.waiting_for_label_photo)
    
    text = (
        "🍱 Раздел КБЖУ\n\n"
        "📋 Анализ этикетки/упаковки\n\n"
        "Отправь мне фото этикетки или упаковки продукта, и я найду КБЖУ в тексте! 📸\n\n"
        "Я прочитаю информацию о пищевой ценности и извлеку точные данные о калориях, белках, жирах и углеводах.\n\n"
        "Если на этикетке указан вес упаковки — использую его автоматически. "
        "Если нет — спрошу у тебя, сколько грамм ты съел(а)."
    )
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer(text, reply_markup=kbju_add_menu)


@router.message(lambda m: m.text == "📷 Скан штрих-кода")
async def kbju_add_via_barcode(message: Message, state: FSMContext):
    """Обработчик сканирования штрих-кода."""
    reset_user_state(message)
    await state.set_state(MealEntryStates.waiting_for_barcode_photo)
    
    text = (
        "🍱 Раздел КБЖУ\n\n"
        "📷 Сканирование штрих-кода\n\n"
        "Отправь мне фото штрих-кода продукта, и я найду информацию о нём в базе Open Food Facts! 📸\n\n"
        "Я распознаю штрих-код с помощью ИИ и получу точные данные о продукте: название, КБЖУ и другие факты."
    )
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer(text, reply_markup=kbju_add_menu)


@router.message(MealEntryStates.waiting_for_photo, F.photo)
async def handle_photo_input(message: Message, state: FSMContext):
    """Обрабатывает фото еды."""
    
    user_id = str(message.from_user.id)
    data = await state.get_data()
    entry_date_str = data.get("entry_date")
    if entry_date_str:
        if isinstance(entry_date_str, str):
            try:
                entry_date = date.fromisoformat(entry_date_str)
            except ValueError:
                parsed = parse_date(entry_date_str)
                entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    # Показываем сообщение об анализе
    await message.answer("📷 Анализирую фото с помощью ИИ, секунду... 🤖")
    
    # Скачиваем фото
    photo = message.photo[-1]  # Берём самое большое разрешение
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    image_data = image_bytes.read()
    
    # Анализируем через Gemini
    kbju_data = gemini_service.estimate_kbju_from_photo(image_data)
    
    if not kbju_data or "total" not in kbju_data:
        await message.answer(
            "⚠️ Не получилось определить КБЖУ по фото.\n"
            "Попробуй сделать фото получше или используй другой способ."
        )
        return
    
    items = kbju_data.get("items", [])
    total = kbju_data.get("total", {})
    
    # Безопасное преобразование значений
    def safe_float(value) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    # Формируем детальный ответ
    lines = ["📷 Анализ фото еды (ИИ):\n"]
    
    totals_for_db = {
        "calories": safe_float(total.get("kcal")),
        "protein": safe_float(total.get("protein")),
        "fat": safe_float(total.get("fat")),
        "carbs": safe_float(total.get("carbs")),
    }
    
    # Показываем каждый продукт
    for item in items:
        name = item.get("name") or "продукт"
        grams = safe_float(item.get("grams"))
        cal = safe_float(item.get("kcal"))
        p = safe_float(item.get("protein"))
        f = safe_float(item.get("fat"))
        c = safe_float(item.get("carbs"))
        
        lines.append(
            f"• {name} ({grams:.0f} г) — {cal:.0f} ккал (Б {p:.1f} / Ж {f:.1f} / У {c:.1f})"
        )
    
    lines.append("\nИТОГО:")
    lines.append(
        f"🔥 Калории: {totals_for_db['calories']:.0f} ккал\n"
        f"💪 Белки: {totals_for_db['protein']:.1f} г\n"
        f"🥑 Жиры: {totals_for_db['fat']:.1f} г\n"
        f"🍩 Углеводы: {totals_for_db['carbs']:.1f} г"
    )
    
    # Сохраняем в БД
    saved_meal = MealRepository.save_meal(
        user_id=user_id,
        raw_query="[Анализ по фото]",
        calories=totals_for_db["calories"],
        protein=totals_for_db["protein"],
        fat=totals_for_db["fat"],
        carbs=totals_for_db["carbs"],
        entry_date=entry_date,
        products_json=json.dumps(items),
    )
    
    # Сохраняем ID последнего приёма для редактирования
    if not hasattr(message.bot, "last_meal_ids"):
        message.bot.last_meal_ids = {}
    message.bot.last_meal_ids[user_id] = saved_meal.id
    
    # Показываем суммарные данные за день
    daily_totals = MealRepository.get_daily_totals(user_id, entry_date)
    lines.append("\nСУММА ЗА СЕГОДНЯ:")
    lines.append(
        f"🔥 Калории: {daily_totals.get('calories', 0):.0f} ккал\n"
        f"💪 Белки: {daily_totals.get('protein', 0):.1f} г\n"
        f"🥑 Жиры: {daily_totals.get('fat', 0):.1f} г\n"
        f"🍩 Углеводы: {daily_totals.get('carbs', 0):.1f} г"
    )
    
    await state.clear()
    push_menu_stack(message.bot, kbju_after_meal_menu)
    await message.answer("\n".join(lines), reply_markup=kbju_after_meal_menu)


@router.message(MealEntryStates.waiting_for_label_photo, F.photo)
async def handle_label_photo(message: Message, state: FSMContext):
    """Обрабатывает фото этикетки."""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    entry_date_str = data.get("entry_date")
    if entry_date_str:
        if isinstance(entry_date_str, str):
            try:
                entry_date = date.fromisoformat(entry_date_str)
            except ValueError:
                parsed = parse_date(entry_date_str)
                entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    # Показываем сообщение об анализе
    await message.answer("📋 Анализирую этикетку с помощью ИИ, секунду... 🤖")
    
    # Скачиваем фото
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    image_data = image_bytes.read()
    
    # Анализируем через Gemini
    label_data = gemini_service.extract_kbju_from_label(image_data)
    
    if not label_data or "kbju_per_100g" not in label_data:
        await message.answer(
            "⚠️ Не удалось найти КБЖУ на этикетке.\n"
            "Попробуй сделать фото более чётким или используй другой способ."
        )
        return
    
    kbju_per_100g = label_data["kbju_per_100g"]
    package_weight = label_data.get("package_weight")
    found_weight = label_data.get("found_weight", False)
    product_name = label_data.get("product_name", "Продукт")
    
    # Безопасное преобразование значений
    def safe_float(value) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    kcal_100g = safe_float(kbju_per_100g.get("kcal"))
    protein_100g = safe_float(kbju_per_100g.get("protein"))
    fat_100g = safe_float(kbju_per_100g.get("fat"))
    carbs_100g = safe_float(kbju_per_100g.get("carbs"))
    
    # Сохраняем данные в FSM для дальнейшего использования
    await state.set_state(MealEntryStates.waiting_for_weight_input)
    await state.update_data(
        kbju_per_100g=kbju_per_100g,
        product_name=product_name,
        entry_date=entry_date.isoformat(),
    )
    
    # Формируем сообщение в зависимости от того, найден ли вес
    if found_weight and package_weight is not None:
        weight = safe_float(package_weight)
        if weight > 0:
            await message.answer(
                f"✅ Нашёл КБЖУ на этикетке!\n\n"
                f"📦 Продукт: {product_name}\n"
                f"📊 КБЖУ на 100 г:\n"
                f"🔥 Калории: {kcal_100g:.0f} ккал\n"
                f"💪 Белки: {protein_100g:.1f} г\n"
                f"🥑 Жиры: {fat_100g:.1f} г\n"
                f"🍩 Углеводы: {carbs_100g:.1f} г\n\n"
                f"📦 В упаковке {weight:.0f} г, сколько Вы съели?"
            )
        else:
            await message.answer(
                f"✅ Нашёл КБЖУ на этикетке!\n\n"
                f"📦 Продукт: {product_name}\n"
                f"📊 КБЖУ на 100 г:\n"
                f"🔥 Калории: {kcal_100g:.0f} ккал\n"
                f"💪 Белки: {protein_100g:.1f} г\n"
                f"🥑 Жиры: {fat_100g:.1f} г\n"
                f"🍩 Углеводы: {carbs_100g:.1f} г\n\n"
                f"❓ Вес в упаковке не найден, сколько вы съели?"
            )
    else:
        await message.answer(
            f"✅ Нашёл КБЖУ на этикетке!\n\n"
            f"📦 Продукт: {product_name}\n"
            f"📊 КБЖУ на 100 г:\n"
            f"🔥 Калории: {kcal_100g:.0f} ккал\n"
            f"💪 Белки: {protein_100g:.1f} г\n"
            f"🥑 Жиры: {fat_100g:.1f} г\n"
            f"🍩 Углеводы: {carbs_100g:.1f} г\n\n"
            f"❓ Вес в упаковке не найден, сколько вы съели?"
        )


@router.message(MealEntryStates.waiting_for_barcode_photo, F.photo)
async def handle_barcode_photo(message: Message, state: FSMContext):
    """Обрабатывает фото штрих-кода."""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    entry_date_str = data.get("entry_date")
    if entry_date_str:
        if isinstance(entry_date_str, str):
            try:
                entry_date = date.fromisoformat(entry_date_str)
            except ValueError:
                parsed = parse_date(entry_date_str)
                entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    # Показываем сообщение о распознавании
    await message.answer("📷 Распознаю штрих-код, секунду... 🤖")
    
    # Скачиваем фото
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    image_data = image_bytes.read()
    
    # Распознаём штрих-код
    barcode = gemini_service.scan_barcode(image_data)
    
    if not barcode:
        await message.answer(
            "Не удалось распознать штрих-код на фото 😔\n\n"
            "Попробуй сделать фото ещё раз:\n"
            "• Убедись, что штрих-код хорошо виден\n"
            "• Сделай фото при хорошем освещении\n"
            "• Штрих-код должен быть в фокусе\n\n"
            "Или используй другие способы добавления КБЖУ."
        )
        return
    
    await message.answer(f"✅ Штрих-код распознан: {barcode}\n\n🔍 Ищу информацию о продукте...")
    
    # Получаем данные из Open Food Facts
    product_data = nutrition_service.get_product_from_openfoodfacts(barcode)
    
    if not product_data:
        await message.answer(
            f"❌ Продукт со штрих-кодом {barcode} не найден в базе Open Food Facts.\n\n"
            "Попробуй другой способ добавления КБЖУ или используй фото этикетки."
        )
        await state.clear()
        return
    
    # Формируем информацию о продукте
    product_name = product_data.get("name", "Неизвестный продукт")
    brand = product_data.get("brand", "")
    nutriments = product_data.get("nutriments", {})
    weight = product_data.get("weight")
    
    def safe_float(value) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    # КБЖУ на 100г
    kcal_100g = safe_float(nutriments.get("kcal", 0))
    protein_100g = safe_float(nutriments.get("protein", 0))
    fat_100g = safe_float(nutriments.get("fat", 0))
    carbs_100g = safe_float(nutriments.get("carbs", 0))
    
    # Проверяем, есть ли хотя бы какое-то КБЖУ
    if not (kcal_100g or protein_100g or fat_100g or carbs_100g):
        await message.answer(
            f"❌ В базе Open Food Facts нет информации о КБЖУ для продукта со штрих-кодом {barcode}.\n\n"
            "Попробуй использовать фото этикетки или другие способы добавления КБЖУ."
        )
        await state.clear()
        return
    
    # Сохраняем данные в FSM для дальнейшего использования
    await state.set_state(MealEntryStates.waiting_for_weight_input)
    await state.update_data(
        kbju_per_100g={
            "kcal": kcal_100g,
            "protein": protein_100g,
            "fat": fat_100g,
            "carbs": carbs_100g,
        },
        product_name=product_name,
        barcode=barcode,
        entry_date=entry_date.isoformat(),
    )
    
    # Формируем сообщение с информацией о продукте
    text_parts = [f"✅ Нашёл продукт в базе Open Food Facts!\n\n"]
    text_parts.append(f"📦 Продукт: <b>{product_name}</b>\n")
    
    if brand:
        text_parts.append(f"🏷 Бренд: {brand}\n")
    
    text_parts.append(f"🔢 Штрих-код: {barcode}\n")
    text_parts.append(f"\n📊 КБЖУ на 100 г:\n")
    text_parts.append(f"🔥 Калории: {kcal_100g:.0f} ккал\n")
    text_parts.append(f"💪 Белки: {protein_100g:.1f} г\n")
    text_parts.append(f"🥑 Жиры: {fat_100g:.1f} г\n")
    text_parts.append(f"🍩 Углеводы: {carbs_100g:.1f} г\n")
    
    # Если есть вес упаковки в базе, упоминаем его, но все равно спрашиваем
    if weight:
        text_parts.append(f"\n📦 В базе указан вес упаковки: {weight} г\n")
        text_parts.append(f"Сколько грамм вы съели? (можно ввести {weight} или другое значение)")
    else:
        text_parts.append(f"\n❓ Сколько грамм вы съели?")
    
    push_menu_stack(message.bot, kbju_add_menu)
    await message.answer("".join(text_parts), reply_markup=kbju_add_menu, parse_mode="HTML")


@router.message(MealEntryStates.waiting_for_weight_input)
async def handle_weight_input(message: Message, state: FSMContext):
    """Обрабатывает ввод веса для этикетки или штрих-кода."""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    
    try:
        weight_grams = float(message.text.replace(",", "."))
        if weight_grams <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Вес должен быть больше нуля. Введи правильное число (например: 50 или 100):")
        return
    
    entry_date_str = data.get("entry_date")
    if entry_date_str:
        if isinstance(entry_date_str, str):
            try:
                entry_date = date.fromisoformat(entry_date_str)
            except ValueError:
                parsed = parse_date(entry_date_str)
                entry_date = parsed.date() if isinstance(parsed, datetime) else date.today()
        else:
            entry_date = date.today()
    else:
        entry_date = date.today()
    
    # Безопасное преобразование значений
    def safe_float(value) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    # Пересчитываем пропорционально указанному весу
    multiplier = weight_grams / 100.0
    
    # Определяем источник (этикетка или штрих-код)
    kbju_per_100g = data.get("kbju_per_100g")
    product_name = data.get("product_name", "Продукт")
    barcode = data.get("barcode")
    
    if kbju_per_100g:
        # Этикетка или штрих-код (оба используют kbju_per_100g)
        kcal_100g = safe_float(kbju_per_100g.get("kcal"))
        protein_100g = safe_float(kbju_per_100g.get("protein"))
        fat_100g = safe_float(kbju_per_100g.get("fat"))
        carbs_100g = safe_float(kbju_per_100g.get("carbs"))
        
        totals_for_db = {
            "calories": kcal_100g * multiplier,
            "protein": protein_100g * multiplier,
            "fat": fat_100g * multiplier,
            "carbs": carbs_100g * multiplier,
        }
        
        # Определяем источник по наличию barcode
        if barcode:
            lines = [f"📷 Сканирование штрих-кода: {product_name}\n"]
            raw_query = f"[Штрих-код: {barcode}]"
        else:
            lines = [f"📋 Анализ этикетки: {product_name}\n"]
            raw_query = f"[Этикетка: {product_name}]"
    else:
        # Старый формат (для обратной совместимости)
        ratio = weight_grams / 100.0
        totals_for_db = {
            "calories": safe_float(data.get("kcal_per_100g", 0)) * ratio,
            "protein": safe_float(data.get("protein_per_100g", 0)) * ratio,
            "fat": safe_float(data.get("fat_per_100g", 0)) * ratio,
            "carbs": safe_float(data.get("carbs_per_100g", 0)) * ratio,
        }
        product_name = data.get("product_name", "Продукт")
        barcode = data.get("barcode", "")
        lines = [f"📷 Сканирование штрих-кода: {product_name}\n"]
        raw_query = f"[Штрих-код: {barcode}]"
    
    lines.append(f"📦 Вес: {weight_grams:.0f} г\n")
    lines.append("КБЖУ:")
    lines.append(
        f"🔥 Калории: {totals_for_db['calories']:.0f} ккал\n"
        f"💪 Белки: {totals_for_db['protein']:.1f} г\n"
        f"🥑 Жиры: {totals_for_db['fat']:.1f} г\n"
        f"🍩 Углеводы: {totals_for_db['carbs']:.1f} г"
    )
    
    # Сохраняем в БД
    saved_meal = MealRepository.save_meal(
        user_id=user_id,
        raw_query=raw_query,
        calories=totals_for_db["calories"],
        protein=totals_for_db["protein"],
        fat=totals_for_db["fat"],
        carbs=totals_for_db["carbs"],
        entry_date=entry_date,
    )
    
    # Сохраняем ID последнего приёма для редактирования
    if not hasattr(message.bot, "last_meal_ids"):
        message.bot.last_meal_ids = {}
    message.bot.last_meal_ids[user_id] = saved_meal.id
    
    # Показываем суммарные данные за день
    daily_totals = MealRepository.get_daily_totals(user_id, entry_date)
    lines.append("\nСУММА ЗА СЕГОДНЯ:")
    lines.append(
        f"🔥 Калории: {daily_totals.get('calories', 0):.0f} ккал\n"
        f"💪 Белки: {daily_totals.get('protein', 0):.1f} г\n"
        f"🥑 Жиры: {daily_totals.get('fat', 0):.1f} г\n"
        f"🍩 Углеводы: {daily_totals.get('carbs', 0):.1f} г"
    )
    
    await state.clear()
    push_menu_stack(message.bot, kbju_after_meal_menu)
    await message.answer("\n".join(lines), reply_markup=kbju_after_meal_menu)


@router.message(lambda m: m.text == "📊 Дневной отчёт")
async def calories_today_results(message: Message):
    """Показывает дневной отчёт по КБЖУ."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    await send_today_results(message, user_id)


async def send_today_results(message: Message, user_id: str):
    """Отправляет результаты за сегодня."""
    today = date.today()
    meals = MealRepository.get_meals_for_date(user_id, today)
    
    if not meals:
        from utils.keyboards import kbju_menu
        push_menu_stack(message.bot, kbju_menu)
        await message.answer(
            "Пока нет записей за сегодня. Добавь приём пищи, и я посчитаю КБЖУ!",
            reply_markup=kbju_menu,
        )
        return
    
    daily_totals = MealRepository.get_daily_totals(user_id, today)
    day_str = today.strftime("%d.%m.%Y")
    
    from utils.meal_formatters import format_today_meals, build_meals_actions_keyboard
    text = format_today_meals(meals, daily_totals, day_str)
    keyboard = build_meals_actions_keyboard(meals, today)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(lambda m: m.text == "📆 Календарь КБЖУ")
async def calories_calendar(message: Message):
    """Показывает календарь КБЖУ."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    await show_kbju_calendar(message, user_id)


async def show_kbju_calendar(message: Message, user_id: str, year: Optional[int] = None, month: Optional[int] = None):
    """Показывает календарь КБЖУ."""
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    
    from utils.calendar_utils import build_kbju_calendar_keyboard
    keyboard = build_kbju_calendar_keyboard(user_id, year, month)
    
    await message.answer(
        f"📆 Календарь КБЖУ\n\nВыбери день:",
        reply_markup=keyboard,
    )


@router.callback_query(lambda c: c.data.startswith("meal_cal_nav:"))
async def navigate_kbju_calendar(callback: CallbackQuery):
    """Навигация по календарю КБЖУ."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = map(int, parts[1].split("-"))
    user_id = str(callback.from_user.id)
    await show_kbju_calendar(callback.message, user_id, year, month)


@router.callback_query(lambda c: c.data.startswith("meal_cal_back:"))
async def back_to_kbju_calendar(callback: CallbackQuery):
    """Возврат к календарю КБЖУ."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = map(int, parts[1].split("-"))
    user_id = str(callback.from_user.id)
    await show_kbju_calendar(callback.message, user_id, year, month)


@router.callback_query(lambda c: c.data.startswith("meal_cal_day:"))
async def select_kbju_calendar_day(callback: CallbackQuery):
    """Выбор дня в календаре КБЖУ."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    user_id = str(callback.from_user.id)
    await show_day_meals(callback.message, user_id, target_date)


async def show_day_meals(message: Message, user_id: str, target_date: date):
    """Показывает приёмы пищи за день."""
    meals = MealRepository.get_meals_for_date(user_id, target_date)
    
    if not meals:
        from utils.meal_formatters import build_kbju_day_actions_keyboard
        await message.answer(
            f"{target_date.strftime('%d.%m.%Y')}: нет записей по КБЖУ.",
            reply_markup=build_kbju_day_actions_keyboard(target_date),
        )
        return
    
    daily_totals = MealRepository.get_daily_totals(user_id, target_date)
    day_str = target_date.strftime("%d.%m.%Y")
    
    from utils.meal_formatters import format_today_meals, build_meals_actions_keyboard
    text = format_today_meals(meals, daily_totals, day_str)
    keyboard = build_meals_actions_keyboard(meals, target_date, include_back=True)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("meal_cal_add:"))
async def add_meal_from_calendar(callback: CallbackQuery, state: FSMContext):
    """Добавляет приём пищи из календаря."""
    await callback.answer()
    parts = callback.data.split(":")
    target_date = date.fromisoformat(parts[1])
    await start_kbju_add_flow(callback.message, target_date, state)


@router.message(F.text == "➕ Внести ещё приём")
async def kbju_add_more_meal(message: Message, state: FSMContext):
    """Добавляет ещё один приём пищи."""
    await start_kbju_add_flow(message, date.today(), state)


@router.message(F.text == "✏️ Редактировать")
async def edit_last_meal(message: Message, state: FSMContext):
    """Редактирует последний добавленный приём пищи."""
    user_id = str(message.from_user.id)
    
    # Получаем ID последнего приёма
    if not hasattr(message.bot, "last_meal_ids"):
        message.bot.last_meal_ids = {}
    
    last_meal_id = message.bot.last_meal_ids.get(user_id)
    if not last_meal_id:
        await message.answer(
            "❌ Не найден последний приём пищи для редактирования.\n"
            "Попробуй добавить приём пищи, а затем отредактировать его."
        )
        return
    
    # Получаем приём пищи
    meal = MealRepository.get_meal_by_id(last_meal_id, user_id)
    if not meal:
        await message.answer("❌ Не нашёл запись для изменения.")
        return
    
    # Извлекаем продукты из products_json
    products = []
    if meal.products_json:
        try:
            products = json.loads(meal.products_json)
        except Exception:
            pass
    
    if not products:
        await message.answer(
            "❌ Не удалось извлечь список продуктов из этой записи.\n"
            "Попробуй удалить и создать запись заново."
        )
        return
    
    # Сохраняем данные в FSM для редактирования
    await state.set_state(MealEntryStates.editing_meal)
    await state.update_data(
        meal_id=last_meal_id,
        target_date=meal.date.isoformat(),
        saved_products=products,
    )
    
    # Формируем список продуктов для редактирования
    edit_lines = ["✏️ Редактирование приёма пищи\n\nТекущий состав:"]
    for i, p in enumerate(products, 1):
        name = p.get("name") or "продукт"
        grams = p.get("grams", 0)
        edit_lines.append(f"{i}. {name}, {grams:.0f} г")
    
    edit_lines.append("\nВведи новый состав в формате:")
    edit_lines.append("название, вес г")
    edit_lines.append("название, вес г")
    edit_lines.append("\nПример:")
    edit_lines.append("курица, 200 г")
    edit_lines.append("рис, 150 г")
    edit_lines.append("\nМожно изменить название и/или вес. КБЖУ пересчитается автоматически.")
    
    push_menu_stack(message.bot, kbju_after_meal_menu)
    await message.answer("\n".join(edit_lines), reply_markup=kbju_after_meal_menu)


@router.callback_query(lambda c: c.data.startswith("meal_edit:"))
async def start_meal_edit(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование приёма пищи."""
    await callback.answer()
    parts = callback.data.split(":")
    meal_id = int(parts[1])
    target_date = date.fromisoformat(parts[2]) if len(parts) > 2 else date.today()
    user_id = str(callback.from_user.id)
    
    meal = MealRepository.get_meal_by_id(meal_id, user_id)
    if not meal:
        await callback.message.answer("❌ Не нашёл запись для изменения.")
        return
    
    # Извлекаем продукты из products_json
    products = []
    if meal.products_json:
        try:
            products = json.loads(meal.products_json)
        except Exception:
            pass
    
    # Если продуктов нет, пробуем извлечь из api_details
    if not products and meal.api_details:
        # Парсим api_details для извлечения продуктов
        lines = meal.api_details.split("\n")
        for line in lines:
            if line.strip().startswith("•"):
                # Извлекаем название и вес
                match = re.match(r"•\s*(.+?)\s*\((\d+(?:\.\d+)?)\s*г\)", line)
                if match:
                    name = match.group(1).strip()
                    grams = float(match.group(2))
                    # Извлекаем КБЖУ
                    kbju_match = re.search(
                        r"(\d+(?:\.\d+)?)\s*ккал.*?Б\s*(\d+(?:\.\d+)?).*?Ж\s*(\d+(?:\.\d+)?).*?У\s*(\d+(?:\.\d+)?)",
                        line
                    )
                    if kbju_match:
                        cal = float(kbju_match.group(1))
                        prot = float(kbju_match.group(2))
                        fat = float(kbju_match.group(3))
                        carbs = float(kbju_match.group(4))
                        # Вычисляем КБЖУ на 100г
                        if grams > 0:
                            products.append({
                                "name": name,
                                "grams": grams,
                                "calories": cal,
                                "protein_g": prot,
                                "fat_total_g": fat,
                                "carbohydrates_total_g": carbs,
                                "calories_per_100g": (cal / grams) * 100,
                                "protein_per_100g": (prot / grams) * 100,
                                "fat_per_100g": (fat / grams) * 100,
                                "carbs_per_100g": (carbs / grams) * 100,
                            })
    
    if not products:
        await callback.message.answer(
            "❌ Не удалось извлечь список продуктов из этой записи.\n"
            "Попробуй удалить и создать запись заново."
        )
        return
    
    # Сохраняем данные в FSM
    await state.update_data(
        meal_id=meal_id,
        target_date=target_date.isoformat(),
        saved_products=products,
    )
    await state.set_state(MealEntryStates.editing_meal)
    
    # Формируем список продуктов для редактирования
    edit_lines = ["✏️ Редактирование приёма пищи\n\nТекущий состав:"]
    for i, p in enumerate(products, 1):
        name = p.get("name") or "продукт"
        grams = p.get("grams", 0)
        edit_lines.append(f"{i}. {name}, {grams:.0f} г")
    
    edit_lines.append("\nВведи новый состав в формате:")
    edit_lines.append("название, вес г")
    edit_lines.append("название, вес г")
    edit_lines.append("\nПример:")
    edit_lines.append("курица, 200 г")
    edit_lines.append("рис, 150 г")
    edit_lines.append("\nМожно изменить название и/или вес. КБЖУ пересчитается автоматически.")
    
    await callback.message.answer("\n".join(edit_lines))


@router.message(MealEntryStates.editing_meal)
async def handle_meal_edit_input(message: Message, state: FSMContext):
    """Обрабатывает ввод нового состава продуктов при редактировании."""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    meal_id = data.get("meal_id")
    target_date_str = data.get("target_date", date.today().isoformat())
    saved_products = data.get("saved_products", [])
    new_text = message.text.strip()
    
    if not meal_id:
        await message.answer("❌ Не получилось определить запись для обновления.")
        await state.clear()
        return
    
    if not new_text:
        await message.answer("Напиши новый состав продуктов в формате: название, вес г")
        return
    
    if not saved_products:
        await message.answer(
            "❌ Не удалось найти сохраненные данные продуктов.\n"
            "Попробуй удалить и создать запись заново."
        )
        await state.clear()
        return
    
    # Парсим ввод пользователя: каждая строка = "название, вес г"
    lines = [line.strip() for line in new_text.split("\n") if line.strip()]
    edited_products = []
    
    for i, line in enumerate(lines):
        # Парсим формат "название, вес г" или "название, вес"
        match = re.match(r"(.+?),\s*(\d+(?:[.,]\d+)?)\s*г?", line, re.IGNORECASE)
        if not match:
            await message.answer(
                f"❌ Неверный формат в строке {i+1}: {line}\n"
                "Используй формат: название, вес г\n"
                "Пример: курица, 200 г"
            )
            return
        
        name = match.group(1).strip()
        grams_str = match.group(2).replace(",", ".")
        grams = float(grams_str)
        
        # Находим соответствующий продукт из сохраненных
        if i < len(saved_products):
            original_product = saved_products[i]
        else:
            original_product = saved_products[-1] if saved_products else None
        
        if not original_product:
            await message.answer("❌ Ошибка: не найдены исходные данные продукта.")
            return
        
        # Получаем КБЖУ на 100г
        calories_per_100g = original_product.get("calories_per_100g")
        protein_per_100g = original_product.get("protein_per_100g")
        fat_per_100g = original_product.get("fat_per_100g")
        carbs_per_100g = original_product.get("carbs_per_100g")
        
        # Если нет значений на 100г, вычисляем из сохраненных данных
        if not calories_per_100g and original_product.get("grams", 0) > 0:
            orig_grams = original_product.get("grams", 1)
            calories_per_100g = (original_product.get("calories", 0) / orig_grams) * 100
            protein_per_100g = (original_product.get("protein_g", 0) / orig_grams) * 100
            fat_per_100g = (original_product.get("fat_total_g", 0) / orig_grams) * 100
            carbs_per_100g = (original_product.get("carbohydrates_total_g", 0) / orig_grams) * 100
        
        # Пересчитываем КБЖУ для нового веса
        new_calories = (calories_per_100g * grams) / 100
        new_protein = (protein_per_100g * grams) / 100
        new_fat = (fat_per_100g * grams) / 100
        new_carbs = (carbs_per_100g * grams) / 100
        
        edited_products.append({
            "name": name,
            "grams": grams,
            "calories": new_calories,
            "protein_g": new_protein,
            "fat_total_g": new_fat,
            "carbohydrates_total_g": new_carbs,
        })
    
    # Суммируем КБЖУ всех продуктов
    totals = {
        "calories": sum(p["calories"] for p in edited_products),
        "protein_g": sum(p["protein_g"] for p in edited_products),
        "fat_total_g": sum(p["fat_total_g"] for p in edited_products),
        "carbohydrates_total_g": sum(p["carbohydrates_total_g"] for p in edited_products),
    }
    
    # Формируем api_details
    api_details_lines = []
    for p in edited_products:
        api_details_lines.append(
            f"• {p['name']} ({p['grams']:.0f} г) — {p['calories']:.0f} ккал "
            f"(Б {p['protein_g']:.1f} / Ж {p['fat_total_g']:.1f} / У {p['carbohydrates_total_g']:.1f})"
        )
    api_details = "\n".join(api_details_lines) if api_details_lines else None
    
    # Обновляем запись
    success = MealRepository.update_meal(
        meal_id=meal_id,
        user_id=user_id,
        description=new_text,
        calories=totals["calories"],
        protein=totals["protein_g"],
        fat=totals["fat_total_g"],
        carbs=totals["carbohydrates_total_g"],
        products_json=json.dumps(edited_products),
        api_details=api_details,
    )
    
    if not success:
        await message.answer("❌ Не нашёл запись для обновления.")
        await state.clear()
        return
    
    await state.clear()
    
    # Показываем обновлённый день
    if isinstance(target_date_str, str):
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()
    
    await message.answer("✅ Приём пищи обновлён!")
    await show_day_meals(message, user_id, target_date)


@router.callback_query(lambda c: c.data.startswith("meal_del:"))
async def delete_meal(callback: CallbackQuery):
    """Удаляет приём пищи."""
    await callback.answer()
    parts = callback.data.split(":")
    meal_id = int(parts[1])
    target_date = date.fromisoformat(parts[2]) if len(parts) > 2 else date.today()
    user_id = str(callback.from_user.id)
    
    success = MealRepository.delete_meal(meal_id, user_id)
    if success:
        await callback.message.answer("✅ Запись удалена")
        await show_day_meals(callback.message, user_id, target_date)
    else:
        await callback.message.answer("❌ Не удалось удалить запись")


@router.callback_query(lambda c: c.data == "kbju_test_start")
async def start_kbju_test_from_button(callback: CallbackQuery, state: FSMContext):
    """Начинает тест КБЖУ из inline кнопки."""
    await callback.answer()
    from utils.keyboards import kbju_gender_menu
    from states.user_states import KbjuTestStates
    
    await state.clear()
    await state.set_state(KbjuTestStates.entering_gender)
    
    push_menu_stack(callback.message.bot, kbju_gender_menu)
    await callback.message.answer(
        "Окей, пройдём небольшой тест 💪\n\n"
        "Для начала — укажи пол:",
        reply_markup=kbju_gender_menu,
    )


def register_meal_handlers(dp):
    """Регистрирует обработчики КБЖУ."""
    dp.include_router(router)
