import os
from dataclasses import dataclass, field
from datetime import time

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_id: int = int(os.getenv("ADMIN_ID", "0"))
    tz: str = os.getenv("TIMEZONE", "Europe/Moscow")

    # Путь к файлу БД
    db_path: str = "barbershop.db"

    # Начальный график работы — засеивается в БД при ПЕРВОМ запуске.
    # Дальше график меняется через /settings и хранится в таблице work_schedule.
    # Ключ — день недели (0 = понедельник ... 6 = воскресенье).
    # Значение — (открытие, закрытие) или None, если выходной.
    work_hours: dict = field(
        default_factory=lambda: {
            0: (time(10, 0), time(20, 0)),
            1: (time(10, 0), time(20, 0)),
            2: (time(10, 0), time(20, 0)),
            3: (time(10, 0), time(20, 0)),
            4: (time(10, 0), time(20, 0)),
            5: (time(10, 0), time(20, 0)),
            6: (time(11, 0), time(18, 0)),
        }
    )

    # На сколько дней вперёд открыта запись
    booking_days_ahead: int = 14

    # За сколько часов до визита отправлять напоминание
    reminder_hours_before: int = 3

    # Антиспам
    throttle_seconds: float = 0.7          # минимальный интервал между действиями
    max_active_bookings: int = 2           # макс. активных записей на пользователя

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN не задан. Заполните .env по образцу .env.example")
        if not self.admin_id:
            raise RuntimeError("ADMIN_ID не задан. Заполните .env по образцу .env.example")


config = Config()

# Шаг сетки записи по умолчанию, мин. 0 = использовать длительность услуги.
DEFAULT_SLOT_STEP = 0

# Услуги по умолчанию (засеиваются в БД при первом запуске).
# (название, длительность в минутах, цена)
DEFAULT_SERVICES = [
    ("Мужская стрижка", 40, 1200),
    ("Стрижка бороды", 20, 700),
    ("Стрижка + борода", 60, 1700),
    ("Детская стрижка", 30, 900),
    ("Бритьё опасной бритвой", 30, 1000),
]
