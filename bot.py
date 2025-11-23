import asyncio
import nest_asyncio
from aiogram import Bot, Dispatcher, F
import calendar
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
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
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, func
from datetime import timedelta
import random
from datetime import datetime


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

MONTH_NAMES = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]

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
        summary = f"📅 {today_str}\n 🏋️ Тренировка:\n"
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


def add_weight(user_id, value, entry_date):
    session = SessionLocal()
    weight = Weight(
        user_id=str(user_id),
        value=str(value),
        date=entry_date
    )
    session.add(weight)
    session.commit()
    session.close()

def add_measurements(user_id, measurements: dict, entry_date):
    """
    measurements: словарь с ключами среди {'chest','waist','hips','biceps','thigh'}
    """
    session = SessionLocal()
    try:
        m = Measurement(
            user_id=str(user_id),
            chest=measurements.get("chest"),
            waist=measurements.get("waist"),
            hips=measurements.get("hips"),
            biceps=measurements.get("biceps"),
            thigh=measurements.get("thigh"),
            date=entry_date
        )
        session.add(m)
        session.commit()
    finally:
        session.close()


def get_workouts_for_day(user_id: str, target_date: date):
    session = SessionLocal()
    try:
        return (
            session.query(Workout)
            .filter(Workout.user_id == user_id, Workout.date == target_date)
            .order_by(Workout.id)
            .all()
        )
    finally:
        session.close()


def get_month_workout_days(user_id: str, year: int, month: int):
    first_day = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    last_day = date(year, month, days_in_month)

    session = SessionLocal()
    try:
        workouts = (
            session.query(Workout.date)
            .filter(
                Workout.user_id == user_id,
                Workout.date >= first_day,
                Workout.date <= last_day,
            )
            .all()
        )
        return {w.date.day for w in workouts}
    finally:
        session.close()


def build_calendar_keyboard(user_id: str, year: int, month: int) -> InlineKeyboardMarkup:
    workout_days = get_month_workout_days(user_id, year, month)
    keyboard: list[list[InlineKeyboardButton]] = []

    header = InlineKeyboardButton(text=f"{MONTH_NAMES[month]} {year}", callback_data="noop")
    keyboard.append([header])

    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(text=d, callback_data="noop") for d in week_days])

    month_calendar = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                marker = "●" if day in workout_days else ""
                row.append(
                    InlineKeyboardButton(
                        text=f"{day}{marker}",
                        callback_data=f"cal_day:{year}-{month:02d}-{day:02d}",
                    )
                )
        keyboard.append(row)

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month % 12 + 1
    next_year = year + 1 if month == 12 else year

    keyboard.append(
        [
            InlineKeyboardButton(
                text="◀️", callback_data=f"cal_nav:{prev_year}-{prev_month:02d}"
            ),
            InlineKeyboardButton(text="Закрыть", callback_data="cal_close"),
            InlineKeyboardButton(
                text="▶️", callback_data=f"cal_nav:{next_year}-{next_month:02d}"
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_day_actions_keyboard(workouts: list[Workout], target_date: date) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for w in workouts:
        label = f"{w.exercise} ({w.count})"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {label}", callback_data=f"wrk_edit:{w.id}"
                ),
                InlineKeyboardButton(
                    text=f"🗑 {label}", callback_data=f"wrk_del:{w.id}"
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к календарю",
                callback_data=f"cal_back:{target_date.year}-{target_date.month:02d}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_calendar(message: Message, user_id: str, year: int | None = None, month: int | None = None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    keyboard = build_calendar_keyboard(user_id, year, month)
    await message.answer(
        "📆 Выбери день, чтобы посмотреть, изменить или удалить тренировку:",
        reply_markup=keyboard,
    )


async def show_day_workouts(message: Message, user_id: str, target_date: date):
    workouts = get_workouts_for_day(user_id, target_date)
    if not workouts:
        await message.answer(
            f"{target_date.strftime('%d.%m.%Y')}: нет тренировок.",
            reply_markup=build_day_actions_keyboard([], target_date),
        )
        return

    text = [f"📅 {target_date.strftime('%d.%m.%Y')} — тренировки:"]
    for w in workouts:
        variant_text = f" ({w.variant})" if w.variant else ""
        text.append(f"• {w.exercise}{variant_text}: {w.count}")

    await message.answer(
        "\n".join(text), reply_markup=build_day_actions_keyboard(workouts, target_date)
    )


def start_date_selection(bot, context: str):
    """Сохраняет контекст выбора даты (тренировка/вес/замеры)."""
    bot.date_selection_context = context
    bot.selected_date = date.today()
    bot.expecting_date_input = False


def get_date_prompt(context: str) -> str:
    prompts = {
        "training": "За какой день добавить тренировку?",
        "weight": "За какой день добавить вес?",
        "measurements": "За какой день добавить замеры?",
    }
    return prompts.get(context, "За какую дату сделать запись?")


def get_other_day_prompt(context: str) -> str:
    prompts = {
        "training": "Выбери день тренировки или введи дату вручную:",
        "weight": "Выбери день для записи веса или введи дату вручную:",
        "measurements": "Выбери день для замеров или введи дату вручную:",
    }
    return prompts.get(context, "Выбери нужный день или введи дату вручную:")


async def proceed_after_date_selection(message: Message):
    context = getattr(message.bot, "date_selection_context", "training")
    selected_date = getattr(message.bot, "selected_date", date.today())
    date_text = selected_date.strftime("%d.%m.%Y")

    if context == "training":
        await message.answer(f"📅 Выбрана дата: {date_text}")
        await message.answer("Теперь выбери упражнение:", reply_markup=exercise_menu)
    elif context == "weight":
        message.bot.expecting_weight = True
        await message.answer(f"📅 Выбрана дата: {date_text}")
        await message.answer("Введи свой вес в килограммах (например: 72.5):")
    elif context == "measurements":
        message.bot.expecting_measurements = True
        await message.answer(f"📅 Выбрана дата: {date_text}")
        await message.answer(
            "Введи замеры в формате:\n\n"
            "грудь=100, талия=80, руки=35\n\n"
            "Можно указать только нужные параметры."
        )



# -------------------- keyboards --------------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Тренировка"), KeyboardButton(text="🍱 КБЖУ")],
        [KeyboardButton(text="⚖️ Вес / 📏 Замеры"), KeyboardButton(text="💊 Добавки")],
        [KeyboardButton(text="📆 Календарь")],
        [KeyboardButton(text="💬 Обратная связь")]
    ],
    resize_keyboard=True
)

# Подменю "Тренировка"
training_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить тренировку")],
        [KeyboardButton(text="🏋️ История тренировок")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
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
        [KeyboardButton(text="⬅️ Назад")]
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

count_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="5"), KeyboardButton(text="8"), KeyboardButton(text="10")
        ],
        [
            KeyboardButton(text="12"), KeyboardButton(text="15"), KeyboardButton(text="20")
        ],
        [
            KeyboardButton(text="✏️ Ввести вручную"), KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)


