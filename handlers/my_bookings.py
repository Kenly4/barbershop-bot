from datetime import date as date_cls

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import config
from database import repo
from keyboards.client import dates_kb, main_menu, my_bookings_kb, times_kb
from services import slots
from states.booking import RescheduleSG
from utils.texts import booking_summary, fmt_date

router = Router()


@router.callback_query(F.data == "menu:my")
async def my_bookings(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    bookings = await repo.get_user_active_bookings(call.from_user.id)
    if not bookings:
        await call.message.edit_text(
            "У вас пока нет активных записей.", reply_markup=main_menu()
        )
        await call.answer()
        return
    text = "<b>Ваши записи:</b>\n\n" + "\n\n".join(
        booking_summary(b) for b in bookings
    )
    await call.message.edit_text(text, reply_markup=my_bookings_kb(bookings))
    await call.answer()


# ---------- Отмена ----------
@router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking(call: CallbackQuery, bot: Bot) -> None:
    booking_id = int(call.data.split(":")[1])
    booking = await repo.get_booking(booking_id)
    if not booking or booking["user_tg_id"] != call.from_user.id:
        await call.answer("Запись не найдена.", show_alert=True)
        return
    if booking["status"] not in ("pending", "confirmed"):
        await call.answer("Эту запись уже нельзя отменить.", show_alert=True)
        return

    await repo.set_status(booking_id, "cancelled")
    await call.message.edit_text(
        f"❌ Запись #{booking_id} отменена.", reply_markup=main_menu()
    )
    await call.answer("Отменено")

    await bot.send_message(
        config.admin_id,
        f"⚠️ <b>Клиент отменил запись</b>\n\n" + booking_summary(booking),
    )


# ---------- Перенос ----------
@router.callback_query(F.data.startswith("resch:"))
async def start_reschedule(call: CallbackQuery, state: FSMContext) -> None:
    booking_id = int(call.data.split(":")[1])
    booking = await repo.get_booking(booking_id)
    if not booking or booking["user_tg_id"] != call.from_user.id:
        await call.answer("Запись не найдена.", show_alert=True)
        return

    await state.update_data(booking_id=booking_id, duration=booking["duration_min"])
    dates = await slots.available_dates()
    await call.message.edit_text(
        f"Перенос записи #{booking_id}.\nВыберите новую дату:",
        reply_markup=dates_kb(dates, prefix="rdate"),
    )
    await state.set_state(RescheduleSG.date)
    await call.answer()


@router.callback_query(RescheduleSG.date, F.data.startswith("rdate:"))
async def reschedule_date(call: CallbackQuery, state: FSMContext) -> None:
    iso = call.data.split(":", 1)[1]
    data = await state.get_data()
    free = await slots.free_slots(date_cls.fromisoformat(iso), data["duration"])
    if not free:
        await call.answer("На эту дату свободных слотов нет.", show_alert=True)
        return
    await state.update_data(date=iso)
    await call.message.edit_text(
        f"Новая дата: <b>{fmt_date(iso)}</b>\nВыберите время:",
        reply_markup=times_kb(free, prefix="rtime"),
    )
    await state.set_state(RescheduleSG.time)
    await call.answer()


@router.callback_query(RescheduleSG.time, F.data.startswith("rtime:"))
async def reschedule_time(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    hhmm = call.data.split(":", 1)[1]
    data = await state.get_data()
    booking_id = data["booking_id"]

    free = await slots.free_slots(date_cls.fromisoformat(data["date"]), data["duration"])
    if hhmm not in free:
        await call.answer("Это время уже заняли, выберите другое.", show_alert=True)
        return

    ok = await repo.reschedule(booking_id, data["date"], hhmm)
    if not ok:
        await call.answer("Это время уже заняли, выберите другое.", show_alert=True)
        return

    await state.clear()
    booking = await repo.get_booking(booking_id)
    await call.message.edit_text(
        f"🔁 Запись #{booking_id} перенесена:\n"
        f"📅 {fmt_date(data['date'])}, ⏰ {hhmm}",
        reply_markup=main_menu(),
    )
    await call.answer("Перенесено")

    await bot.send_message(
        config.admin_id,
        "🔁 <b>Клиент перенёс запись</b>\n\n" + booking_summary(booking),
    )
