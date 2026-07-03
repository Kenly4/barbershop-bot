from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from database import repo
from services.slots import TZ
from utils.texts import fmt_date


async def _send_reminders(bot: Bot) -> None:
    now = datetime.now(TZ)
    window_end = now + timedelta(hours=config.reminder_hours_before)

    for b in await repo.get_bookings_for_reminder():
        try:
            visit = TZ.localize(
                datetime.strptime(f"{b['date']} {b['time']}", "%Y-%m-%d %H:%M")
            )
        except ValueError:
            continue
        # Напоминаем, если визит наступит в ближайшее окно, но ещё не прошёл
        if now < visit <= window_end:
            try:
                await bot.send_message(
                    b["user_tg_id"],
                    f"⏰ Напоминание о визите!\n"
                    f"✂️ {b['service_name']}\n"
                    f"📅 {fmt_date(b['date'])}, ⏰ {b['time']}\n"
                    "Ждём вас 💈",
                )
            except Exception:
                pass  # пользователь мог заблокировать бота
            await repo.mark_reminded(b["id"])


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=config.tz)
    scheduler.add_job(_send_reminders, "interval", minutes=5, args=[bot])
    return scheduler