my_data_menu = ReplyKeyboardMarkup(
    keyboard=[
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
        [KeyboardButton(text="🗑 Удалить вес")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)


measurements_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить замеры")],
        [KeyboardButton(text="🗑 Удалить замеры")],
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




@dp.message(F.text == "🏋️ Тренировка")
async def show_training_menu(message: Message):
    await message.answer("Выбери действие:", reply_markup=training_menu)

@dp.message(F.text == "➕ Добавить тренировку")
async def show_add_training_menu(message: Message):
    start_date_selection(message.bot, "training")
    await message.answer(get_date_prompt("training"), reply_markup=training_date_menu)

@dp.message(F.text == "📅 Сегодня")
async def add_training_today(message: Message):
    message.bot.selected_date = date.today()
    await proceed_after_date_selection(message)

@dp.message(F.text == "📆 Другой день")
async def add_training_other_day(message: Message):
    context = getattr(message.bot, "date_selection_context", "training")
    await message.answer(get_other_day_prompt(context), reply_markup=other_day_menu)

@dp.message(F.text == "📅 Вчера")
async def training_yesterday(message: Message):
    message.bot.selected_date = date.today() - timedelta(days=1)
    await proceed_after_date_selection(message)


@dp.message(F.text == "📆 Позавчера")
async def training_day_before_yesterday(message: Message):
    message.bot.selected_date = date.today() - timedelta(days=2)
    await proceed_after_date_selection(message)


@dp.message(F.text == "✏️ Ввести дату вручную")
async def enter_custom_date(message: Message):
    message.bot.expecting_date_input = True
    await message.answer("Введи дату в формате ДД.ММ.ГГГГ:")

@dp.message(F.text.regexp(r"^\d{2}\.\d{2}\.\d{4}$"), lambda m: getattr(m.bot, "expecting_date_input", False))
async def handle_custom_date(message: Message):
    try:
        entered_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        message.bot.selected_date = entered_date
        message.bot.expecting_date_input = False
        await proceed_after_date_selection(message)
    except ValueError:
        await message.answer("⚠️ Неверный формат. Попробуй так: 31.10.2025")


@dp.message(F.text.in_(["Подтягивания", "Отжимания", "Приседания", "Пресс", "Берпи", "Шаги", "Пробежка", "Скакалка", "Другое"]))
async def choose_exercise(message: Message):
    message.bot.current_exercise = message.text

    # обрабатываем "Другое"
    if message.text == "Другое":
        message.bot.current_variant = "Без варианта"
        await message.answer("Введи название упражнения:")
        message.bot.expecting_custom_exercise = True
        return

    # особые случаи (оставляем как есть)
    elif message.text == "Шаги":
        message.bot.current_variant = "Количество шагов"
        await message.answer("Сколько шагов сделал? Введи число:")
        return
    elif message.text == "Пробежка":
        message.bot.current_variant = "Минуты"
        await message.answer("Сколько минут пробежал? Введи число:")
        return
    elif message.text == "Скакалка":
        message.bot.current_variant = "Количество прыжков"
        await message.answer("Сколько раз прыгал на скакалке? Введи число:")
        return

    # обычные упражнения
    message.bot.current_variant = "Без варианта"
    await message.answer("Выбери количество повторений:", reply_markup=count_menu)

@dp.message(F.text == "✏️ Ввести вручную")
async def enter_manual_count(message: Message):
    await message.answer("Введи количество повторений числом:")


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


@dp.message(F.text.regexp(r"^\d+$"), lambda m: not getattr(m.bot, "expecting_weight", False))
async def process_number(message: Message):
    user_id = str(message.from_user.id)
    number = int(message.text)


    if getattr(message.bot, "expecting_edit_workout_id", False):
        workout_id = message.bot.expecting_edit_workout_id
        session = SessionLocal()
        try:
            workout = session.query(Workout).filter_by(id=workout_id, user_id=user_id).first()
            if not workout:
                await message.answer("Не нашёл тренировку для изменения.")
            else:
                workout.count = number
                session.commit()
                target_date = workout.date
                await message.answer(
                    f"✏️ Обновил: {workout.exercise} — теперь {number} (от {target_date.strftime('%d.%m.%Y')})"
                )
                await show_day_workouts(message, user_id, target_date)
        finally:
            session.close()

        message.bot.expecting_edit_workout_id = False
        return


    # --- режим удаления веса ---
    if getattr(message.bot, "expecting_weight_delete", False):
        index = number - 1
        if 0 <= index < len(message.bot.user_weights):
            entry = message.bot.user_weights[index]

            session = SessionLocal()
            weight = session.query(Weight).filter_by(
                user_id=user_id,
                value=entry.value,
                date=entry.date
            ).first()

            if weight:
                session.delete(weight)
                session.commit()
                session.close()
                message.bot.user_weights.pop(index)
                await message.answer(f"✅ Удалил запись: {entry.date.strftime('%d.%m.%Y')} — {entry.value} кг")
            else:
                session.close()
                await message.answer("❌ Не нашёл такую запись в базе.")

        else:
            await message.answer("⚠️ Нет такой записи.")
        message.bot.expecting_weight_delete = False
        return

    # --- режим удаления замеров ---
    if getattr(message.bot, "expecting_measurement_delete", False):
        index = number - 1
        if 0 <= index < len(message.bot.user_measurements):
            entry = message.bot.user_measurements[index]

            session = SessionLocal()
            m = session.query(Measurement).filter_by(
                user_id=user_id,
                date=entry.date
            ).first()

            if m:
                session.delete(m)
                session.commit()
                session.close()
                message.bot.user_measurements.pop(index)
                await message.answer(f"✅ Удалил замеры от {entry.date.strftime('%d.%m.%Y')}")
            else:
                session.close()
                await message.answer("❌ Не нашёл такие замеры в базе.")

        else:
            await message.answer("⚠️ Нет такой записи.")
        message.bot.expecting_measurement_delete = False
        return


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
                await message.answer(f"Удалил: {entry.exercise} ({entry.variant}) - {entry.count}")
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
                    f"Удалил из истории: {entry.date} — {entry.exercise} ({entry.variant}) - {entry.count}"
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
    # если пользователь выбрал дату ранее — сохраняем на неё
    selected_date = getattr(message.bot, "selected_date", date.today())

    new_workout = Workout(
        user_id=user_id,
        exercise=exercise,
        variant=variant,
        count=count,
        date=selected_date
    )

    session.add(new_workout)
    session.commit()

    # Считаем общее количество по выбранной дате
    total_for_date = (
        session.query(Workout)
        .filter_by(user_id=user_id, exercise=exercise, date=selected_date)
        .with_entities(func.sum(Workout.count))
        .scalar()
    ) or 0

    session.close()

    date_label = (
        "сегодня" if selected_date == date.today() else selected_date.strftime("%d.%m.%Y")
    )

    await message.answer(
        f"Записал! 👍\nВсего {exercise} за {date_label}: {total_for_date} повторений"
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
    start_date_selection(message.bot, "weight")
    await message.answer(get_date_prompt("weight"), reply_markup=training_date_menu)

@dp.message(F.text == "🗑 Удалить вес")
async def delete_weight_start(message: Message):
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
        await message.answer("⚖️ У тебя нет записей веса для удаления.", reply_markup=weight_menu)
        return

    # сохраняем в оперативную память
    message.bot.expecting_weight_delete = True
    message.bot.user_weights = weights

    text = "Выбери номер веса для удаления:\n\n"
    for i, w in enumerate(weights, 1):
        text += f"{i}. {w.date.strftime('%d.%m.%Y')} — {w.value} кг\n"

    await message.answer(text)


@dp.message(F.text.regexp(r"^\d+([.,]\d+)?$"))
async def process_weight_or_number(message: Message):
    user_id = str(message.from_user.id)

    # --- если ждём ввод веса ---
    if getattr(message.bot, "expecting_weight", False):
        weight_value = float(message.text.replace(",", "."))  # поддержка 72,5 тоже
        selected_date = getattr(message.bot, "selected_date", date.today())
        add_weight(user_id, weight_value, selected_date)
        message.bot.expecting_weight = False
        await message.answer(
            f"✅ Записал вес {weight_value} кг за {selected_date.strftime('%d.%m.%Y')}",
            reply_markup=weight_menu
        )
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
    start_date_selection(message.bot, "measurements")
    await message.answer(get_date_prompt("measurements"), reply_markup=training_date_menu)

@dp.message(F.text == "🗑 Удалить замеры")
async def delete_measurements_start(message: Message):
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
        await message.answer("📏 У тебя нет замеров для удаления.", reply_markup=measurements_menu)
        return

    message.bot.expecting_measurement_delete = True
    message.bot.user_measurements = measurements

    text = "Выбери номер замеров для удаления:\n\n"
    for i, m in enumerate(measurements, 1):
        parts = []
        if m.chest:
            parts.append(f"Грудь: {m.chest}")
        if m.waist:
            parts.append(f"Талия: {m.waist}")
        if m.hips:
            parts.append(f"Бёдра: {m.hips}")
        if m.biceps:
            parts.append(f"Бицепс: {m.biceps}")
        if m.thigh:
            parts.append(f"Бедро: {m.thigh}")

        summary = ", ".join(parts) if parts else "нет данных"
        text += f"{i}. {m.date.strftime('%d.%m.%Y')} — {summary}\n"

    await message.answer(text)


@dp.message(F.text, lambda m: getattr(m.bot, "expecting_measurements", False))
async def process_measurements(message: Message):
    user_id = str(message.from_user.id)
    raw = message.text

    try:
        # разбиваем на части: "грудь=100, талия=80, руки=35"
        parts = [p.strip() for p in raw.replace(",", " ").split()]
        if not parts:
            raise ValueError

        # нормализация и маппинг ключей к полям модели
        key_map = {
            "грудь": "chest", "груд": "chest",
            "талия": "waist", "талияю": "waist",
            "бёдра": "hips", "бедра": "hips", "бёдро": "thigh", "бедро": "thigh",
            "руки": "biceps", "бицепс": "biceps", "бицепсы": "biceps",
            "бедро": "thigh"
        }

        measurements_mapped = {}
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if not v:
                    continue
                # заменить запятую на точку для чисел
                val = float(v.replace(",", "."))
                field = key_map.get(k, None)
                if field:
                    measurements_mapped[field] = val
                else:
                    # если ключ не в маппинге — пробуем использовать как есть (безопасно)
                    measurements_mapped[k] = val

        if not measurements_mapped:
            raise ValueError
    except Exception:
        await message.answer("⚠️ Неверный формат. Попробуй так: грудь=100, талия=80, руки=35")
        return

    # сохраняем в базу (функция ниже принимает маппинг полей модели)
    try:
        selected_date = getattr(message.bot, "selected_date", date.today())
        add_measurements(user_id, measurements_mapped, selected_date)
    except Exception as e:
        # на случай неожиданной ошибки — лог в консоль и сообщение пользователю
        print("Error saving measurements:", e)
        await message.answer("⚠️ Ошибка при сохранении. Повтори попытку позже.")
        message.bot.expecting_measurements = False
        return

    message.bot.expecting_measurements = False
    await message.answer(
        "✅ Замеры сохранены: {data} ({date})".format(
            data=measurements_mapped,
            date=getattr(message.bot, "selected_date", date.today()).strftime("%d.%m.%Y")
        ),
        reply_markup=measurements_menu
    )



@dp.message(F.text == "📊 История событий")
async def my_data(message: Message):
    await message.answer("Выбери, что посмотреть:", reply_markup=my_data_menu)


@dp.message(F.text == "⬅️ Назад")
async def go_back(message: Message):
    user_id = str(message.from_user.id)
    # сбрасываем все флаги ожидания, чтобы неожиданные нажатия не шли в парсеры
    for attr in [
        "expecting_measurements",
        "expecting_weight",
        "expecting_delete",
        "expecting_history_delete",
        "expecting_weight_delete",
        "expecting_measurement_delete",
        "expecting_custom_exercise",
        "expecting_date_input",
        "expecting_edit_workout_id",
        "expecting_supplement_name",
        "expecting_supplement_time",
        "selecting_days",
    ]:
        if hasattr(message.bot, attr):
            try:
                setattr(message.bot, attr, False)
            except Exception:
                pass

    # (опционально) удалить временные списки из оперативной памяти
    for list_attr in ["user_weights", "user_measurements", "todays_workouts", "history_workouts"]:
        if hasattr(message.bot, list_attr):
            try:
                delattr(message.bot, list_attr)
            except Exception:
                pass

    for context_attr in ["date_selection_context", "selected_date"]:
        if hasattr(message.bot, context_attr):
            try:
                delattr(message.bot, context_attr)
            except Exception:
                pass

    for calendar_attr in ["edit_workout_date", "edit_calendar_month"]:
        if hasattr(message.bot, calendar_attr):
            try:
                delattr(message.bot, calendar_attr)
            except Exception:
                pass

    if hasattr(message.bot, "active_supplement"):
        try:
            message.bot.active_supplement.pop(user_id, None)
        except Exception:
            pass

    text = get_today_summary_text(user_id)
    await message.answer(text, reply_markup=main_menu)


@dp.message(F.text == "⚖️ Вес / 📏 Замеры")
async def weight_and_measurements(message: Message):
    await message.answer("Выбери, что хочешь посмотреть:", reply_markup=my_data_menu)


def get_user_supplements(message: Message) -> list[dict]:
    if not hasattr(message.bot, "supplements"):
        message.bot.supplements = {}
    return message.bot.supplements.setdefault(str(message.from_user.id), [])


def reset_supplement_state(message: Message):
    for flag in [
        "expecting_supplement_name",
        "expecting_supplement_time",
        "selecting_days",
    ]:
        if hasattr(message.bot, flag):
            setattr(message.bot, flag, False)

    if hasattr(message.bot, "active_supplement"):
        message.bot.active_supplement.pop(str(message.from_user.id), None)


def get_active_supplement(message: Message) -> dict:
    user_id = str(message.from_user.id)
    if not hasattr(message.bot, "active_supplement"):
        message.bot.active_supplement = {}
    return message.bot.active_supplement.setdefault(
        user_id,
        {"name": "", "times": [], "days": [], "duration": "постоянно", "ready": False},
    )


def supplements_main_menu(has_items: bool = False) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text="➕ Создать добавку")]]
    if has_items:
        buttons.append([KeyboardButton(text="✏️ Редактировать добавку"), KeyboardButton(text="📜 История добавок")])
    buttons.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@dp.message(F.text == "💊 Добавки")
