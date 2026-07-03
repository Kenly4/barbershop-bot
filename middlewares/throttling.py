import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import config
from database import repo


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничивает частоту действий пользователя и отсекает заблокированных."""

    def __init__(self) -> None:
        self._last_action: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        # Админа не троттлим и не блокируем
        if user.id == config.admin_id:
            return await handler(event, data)

        if await repo.is_blocked(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer("Доступ ограничен.", show_alert=True)
            return  # молча игнорируем сообщения

        now = time.monotonic()
        last = self._last_action.get(user.id, 0.0)
        if now - last < config.throttle_seconds:
            if isinstance(event, CallbackQuery):
                await event.answer("Слишком быстро, подождите секунду.")
            return  # флуд — игнорируем
        self._last_action[user.id] = now

        return await handler(event, data)
