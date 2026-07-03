from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def new_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Кнопки под уведомлением админа о новой записи."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"adm:confirm:{booking_id}")
    kb.button(text="❌ Отклонить", callback_data=f"adm:reject:{booking_id}")
    kb.button(text="🚫 Заблокировать клиента", callback_data=f"adm:block:{booking_id}")
    kb.adjust(2, 1)
    return kb.as_markup()