async def supplements(message: Message):
    supplements_list = get_user_supplements(message)
    if not supplements_list:
        await message.answer(
            "💊 Добавки\n\n"
            "Привет! Здесь ты можешь записывать свои добавки, получать статистику записей и при желании включить напоминания, чтобы ничего не забыть.",
            reply_markup=supplements_main_menu(has_items=False),
        )
        return

    lines = ["Мои добавки"]
    for item in supplements_list:
        days = ", ".join(item["days"]) if item["days"] else "не выбрано"
        times = ", ".join(item["times"]) if item["times"] else "не выбрано"
        lines.append(
            f"\n💊 {item['name']} \n⏰ Время приема: {times}\n📅 Дни приема: {days}\n⏳ Длительность: {item['duration']}"
        )
    await message.answer("\n".join(lines), reply_markup=supplements_main_menu(has_items=True))


@dp.message(F.text == "➕ Создать добавку")
async def start_create_supplement(message: Message):
    reset_supplement_state(message)
    message.bot.expecting_supplement_name = True
    sup = get_active_supplement(message)
    sup.update({"name": "", "times": [], "days": [], "duration": "постоянно", "ready": False})
    await message.answer("Введите название добавки.")


@dp.message(lambda m: getattr(m.bot, "expecting_supplement_name", False))
async def handle_supplement_name(message: Message):
    sup = get_active_supplement(message)
    sup["name"] = message.text.strip()
    sup["ready"] = False
    message.bot.expecting_supplement_name = False
    await message.answer(
        "Выберите время, дни и длительность приема добавки:",
        reply_markup=supplement_edit_menu(show_save=False),
    )


