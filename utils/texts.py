from datetime import date as date_cls

from keyboards.client import MONTHS_RU, WEEKDAYS_RU


def fmt_date(iso: str) -> str:
    d = date_cls.fromisoformat(iso)
    return f"{WEEKDAYS_RU[d.weekday()]} {d.day} {MONTHS_RU[d.month]}"


STATUS_RU = {
    "pending": "🕓 ожидает подтверждения",
    "confirmed": "✅ подтверждена",
    "cancelled": "❌ отменена",
    "done": "☑️ выполнена",
}


def booking_summary(b: dict, with_id: bool = True) -> str:
    head = f"Запись #{b['id']}\n" if with_id else ""
    price = b.get("price")
    price_line = f"\n💰 {price}₽" if price is not None else ""
    return (
        f"{head}"
        f"✂️ {b['service_name']}{price_line}\n"
        f"📅 {fmt_date(b['date'])}, ⏰ {b['time']}\n"
        f"👤 {b['name']}, 📞 {b['phone']}\n"
        f"Статус: {STATUS_RU.get(b['status'], b['status'])}"
    )
