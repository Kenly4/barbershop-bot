import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database import repo
from keyboards.settings import (
    WEEKDAYS_FULL,
    day_menu,
    schedule_menu,
    service_menu,
    services_menu,
    settings_menu,
    step_menu,
)
from states.booking import SettingsSG

router = Router()
# Вся панель доступна только администратору
router.message.filter(F.from_user.id == config.admin_id)
router.callback_query.filter(F.from_user.id == config.admin_id)

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


def _norm_time(t: str) -> str | None:
    if not _TIME_RE.match(t):
        return None
    h, m = t.split(":")
    return f"{int(h):02d}:{m}"


# ---------- Вход ----------
@router.message(Command("settings"))
async def open_settings(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("⚙️ <b>Настройки</b>", reply_markup=settings_menu())


@router.callback_query(F.data == "set:home")
async def back_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("⚙️ <b>Настройки</b>", reply_markup=settings_menu())
    await call.answer()


@router.callback_query(F.data == "set:close")
async def close_settings(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("Настройки закрыты.")
    await call.answer()


# ---------- График ----------
@router.callback_query(F.data == "set:schedule")
async def show_schedule(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    schedule = await repo.get_schedule()
    await call.message.edit_text(
        "📅 <b>График работы</b>\nВыберите день для изменения:",
        reply_markup=schedule_menu(schedule),
    )
    await call.answer()


@router.callback_query(F.data.startswith("set:day:"))
async def show_day(call: CallbackQuery) -> None:
    wd = int(call.data.split(":")[2])
    schedule = await repo.get_schedule()
    day = schedule[wd]
    status = (
        f"{day['open_t']}–{day['close_t']}" if day["is_open"] else "выходной"
    )
    await call.message.edit_text(
        f"<b>{WEEKDAYS_FULL[wd]}</b>: {status}",
        reply_markup=day_menu(wd, day),
    )
    await call.answer()


@router.callback_query(F.data.startswith("set:daytoggle:"))
async def toggle_day(call: CallbackQuery) -> None:
    wd = int(call.data.split(":")[2])
    await repo.toggle_day(wd)
    schedule = await repo.get_schedule()
    day = schedule[wd]
    status = f"{day['open_t']}–{day['close_t']}" if day["is_open"] else "выходной"
    await call.message.edit_text(
        f"<b>{WEEKDAYS_FULL[wd]}</b>: {status}",
        reply_markup=day_menu(wd, day),
    )
    await call.answer("Обновлено")


@router.callback_query(F.data.startswith("set:dayhours:"))
async def ask_day_hours(call: CallbackQuery, state: FSMContext) -> None:
    wd = int(call.data.split(":")[2])
    await state.update_data(weekday=wd)
    await state.set_state(SettingsSG.day_hours)
    await call.message.edit_text(
        f"Введите часы работы на <b>{WEEKDAYS_FULL[wd]}</b> в формате:\n"
        "<code>10:00 20:00</code>"
    )
    await call.answer()


@router.message(SettingsSG.day_hours)
async def save_day_hours(message: Message, state: FSMContext) -> None:
    parts = re.split(r"[\s\-–]+", (message.text or "").strip())
    if len(parts) != 2:
        await message.answer("Формат: <code>10:00 20:00</code>. Попробуйте ещё раз.")
        return
    open_t, close_t = _norm_time(parts[0]), _norm_time(parts[1])
    if not open_t or not close_t:
        await message.answer("Неверное время. Формат: <code>10:00 20:00</code>.")
        return
    if open_t >= close_t:
        await message.answer("Открытие должно быть раньше закрытия.")
        return
    data = await state.get_data()
    wd = data["weekday"]
    await repo.set_day_hours(wd, open_t, close_t)
    await state.clear()
    schedule = await repo.get_schedule()
    await message.answer(
        f"✅ {WEEKDAYS_FULL[wd]}: {open_t}–{close_t}",
        reply_markup=schedule_menu(schedule),
    )


# ---------- Шаг записи ----------
@router.callback_query(F.data == "set:step")
async def show_step(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    current = int(await repo.get_setting("slot_step", "0"))
    await call.message.edit_text(
        "⏱ <b>Шаг записи</b>\n"
        "Как часто начинаются слоты. «По длительности услуги» — шаг равен времени услуги.",
        reply_markup=step_menu(current),
    )
    await call.answer()


@router.callback_query(F.data.startswith("set:setstep:"))
async def set_step(call: CallbackQuery) -> None:
    step = int(call.data.split(":")[2])
    await repo.set_setting("slot_step", str(step))
    await call.message.edit_text(
        "⏱ <b>Шаг записи</b> обновлён.",
        reply_markup=step_menu(step),
    )
    await call.answer("Сохранено")


# ---------- Услуги ----------
@router.callback_query(F.data == "set:services")
async def show_services(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    services = await repo.get_services()
    await call.message.edit_text(
        "✂️ <b>Услуги</b>\nВыберите услугу или добавьте новую:",
        reply_markup=services_menu(services),
    )
    await call.answer()


@router.callback_query(F.data.startswith("set:svc:"))
async def show_service(call: CallbackQuery) -> None:
    sid = int(call.data.split(":")[2])
    s = await repo.get_service(sid)
    if not s:
        await call.answer("Услуга не найдена.", show_alert=True)
        return
    await call.message.edit_text(
        f"<b>{s['name']}</b>\n💰 {s['price']}₽ · ⏱ {s['duration_min']} мин\n\n"
        "Что изменить?",
        reply_markup=service_menu(sid),
    )
    await call.answer()


@router.callback_query(F.data.startswith("set:svcdel:"))
async def delete_service(call: CallbackQuery) -> None:
    sid = int(call.data.split(":")[2])
    await repo.deactivate_service(sid)
    services = await repo.get_services()
    await call.message.edit_text(
        "🗑 Услуга удалена.", reply_markup=services_menu(services)
    )
    await call.answer("Удалено")


@router.callback_query(F.data == "set:svcadd")
async def ask_service_add(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsSG.svc_add)
    await call.message.edit_text(
        "Добавление услуги. Введите в формате:\n"
        "<code>Название; длительность(мин); цена</code>\n"
        "Например: <code>Укладка; 30; 800</code>"
    )
    await call.answer()


@router.message(SettingsSG.svc_add)
async def save_service_add(message: Message, state: FSMContext) -> None:
    parts = [p.strip() for p in (message.text or "").split(";")]
    if len(parts) != 3 or not parts[0]:
        await message.answer("Формат: <code>Название; длительность; цена</code>.")
        return
    name, dur_raw, price_raw = parts
    if not dur_raw.isdigit() or not price_raw.isdigit():
        await message.answer("Длительность и цена должны быть числами.")
        return
    dur, price = int(dur_raw), int(price_raw)
    if not (5 <= dur <= 480) or price < 0:
        await message.answer("Длительность 5–480 мин, цена не отрицательная.")
        return
    await repo.add_service(name, dur, price)
    await state.clear()
    services = await repo.get_services()
    await message.answer(
        f"✅ Услуга «{name}» добавлена.", reply_markup=services_menu(services)
    )


@router.callback_query(F.data.startswith("set:svcname:"))
async def ask_service_name(call: CallbackQuery, state: FSMContext) -> None:
    sid = int(call.data.split(":")[2])
    await state.update_data(service_id=sid)
    await state.set_state(SettingsSG.svc_name)
    await call.message.edit_text("Введите новое название услуги:")
    await call.answer()


@router.message(SettingsSG.svc_name)
async def save_service_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not (2 <= len(name) <= 60):
        await message.answer("Название 2–60 символов. Попробуйте ещё раз.")
        return
    data = await state.get_data()
    await repo.update_service(data["service_id"], name=name)
    await state.clear()
    services = await repo.get_services()
    await message.answer("✅ Название обновлено.", reply_markup=services_menu(services))


@router.callback_query(F.data.startswith("set:svcprice:"))
async def ask_service_price(call: CallbackQuery, state: FSMContext) -> None:
    sid = int(call.data.split(":")[2])
    await state.update_data(service_id=sid)
    await state.set_state(SettingsSG.svc_price)
    await call.message.edit_text("Введите новую цену (₽), числом:")
    await call.answer()


@router.message(SettingsSG.svc_price)
async def save_service_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Цена должна быть числом. Попробуйте ещё раз.")
        return
    data = await state.get_data()
    await repo.update_service(data["service_id"], price=int(raw))
    await state.clear()
    services = await repo.get_services()
    await message.answer("✅ Цена обновлена.", reply_markup=services_menu(services))


@router.callback_query(F.data.startswith("set:svcdur:"))
async def ask_service_dur(call: CallbackQuery, state: FSMContext) -> None:
    sid = int(call.data.split(":")[2])
    await state.update_data(service_id=sid)
    await state.set_state(SettingsSG.svc_duration)
    await call.message.edit_text("Введите новую длительность (мин), числом:")
    await call.answer()


@router.message(SettingsSG.svc_duration)
async def save_service_dur(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (5 <= int(raw) <= 480):
        await message.answer("Длительность 5–480 мин, числом. Попробуйте ещё раз.")
        return
    data = await state.get_data()
    await repo.update_service(data["service_id"], duration_min=int(raw))
    await state.clear()
    services = await repo.get_services()
    await message.answer("✅ Длительность обновлена.", reply_markup=services_menu(services))