@dp.message(F.text == "✏️ Редактировать время")
async def edit_supplement_time(message: Message):
    sup = get_active_supplement(message)
    if not sup["times"]:
        await message.answer(
            f"ℹ️ Добавьте первое время приема для {sup['name']}",
            reply_markup=time_first_menu(),
        )
        return

    await message.answer(
        f"ℹ️ Добавьте время приема или удалите лишнее для {sup['name']}",
        reply_markup=time_edit_menu(sup["times"]),
    )


@dp.message(F.text == "➕ Добавить")
async def ask_time_value(message: Message):
    if getattr(message.bot, "selecting_days", False):
        return
    sup = get_active_supplement(message)
    sup["ready"] = False
    message.bot.expecting_supplement_time = True
    await message.answer("Введите время приема в формате ЧЧ:ММ\nНапример: 09:00")


@dp.message(lambda m: getattr(m.bot, "expecting_supplement_time", False))
async def handle_time_value(message: Message):
    text = message.text.strip()
    import re

    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", text):
        await message.answer("Пожалуйста, укажите время в формате ЧЧ:ММ. Например: 09:00")
        return

    sup = get_active_supplement(message)
    sup["ready"] = False
    if text not in sup["times"]:
        sup["times"].append(text)
    sup["times"].sort()
    message.bot.expecting_supplement_time = False

    times_list = "\n".join(sup["times"])
    await message.answer(
        f"💊 {sup['name']}\n\nРасписание приема:\n{times_list}\n\nℹ️ Нажмите ❌ чтобы удалить время",
        reply_markup=time_edit_menu(sup["times"]),
    )


