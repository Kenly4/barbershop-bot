"""Наполняет базу демонстрационными данными для показа проекта.

Запуск (из корня проекта):
    ./venv/bin/python -m scripts.seed_demo          # добавить демо-записи
    ./venv/bin/python -m scripts.seed_demo --reset  # пересоздать базу с нуля

Требует заполненный .env (BOT_TOKEN, ADMIN_ID) — значения могут быть любыми
для локальной демонстрации данных.
"""
import asyncio
import os
import sys
from datetime import timedelta

import aiosqlite

from config import config
from database import repo
from database.db import init_db
from services.slots import now

DEMO_CLIENTS = [
    (900000001, "Иван Петров", "+79161112233"),
    (900000002, "Артём Смирнов", "+79261114455"),
    (900000003, "Дмитрий Козлов", "+79031116677"),
    (900000004, "Максим Орлов", "+79991118899"),
]


async def _reset() -> None:
    if os.path.exists(config.db_path):
        os.remove(config.db_path)
        print(f"База {config.db_path} удалена.")


async def seed() -> None:
    await init_db()

    services = await repo.get_services()
    if not services:
        print("Нет услуг — база не инициализирована.")
        return

    for tg_id, name, phone in DEMO_CLIENTS:
        await repo.upsert_user(tg_id, name, phone)

    today = now().date()
    # Раскладываем записи по ближайшим дням в разное время
    plan = [
        (0, "11:00", 0, "confirmed"),
        (0, "13:30", 1, "pending"),
        (0, "16:00", 2, "confirmed"),
        (1, "10:30", 3, "confirmed"),
        (1, "15:00", 0, "pending"),
        (2, "12:00", 2, "confirmed"),
        (3, "14:30", 1, "confirmed"),
    ]

    created = 0
    for day_offset, time_str, svc_idx, status in plan:
        d = (today + timedelta(days=day_offset)).isoformat()
        svc = services[svc_idx % len(services)]
        client = DEMO_CLIENTS[created % len(DEMO_CLIENTS)]
        bid = await repo.create_booking(
            client[0], client[1], client[2], svc["id"], d, time_str
        )
        if bid:
            if status != "pending":
                await repo.set_status(bid, status)
            created += 1

    print(f"Готово: добавлено {created} демо-записей.")
    print("Проверьте в боте: /today, /upcoming, а также запись как клиент.")


async def main() -> None:
    if "--reset" in sys.argv:
        await _reset()
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
