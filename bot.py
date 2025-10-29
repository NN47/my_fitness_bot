import asyncio
import nest_asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import os
import json
from datetime import date
from dotenv import load_dotenv
import threading
import http.server
import socketserver
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, func

import random
from datetime import datetime


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    exercise = Column(String, nullable=False)
    variant = Column(String)
    count = Column(Integer)
    date = Column(Date, default=date.today)

class Weight(Base):
    __tablename__ = "weights"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    value = Column(String, nullable=False)
    date = Column(Date, default=date.today)

class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    chest = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hips = Column(Float, nullable=True)
    biceps = Column(Float, nullable=True)
    thigh = Column(Float, nullable=True)
    date = Column(Date, default=date.today)


Base.metadata.create_all(engine)


def start_keepalive_server():
    PORT = 10000
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"✅ Keep-alive сервер запущен на порту {PORT}")
        httpd.serve_forever()

# Запуск мини-сервера в отдельном потоке
threading.Thread(target=start_keepalive_server, daemon=True).start()


load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("API_TOKEN не найден. Установи переменную окружения или создай .env с API_TOKEN.")


bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# -------------------- helpers --------------------


def add_workout(user_id, exercise, variant, count):
    session = SessionLocal()
    workout = Workout(
        user_id=str(user_id),
        exercise=exercise,
        variant=variant,
        count=count,
        date=date.today()
    )
    session.add(workout)
    session.commit()
    session.close()

def get_today_summary_text(user_id: str) -> str:
    session = SessionLocal()
    today = date.today()
    today_str = datetime.now().strftime("%d.%m.%Y")

    greetings = [
        "🔥 Новый день — новые победы!",
        "🚀 Пора действовать!",
        "💪 Сегодня ты становишься сильнее!",
        "🌟 Всё получится, просто начни!",
        "🏁 Вперёд к цели!"
    ]
    motivation = random.choice(greetings)

    # --- тренировки ---
    workouts = session.query(Workout).filter_by(user_id=user_id, date=today).all()
    if not workouts:
        summary = f"Сегодня ({today_str}) тренировок пока нет 💭\n"
    else:
        summary = f"📅 {today_str}\n💪 События:\n"
        totals = {}
        for w in workouts:
            totals[w.exercise] = totals.get(w.exercise, 0) + w.count
        for ex, total in totals.items():
            summary += f"• {ex}: {total}\n"

    # --- последний вес ---
    weight = session.query(Weight).filter_by(user_id=user_id).order_by(Weight.id.desc()).first()
    if weight:
        summary += f"\n⚖️ Вес: {weight.value} кг (от {weight.date})"

    # --- последние замеры ---
    m = session.query(Measurement).filter_by(user_id=user_id).order_by(Measurement.id.desc()).first()
    if m:
        parts = []
        if m.chest: parts.append(f"Грудь {m.chest} см")
        if m.waist: parts.append(f"Талия {m.waist} см")
        if m.hips: parts.append(f"Бёдра {m.hips} см")
        if parts:
            summary += f"\n📏 Замеры: {', '.join(parts)} ({m.date})"

    session.close()
    return f"{motivation}\n\n{summary}"


def add_weight(user_id, value):
    session = SessionLocal()
    weight = Weight(
        user_id=str(user_id),
        value=str(value),
        date=date.today()
    )
    session.add(weight)
    session.commit()
    session.close()

def add_measurements(user_id, measurements: dict):
    session = SessionLocal()
    m = Measurement(
        user_id=str(user_id),
        data=json.dumps(measurements, ensure_ascii=False),
        date=date.today()
    )
    session.add(m)
    session.commit()
    session.close()



# -------------------- keyboards --------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Тренировки"), KeyboardButton(text="📊История событий")]
    ],
    resize_keyboard=True
)


activity_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💪Добавить упражнение")],
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
        [KeyboardButton(text="🏋️ История тренировок")],
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
    name = message.from_user.first_name or "друг"
    welcome = (
        f"👋 Привет, {name}!\n"
        f"Твой фитнес-помощник готов 💪\n\n"
        f"{text}\n\n"
        "Выбери действие ниже:"
    )
    await message.answer(welcome, reply_markup=main_menu)