@dp.message(F.text.startswith("❌ "))
async def delete_time(message: Message):
    sup = get_active_supplement(message)
    sup["ready"] = False
    time_value = message.text.replace("❌ ", "").strip()
    if time_value in sup["times"]:
        sup["times"].remove(time_value)

    if sup["times"]:
        await message.answer(
            f"Обновленное расписание:\n{chr(10).join(sup['times'])}",
            reply_markup=time_edit_menu(sup["times"]),
        )
    else:
        await message.answer(
            f"ℹ️ Добавьте первое время приема для {sup['name']}",
            reply_markup=time_first_menu(),
        )


@dp.message(F.text == "💾 Сохранить")
async def save_time_or_supplement(message: Message):
    sup = get_active_supplement(message)
    if getattr(message.bot, "expecting_supplement_time", False):
        message.bot.expecting_supplement_time = False

    if getattr(message.bot, "selecting_days", False):
        message.bot.selecting_days = False
        sup["ready"] = True
        await message.answer(supplement_schedule_prompt(sup), reply_markup=supplement_edit_menu(show_save=True))
        return

    if not sup.get("ready"):
        sup["ready"] = True
        await message.answer(
            supplement_schedule_prompt(sup),
            reply_markup=supplement_edit_menu(show_save=True),
        )
        return

    supplements_list = get_user_supplements(message)
    supplements_list.append({
        "name": sup["name"],
        "times": sup["times"].copy(),
        "days": sup["days"].copy(),
        "duration": sup["duration"],
    })

    reset_supplement_state(message)

    await message.answer(
        "Мои добавки\n\n"
        f"💊 {supplements_list[-1]['name']} \n"
        f"⏰ Время приема: {', '.join(supplements_list[-1]['times']) or 'не выбрано'}\n"
        f"📅 Дни приема: {', '.join(supplements_list[-1]['days']) or 'не выбрано'}\n"
        f"⏳ Длительность: {supplements_list[-1]['duration']}",
        reply_markup=supplements_main_menu(has_items=True),
    )


