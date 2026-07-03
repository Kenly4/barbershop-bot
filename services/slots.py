import logging
from datetime import date as date_cls, datetime, timedelta

import pytz

from config import config
from database import repo

try:
    TZ = pytz.timezone(config.tz)
except pytz.UnknownTimeZoneError:
    logging.warning("Неизвестный часовой пояс %r, использую Europe/Moscow", config.tz)
    TZ = pytz.timezone("Europe/Moscow")


def now() -> datetime:
    return datetime.now(TZ)


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


async def available_dates() -> list[date_cls]:
    """Даты, открытые для записи (рабочие дни на N дней вперёд)."""
    schedule = await repo.get_schedule()
    today = now().date()
    result: list[date_cls] = []
    for offset in range(config.booking_days_ahead):
        d = today + timedelta(days=offset)
        day = schedule.get(d.weekday())
        if day and day["is_open"]:
            result.append(d)
    return result


async def _slot_step(duration_min: int) -> int:
    """Шаг сетки: настройка slot_step, либо длительность услуги (если 0)."""
    try:
        step = int(await repo.get_setting("slot_step", "0"))
    except ValueError:
        step = 0
    return step if step > 0 else duration_min


async def free_slots(d: date_cls, duration_min: int) -> list[str]:
    """Свободные слоты (HH:MM): по графику, без пересечений и без прошедшего времени."""
    schedule = await repo.get_schedule()
    day = schedule.get(d.weekday())
    if not day or not day["is_open"]:
        return []

    open_min = _to_min(day["open_t"])
    close_min = _to_min(day["close_t"])
    step = await _slot_step(duration_min)
    if step <= 0 or close_min <= open_min:
        return []

    # Занятые интервалы в минутах: [начало, конец)
    booked = [
        (_to_min(t), _to_min(t) + dur)
        for t, dur in await repo.get_booked_intervals(d.isoformat())
    ]
    current = now()

    result: list[str] = []
    start = open_min
    while start + duration_min <= close_min:
        end = start + duration_min
        overlaps = any(start < b_end and b_start < end for b_start, b_end in booked)
        slot_dt = TZ.localize(datetime.combine(d, datetime.min.time())) + timedelta(
            minutes=start
        )
        if not overlaps and slot_dt > current:
            result.append(_to_hhmm(start))
        start += step
    return result
