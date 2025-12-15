"""Обработчики для настроек."""
import logging
from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from utils.keyboards import settings_menu, delete_account_confirm_menu, push_menu_stack, main_menu_button
from database.session import get_db_session

logger = logging.getLogger(__name__)

router = Router()


def reset_user_state(message: Message, *, keep_supplements: bool = False):
    """Сбрасывает состояние пользователя (упрощённая версия)."""
    # TODO: Заменить на FSM состояния
    pass


def delete_user_account(user_id: str) -> bool:
    """Удаляет аккаунт пользователя и все связанные данные."""
    # TODO: Реализовать полное удаление всех данных пользователя
    # Пока заглушка
    logger.warning(f"Delete account requested for user {user_id} (not implemented)")
    return False


@router.message(lambda m: m.text == "⚙️ Настройки")
async def settings(message: Message):
    """Показывает меню настроек."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened settings")
    
    push_menu_stack(message.bot, settings_menu)
    await message.answer(
        "⚙️ Настройки\n\nВыбери действие:",
        reply_markup=settings_menu,
    )


@router.message(lambda m: m.text == "🗑 Удалить аккаунт")
async def delete_account_start(message: Message):
    """Начинает процесс удаления аккаунта."""
    reset_user_state(message)
    message.bot.expecting_account_deletion_confirm = True
    user_id = str(message.from_user.id)
    logger.warning(f"User {user_id} initiated account deletion")
    
    push_menu_stack(message.bot, delete_account_confirm_menu)
    await message.answer(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы уверены, что хотите удалить аккаунт?\n\n"
        "При удалении аккаунта будут <b>безвозвратно удалены</b> все ваши данные:\n"
        "• Все тренировки\n"
        "• Все записи веса и замеров\n"
        "• Все записи КБЖУ\n"
        "• Все добавки и их история\n"
        "• Настройки КБЖУ\n\n"
        "Это действие нельзя отменить!",
        reply_markup=delete_account_confirm_menu,
        parse_mode="HTML",
    )


@router.message(lambda m: m.text == "✅ Да, удалить аккаунт")
async def delete_account_confirm(message: Message):
    """Подтверждает удаление аккаунта."""
    if not getattr(message.bot, "expecting_account_deletion_confirm", False):
        await message.answer("Что-то пошло не так. Попробуй заново через меню Настройки.")
        return
    
    user_id = str(message.from_user.id)
    message.bot.expecting_account_deletion_confirm = False
    logger.warning(f"User {user_id} confirmed account deletion")
    
    success = delete_user_account(user_id)
    
    if success:
        await message.answer(
            "✅ Аккаунт успешно удалён.\n\n"
            "Все ваши данные были удалены из базы данных.\n\n"
            "Если захотите вернуться, просто нажмите /start",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/start")]],
                resize_keyboard=True
            )
        )
    else:
        push_menu_stack(message.bot, settings_menu)
        await message.answer(
            "❌ Произошла ошибка при удалении аккаунта.\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=settings_menu,
        )


@router.message(lambda m: m.text == "❌ Отмена")
async def delete_account_cancel(message: Message):
    """Отменяет удаление аккаунта."""
    if getattr(message.bot, "expecting_account_deletion_confirm", False):
        message.bot.expecting_account_deletion_confirm = False
        push_menu_stack(message.bot, settings_menu)
        await message.answer(
            "❌ Удаление аккаунта отменено.",
            reply_markup=settings_menu,
        )


@router.message(lambda m: m.text == "💬 Поддержка")
async def support(message: Message):
    """Показывает информацию о поддержке."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} opened support")
    
    push_menu_stack(message.bot, settings_menu)
    await message.answer(
        "💬 Поддержка\n\n"
        "Эта функция пока в разработке. Скоро здесь можно будет связаться с поддержкой!",
        reply_markup=settings_menu,
    )


@router.message(lambda m: m.text == "🔒 Политика конфиденциальности")
async def privacy_policy(message: Message):
    """Показывает политику конфиденциальности."""
    reset_user_state(message)
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} viewed privacy policy")
    
    privacy_text = (
        "🔒 <b>Политика конфиденциальности</b>\n\n"
        "Добро пожаловать в Fitness Bot! Мы ценим вашу конфиденциальность и стремимся защищать ваши личные данные.\n\n"
        "<b>1. Сбор данных</b>\n"
        "Бот собирает и хранит следующие данные:\n"
        "• Идентификатор пользователя Telegram\n"
        "• Данные о тренировках (упражнения, количество, даты)\n"
        "• Записи веса и замеров тела\n"
        "• Записи питания (КБЖУ)\n"
        "• Информация о добавках и их приёме\n"
        "• Настройки КБЖУ и цели\n"
        "• Фотографии замеров (если загружаются)\n\n"
        "<b>2. Использование данных</b>\n"
        "Ваши данные используются исключительно для:\n"
        "• Предоставления функционала бота\n"
        "• Отображения статистики и прогресса\n"
        "• Расчёта калорий и КБЖУ\n"
        "• Хранения истории тренировок и питания\n\n"
        "<b>3. Хранение данных</b>\n"
        "Все данные хранятся в защищённой базе данных на сервере бота. "
        "Мы применяем стандартные меры безопасности для защиты вашей информации.\n\n"
        "<b>4. Передача данных третьим лицам</b>\n"
        "Мы не передаём ваши персональные данные третьим лицам. "
        "Данные используются только для работы бота и не продаются, не сдаются в аренду и не передаются другим компаниям.\n\n"
        "<b>5. Удаление данных</b>\n"
        "Вы можете в любой момент удалить свой аккаунт и все связанные данные через функцию "
        "\"🗑 Удалить аккаунт\" в настройках. После удаления все ваши данные будут безвозвратно удалены из базы данных.\n\n"
        "<b>6. Изменения в политике</b>\n"
        "Мы оставляем за собой право обновлять данную политику конфиденциальности. "
        "О существенных изменениях мы уведомим пользователей через бота.\n\n"
        "<b>7. Контакты</b>\n"
        "Если у вас есть вопросы о политике конфиденциальности, используйте функцию \"💬 Поддержка\" в настройках.\n\n"
        "Дата последнего обновления: 2024"
    )
    
    push_menu_stack(message.bot, settings_menu)
    await message.answer(privacy_text, reply_markup=settings_menu, parse_mode="HTML")


def register_settings_handlers(dp):
    """Регистрирует обработчики настроек."""
    dp.include_router(router)