@dp.message(F.text == "📅 Редактировать дни")
async def edit_days(message: Message):
    sup = get_active_supplement(message)
    message.bot.selecting_days = True
    await message.answer(
        "Выберите дни приема:\nНажмите на день для выбора",
        reply_markup=days_menu(sup["days"]),
    )


@dp.message(lambda m: getattr(m.bot, "selecting_days", False) and m.text.replace("✅ ", "") in {"Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"})
async def toggle_day(message: Message):
    sup = get_active_supplement(message)
    sup["ready"] = False
    day = message.text.replace("✅ ", "")
    if day in sup["days"]:
        sup["days"].remove(day)
    else:
        sup["days"].append(day)

    await message.answer("Дни обновлены", reply_markup=days_menu(sup["days"]))


@dp.message(lambda m: getattr(m.bot, "selecting_days", False) and m.text == "Выбрать все")
async def select_all_days(message: Message):
    sup = get_active_supplement(message)
    sup["ready"] = False
    sup["days"] = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    await message.answer("Все дни выбраны", reply_markup=days_menu(sup["days"]))


@dp.message(F.text == "⏳ Длительность приема")
async def choose_duration(message: Message):
    await message.answer("Выберите длительность приема", reply_markup=duration_menu())


@dp.message(lambda m: m.text in {"Постоянно", "14 дней", "30 дней"})
async def set_duration(message: Message):
    sup = get_active_supplement(message)
    sup["duration"] = message.text.lower()
    sup["ready"] = True
    await message.answer(
        supplement_schedule_prompt(sup),
        reply_markup=supplement_edit_menu(show_save=True),
    )


