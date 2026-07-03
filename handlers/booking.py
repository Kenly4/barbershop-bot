from datetime import date as date_cls

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import config
from database import repo
from keyboards.admin import new_booking_kb
from keyboards.client import (
    confirm_kb,
    dates_kb,
    main_menu,
    request_phone_kb,
    services_kb,
    times_kb,
)
from services import slots
from states.booking import BookingSG
from utils.texts import booking_summary, fmt_date
from utils.validators import normalize_phone, valid_name

router = Router()


@router.callback_query(F.data == "menu:book")
async def start_booking(call: CallbackQuery, state: FSMContext) -> None:
    active = await repo.count_active_bookings(call.from_user.id)
    if active >= config.max_active_bookings:
        await call.answer(
            f"У вас уже {active} активных записей — это максимум. "
            "Сначала завершите или отмените их.",
            show_alert=True,
        )
        return
    await state.clear()
    services = await repo.get_services()
    await call.message.edit_text("Выберите услугу:", reply_markup=services_kb(services))
    await state.set_state(BookingSG.service)
    await call.answer()


@router.callback_query(BookingSG.service, F.data.startswith("svc:"))
async def choose_service(call: CallbackQuery, state: FSMContext) -> None:
    service_id = int(call.data.split(":")[1])
    service = await repo.get_service(service_id)
    if not service:
        await call.answer("Услуга недоступна.", show_alert=True)
        return
    await state.update_data(
        service_id=service_id,
        duration=service["duration_min"],
        service_name=service["name"],
        price=service["price"],
    )
    dates = await slots.available_dates()
    await call.message.edit_text(
        f"Услуга: <b>{service['name']}</b>\nВыберите дату:",
        reply_markup=dates_kb(dates),
    )
    await state.set_state(BookingSG.date)
    await call.answer()


@router.callback_query(BookingSG.date, F.data == "book:back_service")
async def back_to_service(call: CallbackQuery, state: FSMContext) -> None:
    services = await repo.get_services()
    await call.message.edit_text("Выберите услугу:", reply_markup=services_kb(services))
    await state.set_state(BookingSG.service)
    await call.answer()


@router.callback_query(BookingSG.date, F.data.startswith("date:"))
async def choose_date(call: CallbackQuery, state: FSMContext) -> None:
    iso = call.data.split(":", 1)[1]
    data = await state.get_data()
    free = await slots.free_slots(date_cls.fromisoformat(iso), data["duration"])
    if not free:
        await call.answer("На эту дату свободных слотов нет.", show_alert=True)
        return
    await state.update_data(date=iso)
    await call.message.edit_text(
        f"Дата: <b>{fmt_date(iso)}</b>\nВыберите время:",
        reply_markup=times_kb(free),
    )
    await state.set_state(BookingSG.time)
    await call.answer()


@router.callback_query(BookingSG.time, F.data == "book:back_date")
async def back_to_date(call: CallbackQuery, state: FSMContext) -> None:
    dates = await slots.available_dates()
    await call.message.edit_text("Выберите дату:", reply_markup=dates_kb(dates))
    await state.set_state(BookingSG.date)
    await call.answer()


@router.callback_query(BookingSG.time, F.data.startswith("time:"))
async def choose_time(call: CallbackQuery, state: FSMContext) -> None:
    hhmm = call.data.split(":", 1)[1]
    await state.update_data(time=hhmm)

    # Пробуем взять сохранённые данные пользователя
    user = await repo.get_user(call.from_user.id)
    if user and user.get("name") and user.get("phone"):
        await state.update_data(name=user["name"], phone=user["phone"])
        await _show_confirm(call.message, state, edit=True)
        await call.answer()
        return

    await call.message.edit_text("Как вас зовут? Напишите имя одним сообщением.")
    await state.set_state(BookingSG.name)
    await call.answer()


@router.message(BookingSG.name)
async def enter_name(message: Message, state: FSMContext) -> None:
    if not valid_name(message.text or ""):
        await message.answer("Имя выглядит некорректно. Введите ещё раз (только буквы).")
        return
    await state.update_data(name=message.text.strip())
    await message.answer(
        "Отправьте номер телефона кнопкой ниже или введите вручную:",
        reply_markup=request_phone_kb(),
    )
    await state.set_state(BookingSG.phone)


@router.message(BookingSG.phone, F.contact)
async def enter_phone_contact(message: Message, state: FSMContext) -> None:
    await _save_phone(message, state, message.contact.phone_number)


@router.message(BookingSG.phone, F.text)
async def enter_phone_text(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text)
    if not phone:
        await message.answer("Не похоже на номер телефона. Попробуйте ещё раз.")
        return
    await _save_phone(message, state, phone)


async def _save_phone(message: Message, state: FSMContext, raw_phone: str) -> None:
    phone = normalize_phone(raw_phone) or raw_phone
    await state.update_data(phone=phone)
    await message.answer("Проверьте данные:", reply_markup=ReplyKeyboardRemove())
    await _show_confirm(message, state, edit=False)


async def _show_confirm(message: Message, state: FSMContext, edit: bool) -> None:
    data = await state.get_data()
    text = (
        "<b>Подтверждение записи</b>\n\n"
        f"✂️ {data['service_name']} — {data['price']}₽\n"
        f"📅 {fmt_date(data['date'])}, ⏰ {data['time']}\n"
        f"👤 {data['name']}\n"
        f"📞 {data['phone']}"
    )
    if edit:
        await message.edit_text(text, reply_markup=confirm_kb())
    else:
        await message.answer(text, reply_markup=confirm_kb())
    await state.set_state(BookingSG.confirm)


@router.callback_query(BookingSG.confirm, F.data == "book:confirm")
async def confirm_booking(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()

    # Повторная проверка занятости слота перед вставкой
    free = await slots.free_slots(date_cls.fromisoformat(data["date"]), data["duration"])
    if data["time"] not in free:
        await call.message.edit_text(
            "К сожалению, это время уже заняли. Попробуйте выбрать другой слот.",
            reply_markup=main_menu(),
        )
        await state.clear()
        await call.answer()
        return

    await repo.upsert_user(call.from_user.id, name=data["name"], phone=data["phone"])
    booking_id = await repo.create_booking(
        call.from_user.id,
        data["name"],
        data["phone"],
        data["service_id"],
        data["date"],
        data["time"],
    )
    if booking_id is None:
        await call.message.edit_text(
            "К сожалению, это время только что заняли. Выберите другой слот.",
            reply_markup=main_menu(),
        )
        await state.clear()
        await call.answer()
        return

    await call.message.edit_text(
        f"✅ Вы записаны! Номер записи #{booking_id}.\n"
        f"📅 {fmt_date(data['date'])}, ⏰ {data['time']}\n\n"
        "Мы напомним о визите заранее. До встречи!",
        reply_markup=main_menu(),
    )
    await state.clear()
    await call.answer("Запись создана")

    # Уведомляем администратора
    booking = await repo.get_booking(booking_id)
    tg = call.from_user
    username = f" (@{tg.username})" if tg.username else ""
    await bot.send_message(
        config.admin_id,
        f"🔔 <b>Новая запись</b>{username}\n\n" + booking_summary(booking),
        reply_markup=new_booking_kb(booking_id),
    )
