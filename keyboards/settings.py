from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

WEEKDAYS_FULL = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]

STEP_OPTIONS = [0, 15, 20, 30, 40, 45, 60]


def settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 График работы", callback_data="set:schedule")
    kb.button(text="⏱ Шаг записи", callback_data="set:step")
    kb.button(text="✂️ Услуги и цены", callback_data="set:services")
    kb.button(text="✖️ Закрыть", callback_data="set:close")
    kb.adjust(1)
    return kb.as_markup()


def schedule_menu(schedule: dict[int, dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for wd in range(7):
        day = schedule[wd]
        if day["is_open"]:
            label = f"🟢 {WEEKDAYS_FULL[wd]}: {day['open_t']}–{day['close_t']}"
        else:
            label = f"🔴 {WEEKDAYS_FULL[wd]}: выходной"
        kb.button(text=label, callback_data=f"set:day:{wd}")
    kb.button(text="⬅️ Назад", callback_data="set:home")
    kb.adjust(1)
    return kb.as_markup()


def day_menu(wd: int, day: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "🔴 Сделать выходным" if day["is_open"] else "🟢 Сделать рабочим"
    kb.button(text=toggle, callback_data=f"set:daytoggle:{wd}")
    kb.button(text="🕙 Изменить часы", callback_data=f"set:dayhours:{wd}")
    kb.button(text="⬅️ Назад", callback_data="set:schedule")
    kb.adjust(1)
    return kb.as_markup()


def step_menu(current: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for opt in STEP_OPTIONS:
        label = "По длительности услуги" if opt == 0 else f"{opt} мин"
        if opt == current:
            label = "✅ " + label
        kb.button(text=label, callback_data=f"set:setstep:{opt}")
    kb.button(text="⬅️ Назад", callback_data="set:home")
    kb.adjust(2)
    return kb.as_markup()


def services_menu(services: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in services:
        kb.button(
            text=f"{s['name']} · {s['price']}₽ · {s['duration_min']}мин",
            callback_data=f"set:svc:{s['id']}",
        )
    kb.button(text="➕ Добавить услугу", callback_data="set:svcadd")
    kb.button(text="⬅️ Назад", callback_data="set:home")
    kb.adjust(1)
    return kb.as_markup()


def service_menu(service_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Название", callback_data=f"set:svcname:{service_id}")
    kb.button(text="💰 Цену", callback_data=f"set:svcprice:{service_id}")
    kb.button(text="⏱ Длительность", callback_data=f"set:svcdur:{service_id}")
    kb.button(text="🗑 Удалить", callback_data=f"set:svcdel:{service_id}")
    kb.button(text="⬅️ Назад", callback_data="set:services")
    kb.adjust(2)
    return kb.as_markup()
