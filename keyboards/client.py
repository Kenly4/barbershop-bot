from datetime import date as date_cls

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "", "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться", callback_data="menu:book")
    kb.button(text="📋 Мои записи", callback_data="menu:my")
    kb.button(text="ℹ️ Инфо", callback_data="menu:info")
    kb.adjust(1)
    return kb.as_markup()


def services_kb(services: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in services:
        kb.button(
            text=f"{s['name']} — {s['price']}₽ · {s['duration_min']} мин",
            callback_data=f"svc:{s['id']}",
        )
    kb.button(text="⬅️ В меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def dates_kb(dates: list[date_cls], prefix: str = "date") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in dates:
        label = f"{WEEKDAYS_RU[d.weekday()]} {d.day} {MONTHS_RU[d.month]}"
        kb.button(text=label, callback_data=f"{prefix}:{d.isoformat()}")
    kb.button(text="⬅️ Назад", callback_data="book:back_service")
    kb.adjust(3)
    return kb.as_markup()


def times_kb(times: list[str], prefix: str = "time") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in times:
        kb.button(text=t, callback_data=f"{prefix}:{t}")
    kb.button(text="⬅️ Назад", callback_data="book:back_date")
    kb.adjust(4)
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="book:confirm")
    kb.button(text="❌ Отмена", callback_data="menu:home")
    kb.adjust(2)
    return kb.as_markup()


def request_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def my_bookings_kb(bookings: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(
            text=f"🔁 Перенести #{b['id']}", callback_data=f"resch:{b['id']}"
        )
        kb.button(
            text=f"❌ Отменить #{b['id']}", callback_data=f"cancel:{b['id']}"
        )
    kb.button(text="⬅️ В меню", callback_data="menu:home")
    kb.adjust(2)
    return kb.as_markup()
