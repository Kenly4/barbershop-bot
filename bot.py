import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database.db import init_db
from handlers import admin, booking, common, my_bookings, settings
from middlewares.throttling import ThrottlingMiddleware
from services.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    config.validate()
    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Антиспам на сообщения и колбэки
    throttling = ThrottlingMiddleware()
    dp.message.middleware(throttling)
    dp.callback_query.middleware(throttling)

    # Порядок роутеров: настройки/админ → общий → запись → мои записи
    dp.include_router(settings.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(booking.router)
    dp.include_router(my_bookings.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    logging.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
