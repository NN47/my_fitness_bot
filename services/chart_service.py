"""Сервис для создания графиков."""
import os
import logging
from io import BytesIO
from typing import Optional
from datetime import date

# Настройка matplotlib для быстрого запуска
os.environ['MPLCONFIGDIR'] = '/tmp/.matplotlib'

try:
    import matplotlib
    matplotlib.use('Agg')  # Используем backend без GUI
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    # Отключаем предупреждения о шрифтах
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    mdates = None

logger = logging.getLogger(__name__)


class ChartService:
    """Сервис для создания графиков."""
    
    def create_weight_chart(self, weights: list[dict], period: str) -> Optional[BytesIO]:
        """
        Создает график веса и возвращает его как BytesIO.
        
        Args:
            weights: Список словарей с ключами 'date' и 'value'
            period: Период ("week", "month", "half_year", "all_time")
            
        Returns:
            BytesIO с изображением графика или None при ошибке
        """
        if not weights:
            return None
        
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib не доступен, график не может быть создан")
            return None
        
        try:
            # Подготовка данных
            dates = [w["date"] for w in weights]
            values = [w["value"] for w in weights]
            
            # Создание графика
            plt.figure(figsize=(12, 6))
            plt.plot(dates, values, marker='o', linestyle='-', linewidth=2, markersize=6, color='#2E86AB')
            plt.fill_between(dates, values, alpha=0.3, color='#2E86AB')
            
            # Настройка осей
            plt.xlabel('Дата', fontsize=12, fontweight='bold')
            plt.ylabel('Вес (кг)', fontsize=12, fontweight='bold')
            
            # Название периода
            period_names = {
                "week": "За неделю",
                "month": "За месяц",
                "half_year": "За полгода",
                "all_time": "За все время"
            }
            plt.title(
                f'📊 График веса - {period_names.get(period, "За все время")}',
                fontsize=14,
                fontweight='bold',
                pad=20
            )
            
            # Настройка формата дат на оси X
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            plt.xticks(rotation=45, ha='right')
            
            # Сетка
            plt.grid(True, alpha=0.3, linestyle='--')
            
            # Минимальные и максимальные значения с небольшим отступом
            if values:
                min_val = min(values)
                max_val = max(values)
                range_val = max_val - min_val
                plt.ylim(max(0, min_val - range_val * 0.1), max_val + range_val * 0.1)
            
            # Добавляем значения на точки
            for i, (d, v) in enumerate(zip(dates, values)):
                if i == 0 or i == len(dates) - 1 or i % max(1, len(dates) // 5) == 0:
                    plt.annotate(
                        f'{v:.1f}',
                        (d, v),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha='center',
                        fontsize=9
                    )
            
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            logger.info(f"Created weight chart for period {period} with {len(weights)} points")
            return buf
        except Exception as e:
            logger.error(f"Ошибка при создании графика: {e}", exc_info=True)
            return None


# Глобальный экземпляр сервиса
chart_service = ChartService()
