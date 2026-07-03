from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import repo
from keyboards.client import main_menu

router = Router()

GREETING = (
    "💈 <b>Барбершоп «Маник»</b>\n\n"
    "Привет, {name}! Я помогу записаться к мастеру.\n"
    "Выберите действие в меню ниже."
)

INFO = (
    "💈 <b>Барбершоп «Маник»</b>\n\n"
    "📍 Адрес: ул. Примерная, 1\n"
    "🕙 Часы работы: Пн–Сб 10:00–20:00, Вс 11:00–18:00\n"
    "📞 Телефон: +7 (900) 000-00-00"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await repo.upsert_user(message.from_user.id, name=message.from_user.full_name)
    await message.answer(
        GREETING.format(name=message.from_user.first_name),
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu:home")
async def back_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        GREETING.format(name=call.from_user.first_name),
        reply_markup=main_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "menu:info")
async def show_info(call: CallbackQuery) -> None:
    await call.message.edit_text(INFO, reply_markup=main_menu())
    await call.answer()
