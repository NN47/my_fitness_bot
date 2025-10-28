import asyncio
import nest_asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import os
import json
from datetime import date
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("API_TOKEN не найден. Установи переменную окружения или создай .env с API_TOKEN.")


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# -------------------- helpers --------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_workout(user_id, exercise, variant, count):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {"workouts": []}
    data[user_id]["workouts"].append({
        "exercise": exercise,
        "variant": variant,
        "count": count,
        "date": str(date.today())  
    })
    save_data(data)

def get_today_summary_text(user_id: str) -> str:
    data = load_data()
    today = str(date.today())

    if user_id not in data:
        return "Сегодня записей нет 😕"

    user = data[user_id]
    workouts = user.get("workouts", [])
    weights = user.get("weights", [])
    measurements = user.get("measurements", [])

    # --- собираем тренировки за сегодня ---
    todays_workouts = [w for w in workouts if w["date"] == today]
    if not todays_workouts:
        summary = "Сегодня тренировок пока нет 💭\n"
    else:
        summary = "💪 Результаты за сегодня:\n"
        totals = {}
        for w in todays_workouts:
            ex = w["exercise"]
            totals[ex] = totals.get(ex, 0) + w["count"]

        for ex, total in totals.items():
            summary += f"• {ex}: {total}\n"

    # --- добавляем последний вес ---
    if weights:
        last_weight = weights[-1]
        summary += f"\n⚖️ Вес: {last_weight['value']} кг (от {last_weight['date']})"

    # --- добавляем последние замеры ---
    if measurements:
        last_m = measurements[-1]
        parts = [f"{k}={v} см" for k, v in last_m.items() if k != "date"]
        summary += f"\n📏 Замеры ({last_m['date']}): {', '.join(parts)}"

    return summary


def add_weight(user_id, value):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"workouts": [], "weights": []}
    if "weights" not in data[user_id]:
        data[user_id]["weights"] = []
    data[user_id]["weights"].append({
        "value": value,
        "date": str(date.today())
    })
    save_data(data)

def add_measurements(user_id, measurements: dict):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"workouts": [], "weights": [], "measurements": []}
    if "measurements" not in data[user_id]:
        data[user_id]["measurements"] = []
    data[user_id]["measurements"].append({
        "date": str(date.today()),
        **measurements
    })
    save_data(data)



# -------------------- keyboards --------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Тренировки"), KeyboardButton(text="Мои данные")]
    ],
    resize_keyboard=True
)


activity_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить упражнение")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

exercise_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Подтягивания")],
        [KeyboardButton(text="Отжимания")],
        [KeyboardButton(text="Приседания")],
        [KeyboardButton(text="Пресс")],
        [KeyboardButton(text="Берпи")],
        [KeyboardButton(text="Шаги")],
        [KeyboardButton(text="Пробежка")],   
        [KeyboardButton(text="Скакалка")],   
        [KeyboardButton(text="Другое")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)



my_data_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Тренировки")],
        [KeyboardButton(text="⚖️ Вес")],
        [KeyboardButton(text="📏 Замеры")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)


