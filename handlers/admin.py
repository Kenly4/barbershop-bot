from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import config
from database import repo
from services import slots
from utils.texts import booking_summary, fmt_date

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id == config.admin_id


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "<b>Команды администратора</b>\n"
        "/settings — ⚙️ панель настроек (график, шаг, услуги)\n"
        "/today — записи на сегодня\n"
        "/upcoming — все предстоящие записи\n"
        "/date ГГГГ-ММ-ДД — записи на дату\n"
        "/unblock ID — разблокировать пользователя"
    )


@router.message(Command("today"))
async def admin_today(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    today = slots.now().date().isoformat()
    bookings = await repo.get_bookings_by_date(today)
    if not bookings:
        await message.answer("На сегодня записей нет.")
        return
    text = f"<b>Записи на {fmt_date(today)}:</b>\n\n" + "\n\n".join(
        booking_summary(b) for b in bookings
    )
    await message.answer(text)


@router.message(Command("upcoming"))
async def admin_upcoming(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    bookings = await repo.get_upcoming_bookings()
    if not bookings:
        await message.answer("Предстоящих записей нет.")
        return
    text = "<b>Предстоящие записи:</b>\n\n" + "\n\n".join(
        booking_summary(b) for b in bookings
    )
    await message.answer(text)


@router.message(Command("date"))
async def admin_by_date(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /date ГГГГ-ММ-ДД")
        return
    try:
        datetime.strptime(parts[1], "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверная дата. Формат: /date ГГГГ-ММ-ДД")
        return
    bookings = await repo.get_bookings_by_date(parts[1])
    if not bookings:
        await message.answer(f"На {fmt_date(parts[1])} записей нет.")
        return
    text = f"<b>Записи на {fmt_date(parts[1])}:</b>\n\n" + "\n\n".join(
        booking_summary(b) for b in bookings
    )
    await message.answer(text)


@router.message(Command("unblock"))
async def admin_unblock(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /unblock ID")
        return
    await repo.set_blocked(int(parts[1]), False)
    await message.answer(f"Пользователь {parts[1]} разблокирован.")


# ---------- Действия под уведомлением о новой записи ----------
@router.callback_query(F.data.startswith("adm:"))
async def admin_action(call: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer("Недоступно.", show_alert=True)
        return

    _, action, raw_id = call.data.split(":")
    booking_id = int(raw_id)
    booking = await repo.get_booking(booking_id)
    if not booking:
        await call.answer("Запись не найдена.", show_alert=True)
        return

    if action == "confirm":
        await repo.set_status(booking_id, "confirmed")
        await call.message.edit_text(
            "✅ Подтверждено.\n\n" + booking_summary(await repo.get_booking(booking_id))
        )
        await bot.send_message(
            booking["user_tg_id"],
            f"✅ Ваша запись #{booking_id} подтверждена!\n"
            f"📅 {fmt_date(booking['date'])}, ⏰ {booking['time']}",
        )
    elif action == "reject":
        await repo.set_status(booking_id, "cancelled")
        await call.message.edit_text(
            "❌ Отклонено.\n\n" + booking_summary(await repo.get_booking(booking_id))
        )
        await bot.send_message(
            booking["user_tg_id"],
            f"К сожалению, запись #{booking_id} отклонена. "
            "Свяжитесь с нами или выберите другое время.",
        )
    elif action == "block":
        await repo.set_blocked(booking["user_tg_id"], True)
        await repo.set_status(booking_id, "cancelled")
        await call.message.edit_text(
            f"🚫 Клиент {booking['user_tg_id']} заблокирован, запись отменена."
        )
    await call.answer()