@dp.message(F.text == "🏋️ Тренировки")
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

            session = SessionLocal()
            # Удаляем запись из базы, совпадающую по всем полям
            workout = session.query(Workout).filter_by(
                user_id=user_id,
                exercise=entry.exercise,
                variant=entry.variant,
                count=entry.count,
                date=entry.date
            ).first()

            if workout:
                session.delete(workout)
                session.commit()
                session.close()
                message.bot.todays_workouts.pop(index)
                await message.answer(f"Удалил: {entry['exercise']} ({entry['variant']}) - {entry['count']}")
            else:
                session.close()
                await message.answer("Не нашёл такую запись в базе.")

        else:
            await message.answer("Нет такой записи.")

        message.bot.expecting_delete = False
        return


    # --- режим удаления из всей истории ---
    if getattr(message.bot, "expecting_history_delete", False):
        index = number - 1
        if 0 <= index < len(message.bot.history_workouts):
            entry = message.bot.history_workouts[index]

            session = SessionLocal()
            workout = session.query(Workout).filter_by(
                user_id=user_id,
                exercise=entry.exercise,
                variant=entry.variant,
                count=entry.count,
                date=entry.date
            ).first()

            if workout:
                session.delete(workout)
                session.commit()
                message.bot.history_workouts.pop(index)
                await message.answer(
                    f"Удалил из истории: {entry['date']} — {entry['exercise']} ({entry['variant']}) - {entry['count']}"
                )
            else:
                await message.answer("Не нашёл такую запись в базе.")

            session.close()
        else:
            await message.answer("Нет такой записи.")

        message.bot.expecting_history_delete = False
        return




   

    # --- режим добавления подхода ---
    if not hasattr(message.bot, "current_exercise"):
        await message.answer("Сначала выбери упражнение из меню.")
        return

    count = number
    exercise = message.bot.current_exercise
    variant = message.bot.current_variant

    # Сохраняем тренировку в базу
    session = SessionLocal()
    new_workout = Workout(
        user_id=user_id,
        exercise=exercise,
        variant=variant,
        count=count,
        date=date.today()
    )
    session.add(new_workout)
    session.commit()

    # Считаем общее количество за сегодня по этому упражнению
    total_today = (
        session.query(Workout)
        .filter_by(user_id=user_id, exercise=exercise, date=date.today())
        .with_entities(func.sum(Workout.count))
        .scalar()
    ) or 0

    session.close()

    await message.answer(
        f"Записал! 👍\nВсего {exercise} сегодня: {total_today} повторений"
    )
    await message.answer("Если хочешь — введи ещё количество или вернись через '⬅️ Назад'")



@dp.message(F.text == "⚖️ Вес")
async def my_weight(message: Message):
    user_id = str(message.from_user.id)
    session = SessionLocal()

    weights = (
        session.query(Weight)
        .filter_by(user_id=user_id)
        .order_by(Weight.date.desc())
        .all()
    )
    session.close()

    if not weights:
        await message.answer("⚖️ У тебя пока нет записей веса.", reply_markup=weight_menu)
        return

    text = "📊 История твоего веса:\n\n"
    for i, w in enumerate(weights, 1):
        text += f"{i}. {w.date.strftime('%d.%m.%Y')} — {w.value} кг\n"

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
    session = SessionLocal()

    measurements = (
        session.query(Measurement)
        .filter_by(user_id=user_id)
        .order_by(Measurement.date.desc())
        .all()
    )
    session.close()

    if not measurements:
        await message.answer("📐 У тебя пока нет замеров.", reply_markup=measurements_menu)
        return

    text = "📊 История замеров:\n\n"
    for i, m in enumerate(measurements, 1):
        parts = []
        if m.chest:
            parts.append(f"Грудь: {m.chest} см")
        if m.waist:
            parts.append(f"Талия: {m.waist} см")
        if m.hips:
            parts.append(f"Бёдра: {m.hips} см")
        if m.biceps:
            parts.append(f"Бицепс: {m.biceps} см")
        if m.thigh:
            parts.append(f"Бедро: {m.thigh} см")

        text += f"{i}. {m.date.strftime('%d.%m.%Y')} — {', '.join(parts)}\n"

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


@dp.message(F.text == "📊История событий")
async def my_data(message: Message):
    await message.answer("Выбери, что посмотреть:", reply_markup=my_data_menu)