my_workouts_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Сегодня")],
        [KeyboardButton(text="В другие дни")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

today_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Удалить запись")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

history_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Удалить запись из истории")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

weight_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить вес")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

measurements_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить замеры")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)


# -------------------- handlers --------------------
@dp.message(Command("start"))
async def start(message: Message):
    user_id = str(message.from_user.id)
    text = get_today_summary_text(user_id)
    await message.answer(f"Привет! 👋\n\n{text}", reply_markup=main_menu)


@dp.message(F.text == "Тренировки")
async def workouts(message: Message):
    await message.answer("Выбери упражнение:", reply_markup=exercise_menu)


@dp.message(F.text.in_(["Подтягивания", "Отжимания", "Приседания", "Пресс", "Берпи", "Шаги", "Пробежка", "Скакалка", "Другое"]))
async def choose_exercise(message: Message):
    message.bot.current_exercise = message.text

    if message.text == "Другое":
        message.bot.current_variant = "Без варианта"
        await message.answer("Введи название упражнения:")
        message.bot.expecting_custom_exercise = True
    elif message.text == "Шаги":
        message.bot.current_variant = "Количество шагов"
        await message.answer("Сколько шагов сделал? Введи число:")
    elif message.text == "Пробежка":
        message.bot.current_variant = "Минуты"
        await message.answer("Сколько минут пробежал? Введи число:")
    elif message.text == "Скакалка":
        message.bot.current_variant = "Количество прыжков"
        await message.answer("Сколько раз прыгал на скакалке? Введи число:")
    else:
        message.bot.current_variant = "Без варианта"
        await message.answer("Сколько раз сделал? Введи число:")



# пользователь ввёл название упражнения в "Другое"
@dp.message(F.text, lambda m: getattr(m.bot, "expecting_custom_exercise", False))
async def handle_custom_exercise(message: Message):
    message.bot.current_exercise = message.text
    message.bot.current_variant = "Без варианта"
    message.bot.expecting_custom_exercise = False
    await message.answer("Отлично! Теперь введи количество раз:")





@dp.message(F.text == "Удалить запись")
async def delete_entry_start(message: Message):
    if not hasattr(message.bot, "todays_workouts") or not message.bot.todays_workouts:
        await message.answer("Сегодня ещё нет записей для удаления.", reply_markup=my_workouts_menu)
        return

    message.bot.expecting_delete = True
    await message.answer("Введи номер записи, которую хочешь удалить:")


@dp.message(F.text.regexp(r"^\d+$"))
async def process_number(message: Message):
    user_id = str(message.from_user.id)
    number = int(message.text)

    # --- режим удаления сегодняшних тренировок ---
    if getattr(message.bot, "expecting_delete", False):
        index = number - 1
        if 0 <= index < len(message.bot.todays_workouts):
            entry = message.bot.todays_workouts[index]

            data = load_data()
            for w in data[user_id]["workouts"]:
                if (w["exercise"] == entry["exercise"] and
                    w["variant"] == entry["variant"] and
                    w["count"] == entry["count"] and
                    w["date"] == entry["date"]):
                    data[user_id]["workouts"].remove(w)
                    break

            save_data(data)
            message.bot.todays_workouts.pop(index)

            await message.answer(f"Удалил: {entry['exercise']} ({entry['variant']}) - {entry['count']}")
        else:
            await message.answer("Нет такой записи.")

        message.bot.expecting_delete = False
        return

    # --- режим удаления из всей истории ---
    if getattr(message.bot, "expecting_history_delete", False):
        index = number - 1
        if 0 <= index < len(message.bot.history_workouts):
            entry = message.bot.history_workouts[index]

            data = load_data()
            data[user_id]["workouts"].remove(entry)
            save_data(data)
            message.bot.history_workouts.pop(index)

            await message.answer(f"Удалил из истории: {entry['date']} — {entry['exercise']} ({entry['variant']}) - {entry['count']}")
        else:
            await message.answer("Нет такой записи.")

        message.bot.expecting_history_delete = False
        return

    # --- режим добавления подхода ---
    if not hasattr(message.bot, "current_exercise"):
        await message.answer("Сначала выбери упражнение из меню.")
        return

    count = number
    add_workout(user_id, message.bot.current_exercise, message.bot.current_variant, count)

    data = load_data()
    today = str(date.today())
    total_today = sum(
        w["count"]
        for w in data[user_id]["workouts"]
        if w["exercise"] == message.bot.current_exercise and w["date"] == today
    )

    await message.answer(
        f"Записал! 👍\nВсего {message.bot.current_exercise} сегодня: {total_today} повторений"
    )
    await message.answer("Если хочешь — введи ещё количество или вернись через '⬅️ Назад'")

@dp.message(F.text == "⚖️ Вес")
async def my_weight(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()
    weights = data.get(user_id, {}).get("weights", [])

    if not weights:
        await message.answer("⚖️ У тебя пока нет записей веса.", reply_markup=weight_menu)
        return

    text = "📊 История твоего веса:\n\n"
    for i, w in enumerate(weights, 1):
        text += f"{i}. {w['date']} — {w['value']} кг\n"

    await message.answer(text, reply_markup=weight_menu)

@dp.message(F.text == "➕ Добавить вес")
async def add_weight_start(message: Message):
    message.bot.expecting_weight = True
    await message.answer("Введи свой вес в килограммах (например: 72.5):")

@dp.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_weight_or_number(message: Message):
    user_id = str(message.from_user.id)

    # --- если ждём ввод веса ---
    if getattr(message.bot, "expecting_weight", False):
        weight_value = float(message.text.replace(",", "."))  # поддержка 72,5 тоже
        add_weight(user_id, weight_value)
        message.bot.expecting_weight = False
        await message.answer(f"✅ Записал вес: {weight_value} кг", reply_markup=weight_menu)
        return

    # иначе пусть идёт обычная обработка числа (повторы и т.п.)
    await process_number(message)

@dp.message(F.text == "📏 Замеры")
async def my_measurements(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()
    measurements = data.get(user_id, {}).get("measurements", [])

    if not measurements:
        await message.answer("📐 У тебя пока нет замеров.", reply_markup=measurements_menu)
        return

    text = "📊 История замеров:\n\n"
    for i, m in enumerate(measurements, 1):
        parts = [f"{k}: {v} см" for k, v in m.items() if k != "date"]
        text += f"{i}. {m['date']} — {', '.join(parts)}\n"

    await message.answer(text, reply_markup=measurements_menu)

@dp.message(F.text == "➕ Добавить замеры")
async def add_measurements_start(message: Message):
    message.bot.expecting_measurements = True
    await message.answer(
        "Введи замеры в формате:\n\n"
        "грудь=100, талия=80, руки=35\n\n"
        "Можно указать только нужные параметры."
    )

@dp.message(F.text, lambda m: getattr(m.bot, "expecting_measurements", False))
async def process_measurements(message: Message):
    user_id = str(message.from_user.id)
    raw = message.text

    try:
        # парсим строку вида "грудь=100, талия=80, руки=35"
        parts = [p.strip() for p in raw.replace(",", " ").split()]
        measurements = {}
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                measurements[k.strip()] = float(v.strip())
        if not measurements:
            raise ValueError
    except Exception:
        await message.answer("⚠️ Неверный формат. Попробуй так: грудь=100, талия=80, руки=35")
        return

    add_measurements(user_id, measurements)
    message.bot.expecting_measurements = False
    await message.answer(f"✅ Замеры сохранены: {measurements}", reply_markup=measurements_menu)


@dp.message(F.text == "Мои данные")
async def my_data(message: Message):
    await message.answer("Выбери, что посмотреть:", reply_markup=my_data_menu)


@dp.message(F.text == "⬅️ Назад")
async def go_back(message: Message):
    user_id = str(message.from_user.id)
    text = get_today_summary_text(user_id)
    await message.answer(text, reply_markup=main_menu)


@dp.message(F.text == "🏋️ Тренировки")
async def my_workouts(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    # получаем всю историю
    history = data.get(user_id, {}).get("workouts", [])

    if not history:
        await message.answer("У тебя пока нет истории тренировок 📭", reply_markup=my_workouts_menu)
        return

    # сохраняем историю для удаления
    message.bot.history_workouts = history
    message.bot.expecting_history_delete = False

    # формируем текст для вывода
    text = "📜 История твоих тренировок:\n\n"
    for i, w in enumerate(history, 1):
        text += f"{i}. {w['date']} — {w['exercise']} ({w['variant']}): {w['count']}\n"

    await message.answer(text, reply_markup=history_menu)


@dp.message(F.text == "⚖️ Вес")
async def my_weight(message: Message):
    await message.answer("📊 Здесь будет твой вес (можно хранить/добавлять записи).")

@dp.message(F.text == "📏 Замеры")
async def my_measurements(message: Message):
    await message.answer("📐 Здесь будут твои замеры (грудь, талия, руки и т.д.).")



@dp.message(F.text == "Сегодня")
async def workouts_today(message: Message):
    user_id = str(message.from_user.id)
    text = get_today_summary_text(user_id)

    if "нет" in text:
        await message.answer(text, reply_markup=my_workouts_menu)
    else:
        await message.answer(text, reply_markup=today_menu)

        # сохраняем список для удаления
        data = load_data()
        today = str(date.today())
        message.bot.todays_workouts = [w for w in data[user_id]["workouts"] if w["date"] == today]




@dp.message(F.text == "В другие дни")
async def workouts_history(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]["workouts"]:
        await message.answer("У тебя пока нет истории тренировок 📭", reply_markup=my_workouts_menu)
    else:
        text = "История твоих тренировок:\n\n"
        for w in data[user_id]["workouts"]:
            text += f"{w['date']}: {w['exercise']} ({w['variant']}): {w['count']} раз\n"
        await message.answer(text, reply_markup=history_menu)


@dp.message(F.text == "Удалить запись из истории")
async def delete_from_history_start(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]["workouts"]:
        await message.answer("История пуста 📭", reply_markup=my_workouts_menu)
        return

    message.bot.expecting_history_delete = True
    message.bot.history_workouts = data[user_id]["workouts"]

    text = "Выбери номер записи для удаления:\n\n"
    for i, w in enumerate(data[user_id]["workouts"], 1):
        text += f"{i}. {w['date']} — {w['exercise']} ({w['variant']}): {w['count']}\n"

    await message.answer(text)






# -------------------- run --------------------
import nest_asyncio
nest_asyncio.apply()

await dp.start_polling(bot)
