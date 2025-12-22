"""Сервис для отправки запланированных уведомлений."""
import asyncio
import logging
from datetime import datetime, time
from aiogram import Bot
from database.session import get_db_session
from database.models import User

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Планировщик уведомлений о приёмах пищи."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        
    async def send_notification(self, user_id: str, message: str):
        """Отправляет уведомление пользователю."""
        try:
            await self.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Уведомление отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
    
    async def send_meal_notifications(self, meal_type: str, message_text: str):
        """Отправляет уведомления о приёме пищи всем пользователям."""
        try:
            with get_db_session() as session:
                users = session.query(User).all()
                user_ids = [user.user_id for user in users]
            
            logger.info(f"Отправка уведомлений о {meal_type} {len(user_ids)} пользователям")
            
            # Отправляем уведомления всем пользователям
            tasks = [self.send_notification(user_id, message_text) for user_id in user_ids]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Уведомления о {meal_type} отправлены")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений о {meal_type}: {e}")
    
    def calculate_next_time(self, target_time: time) -> float:
        """Вычисляет время до следующего указанного времени в секундах."""
        now = datetime.now()
        target_datetime = datetime.combine(now.date(), target_time)
        
        # Если время уже прошло сегодня, планируем на завтра
        if now.time() >= target_time:
            from datetime import timedelta
            target_datetime += timedelta(days=1)
        
        delta = (target_datetime - now).total_seconds()
        return delta
    
    async def schedule_daily_notification(self, target_time: time, meal_type: str, message_text: str):
        """Планирует ежедневное уведомление на указанное время."""
        while self.running:
            try:
                # Вычисляем время до следующего указанного времени
                wait_seconds = self.calculate_next_time(target_time)
                
                logger.info(
                    f"Следующее уведомление о {meal_type} будет отправлено через "
                    f"{wait_seconds / 3600:.2f} часов (в {target_time})"
                )
                
                # Ждём до указанного времени
                await asyncio.sleep(wait_seconds)
                
                # Отправляем уведомления
                await self.send_meal_notifications(meal_type, message_text)
                
                # Ждём 1 секунду перед следующей итерацией (чтобы не отправлять дважды)
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info(f"Планировщик уведомлений о {meal_type} остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений о {meal_type}: {e}")
                # В случае ошибки ждём минуту перед повтором
                await asyncio.sleep(60)
    
    async def start(self):
        """Запускает планировщик уведомлений."""
        self.running = True
        logger.info("Запуск планировщика уведомлений о приёмах пищи")
        
        # Создаём задачи для каждого времени
        tasks = [
            self.schedule_daily_notification(
                time(10, 0),
                "завтрак",
                "Добавьте завтрак и Вы на один шаг приблизитесь к цели!"
            ),
            self.schedule_daily_notification(
                time(14, 0),
                "обед",
                "Добавьте обед и Вы на один шаг приблизитесь к цели!"
            ),
            self.schedule_daily_notification(
                time(20, 0),
                "ужин",
                "Добавьте ужин и Вы на один шаг приблизитесь к цели!"
            ),
        ]
        
        # Запускаем все задачи параллельно
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def stop(self):
        """Останавливает планировщик уведомлений."""
        self.running = False
        logger.info("Планировщик уведомлений остановлен")