@dp.message(F.text == "⬅️ Вернуться")
async def back_from_supplement_steps(message: Message):
    if getattr(message.bot, "selecting_days", False):
        message.bot.selecting_days = False
        sup = get_active_supplement(message)
        sup["ready"] = True
        await message.answer(
            supplement_schedule_prompt(sup),
            reply_markup=supplement_edit_menu(show_save=True),
        )
        return

    await supplements(message)


@dp.message(F.text == "⬅️ Отменить")
async def cancel_supplement(message: Message):
    reset_supplement_state(message)
    await supplements(message)


@dp.message(F.text == "✏️ Редактировать добавку")
async def edit_supplement_placeholder(message: Message):
    supplements_list = get_user_supplements(message)
    if not supplements_list:
        await message.answer("Пока нет добавок для редактирования.", reply_markup=supplements_main_menu(False))
        return
    await message.answer("Редактирование добавок скоро появится. Вы можете создать новые записи сейчас.", reply_markup=supplements_main_menu(True))


@dp.message(F.text == "📜 История добавок")
async def supplements_history(message: Message):
    supplements_list = get_user_supplements(message)
    if not supplements_list:
        await message.answer("История добавок пуста.", reply_markup=supplements_main_menu(False))
        return
    lines = ["Последние добавки"]
    for item in supplements_list:
        days = ", ".join(item["days"]) if item["days"] else "не выбрано"
        times = ", ".join(item["times"]) if item["times"] else "не выбрано"
        lines.append(
            f"💊 {item['name']} — {times}; дни: {days}; длительность: {item['duration']}"
        )
    await message.answer("\n".join(lines), reply_markup=supplements_main_menu(True))


def supplement_schedule_prompt(sup: dict) -> str:
    times = ", ".join(sup["times"]) if sup["times"] else "не выбрано"
    days = ", ".join(sup["days"]) if sup["days"] else "не выбрано"
    return (
        f"💊 {sup['name']}\n\n"
        f"⏰ Время приема: {times}\n"
        f"📅 Дни приема: {days}\n"
        f"⏳ Длительность: {sup['duration']}\n\n"
        "ℹ️ Выберите время и дни приема для сохранения"
    )