@dp.message(F.text == "⬅️ Назад")
async def go_back(message: Message):
    user_id = str(message.from_user.id)
    text = get_today_summary_text(user_id)
    await message.answer(text, reply_markup=main_menu)


from sqlalchemy.orm import Session

@dp.message(F.text == "🏋️ История тренировок")
async def my_workouts(message: Message):
    user_id = str(message.from_user.id)
    
    # создаём сессию
    db = SessionLocal()
    try:
        # получаем все тренировки пользователя
        history = (
            db.query(Workout)
            .filter(Workout.user_id == user_id)
            .order_by(Workout.date.desc())
            .all()
        )
    finally:
        db.close()

    if not history:
        await message.answer("У тебя пока нет истории тренировок 📭", reply_markup=my_workouts_menu)
        return

    # сохраняем историю для удаления (в оперативной памяти)
    message.bot.history_workouts = history
    message.bot.expecting_history_delete = False

    # формируем текст для вывода
    text = "📜 История твоих тренировок:\n\n"
    for i, w in enumerate(history, 1):
        variant_text = f" ({w.variant})" if w.variant else ""
        text += f"{i}. {w.date} — {w.exercise}{variant_text}: {w.count}\n"

    await message.answer(text, reply_markup=history_menu)







@dp.message(F.text == "Сегодня")
async def workouts_today(message: Message):
    user_id = str(message.from_user.id)

    # создаём сессию
    db = SessionLocal()
    try:
        # получаем все тренировки пользователя за сегодня
        today = date.today()
        todays_workouts = (
            db.query(Workout)
            .filter(Workout.user_id == user_id, Workout.date == today)
            .all()
        )
    finally:
        db.close()

    # если ничего нет — выводим сообщение
    if not todays_workouts:
        await message.answer("Сегодня ты ещё ничего не записывал 💤", reply_markup=my_workouts_menu)
        return

    # сохраняем список для возможности удаления
    message.bot.todays_workouts = todays_workouts
    message.bot.expecting_delete = False

    # формируем текст для вывода
    text = "💪 Результаты за сегодня:\n\n"
    for i, w in enumerate(todays_workouts, 1):
        variant_text = f" ({w.variant})" if w.variant else ""
        text += f"{i}. {w.exercise}{variant_text}: {w.count}\n"

    await message.answer(text, reply_markup=today_menu)



@dp.message(F.text == "В другие дни")
async def workouts_history(message: Message):
    user_id = str(message.from_user.id)

    # создаём сессию
    db = SessionLocal()
    try:
        # получаем все тренировки, кроме сегодняшних
        history = (
            db.query(Workout)
            .filter(Workout.user_id == user_id, Workout.date != date.today())
            .order_by(Workout.date.desc())
            .all()
        )
    finally:
        db.close()

    # если записей нет
    if not history:
        await message.answer("У тебя пока нет истории тренировок 📭", reply_markup=my_workouts_menu)
        return

    # формируем текст
    text = "📅 История твоих тренировок:\n\n"
    for w in history:
        variant_text = f" ({w.variant})" if w.variant else ""
        text += f"{w.date}: {w.exercise}{variant_text}: {w.count} раз\n"

    await message.answer(text, reply_markup=history_menu)



@dp.message(F.text == "Удалить запись из истории")
async def delete_from_history_start(message: Message):
    user_id = str(message.from_user.id)

    # создаём сессию
    db = SessionLocal()
    try:
        # получаем все тренировки пользователя
        history = (
            db.query(Workout)
            .filter(Workout.user_id == user_id)
            .order_by(Workout.date.desc())
            .all()
        )
    finally:
        db.close()

    if not history:
        await message.answer("История пуста 📭", reply_markup=my_workouts_menu)
        return

    # сохраняем в оперативную память (для следующего шага — удаления)
    message.bot.expecting_history_delete = True
    message.bot.history_workouts = history

    # формируем текст
    text = "Выбери номер записи для удаления:\n\n"
    for i, w in enumerate(history, 1):
        variant_text = f" ({w.variant})" if w.variant else ""
        text += f"{i}. {w.date} — {w.exercise}{variant_text}: {w.count}\n"

    await message.answer(text)




# -------------------- run --------------------
nest_asyncio.apply()

async def main():
    print("🚀 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