def supplement_edit_menu(show_save: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="✏️ Редактировать время"), KeyboardButton(text="📅 Редактировать дни")],
        [KeyboardButton(text="⏳ Длительность приема")],
    ]
    if show_save:
        buttons.append([KeyboardButton(text="💾 Сохранить")])
    buttons.append([KeyboardButton(text="⬅️ Отменить")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def time_edit_menu(times: list[str]) -> ReplyKeyboardMarkup:
    buttons: list[list[KeyboardButton]] = []
    for t in times:
        buttons.append([KeyboardButton(text=f"❌ {t}")])
    buttons.append([KeyboardButton(text="➕ Добавить"), KeyboardButton(text="💾 Сохранить")])
    buttons.append([KeyboardButton(text="⬅️ Вернуться")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def time_first_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="➕ Добавить"), KeyboardButton(text="⬅️ Вернуться")]],
        resize_keyboard=True,
    )


def days_menu(selected: list[str]) -> ReplyKeyboardMarkup:
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    rows = []
    for day in week_days:
        prefix = "✅ " if day in selected else ""
        rows.append([KeyboardButton(text=f"{prefix}{day}")])
    rows.append([KeyboardButton(text="Выбрать все"), KeyboardButton(text="💾 Сохранить")])
    rows.append([KeyboardButton(text="⬅️ Вернуться")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def duration_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Постоянно"), KeyboardButton(text="14 дней")],
            [KeyboardButton(text="30 дней")],
            [KeyboardButton(text="⬅️ Вернуться")],
        ],
        resize_keyboard=True,
    )


@dp.message(F.text == "🍱 КБЖУ")
async def calories(message: Message):
    await message.answer("🍱 Раздел КБЖУ в разработке 💭")


@dp.message(F.text == "📆 Календарь")
async def calendar_view(message: Message):
    user_id = str(message.from_user.id)
    await show_calendar(message, user_id)


@dp.callback_query(F.data == "cal_close")
async def close_calendar(callback: CallbackQuery):
    await callback.answer("Календарь закрыт")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@dp.callback_query(F.data == "noop")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data.startswith("cal_nav:"))
async def navigate_calendar(callback: CallbackQuery):
    await callback.answer()
    _, ym = callback.data.split(":", 1)
    year, month = map(int, ym.split("-"))
    user_id = str(callback.from_user.id)
    await callback.message.edit_reply_markup(
        reply_markup=build_calendar_keyboard(user_id, year, month)
    )


@dp.callback_query(F.data.startswith("cal_back:"))
async def back_to_calendar(callback: CallbackQuery):
    await callback.answer()
    _, ym = callback.data.split(":", 1)
    year, month = map(int, ym.split("-"))
    user_id = str(callback.from_user.id)
    await show_calendar(callback.message, user_id, year, month)


@dp.callback_query(F.data.startswith("cal_day:"))
async def select_calendar_day(callback: CallbackQuery):
    await callback.answer()
    _, date_str = callback.data.split(":", 1)
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    callback.bot.edit_calendar_month = date(target_date.year, target_date.month, 1)
    await show_day_workouts(callback.message, str(callback.from_user.id), target_date)


@dp.callback_query(F.data.startswith("wrk_del:"))
async def delete_workout(callback: CallbackQuery):
    await callback.answer()
    workout_id = int(callback.data.split(":", 1)[1])
    user_id = str(callback.from_user.id)

    session = SessionLocal()
    try:
        workout = session.query(Workout).filter_by(id=workout_id, user_id=user_id).first()
        if not workout:
            await callback.message.answer("Не нашёл такую запись для удаления.")
            return

        target_date = workout.date
        session.delete(workout)
        session.commit()
    finally:
        session.close()

    await callback.message.answer(
        f"🗑 Удалил: {target_date.strftime('%d.%m.%Y')} — {workout.exercise} ({workout.count})"
    )
    await show_day_workouts(callback.message, user_id, target_date)


@dp.callback_query(F.data.startswith("wrk_edit:"))
async def edit_workout(callback: CallbackQuery):
    await callback.answer()
    workout_id = int(callback.data.split(":", 1)[1])
    user_id = str(callback.from_user.id)

    session = SessionLocal()
    try:
        workout = session.query(Workout).filter_by(id=workout_id, user_id=user_id).first()
    finally:
        session.close()

    if not workout:
        await callback.message.answer("Не нашёл тренировку для изменения.")
        return

    callback.bot.expecting_edit_workout_id = workout_id
    callback.bot.edit_workout_date = workout.date
    await callback.message.answer(
        f"✏️ Введи новое количество для {workout.exercise} от {workout.date.strftime('%d.%m.%Y')}"
    )


@dp.message(F.text == "💬 Обратная связь")
async def feedback(message: Message):
    await message.answer("💬 Раздел обратной связи в разработке 💭")


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
