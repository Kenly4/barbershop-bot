from typing import Any, Optional

import aiosqlite

from config import config

ACTIVE_STATUSES = ("pending", "confirmed")


def _dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


async def _conn() -> aiosqlite.Connection:
    db = await aiosqlite.connect(config.db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


# ---------- Пользователи ----------
async def upsert_user(tg_id: int, name: str | None = None, phone: str | None = None) -> None:
    db = await _conn()
    try:
        await db.execute(
            """
            INSERT INTO users (tg_id, name, phone) VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                name = COALESCE(excluded.name, users.name),
                phone = COALESCE(excluded.phone, users.phone)
            """,
            (tg_id, name, phone),
        )
        await db.commit()
    finally:
        await db.close()


async def get_user(tg_id: int) -> Optional[dict]:
    db = await _conn()
    try:
        cur = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        return _dict(row) if row else None
    finally:
        await db.close()


async def is_blocked(tg_id: int) -> bool:
    user = await get_user(tg_id)
    return bool(user and user["is_blocked"])


async def set_blocked(tg_id: int, blocked: bool) -> None:
    db = await _conn()
    try:
        await db.execute(
            "INSERT INTO users (tg_id, is_blocked) VALUES (?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET is_blocked = excluded.is_blocked",
            (tg_id, int(blocked)),
        )
        await db.commit()
    finally:
        await db.close()


# ---------- Услуги ----------
async def get_services() -> list[dict]:
    db = await _conn()
    try:
        cur = await db.execute(
            "SELECT * FROM services WHERE is_active = 1 ORDER BY id"
        )
        return [_dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def get_service(service_id: int) -> Optional[dict]:
    db = await _conn()
    try:
        cur = await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        row = await cur.fetchone()
        return _dict(row) if row else None
    finally:
        await db.close()


# ---------- Записи ----------
async def get_booked_times(date: str) -> set[str]:
    """Занятые слоты (HH:MM) на конкретную дату."""
    db = await _conn()
    try:
        cur = await db.execute(
            f"SELECT time FROM bookings WHERE date = ? "
            f"AND status IN ({','.join('?' * len(ACTIVE_STATUSES))})",
            (date, *ACTIVE_STATUSES),
        )
        return {r["time"] for r in await cur.fetchall()}
    finally:
        await db.close()


async def get_booked_intervals(date: str) -> list[tuple[str, int]]:
    """Активные записи на дату: список (время 'HH:MM', длительность в минутах)."""
    db = await _conn()
    try:
        cur = await db.execute(
            f"""
            SELECT b.time AS time, s.duration_min AS duration
            FROM bookings b JOIN services s ON s.id = b.service_id
            WHERE b.date = ? AND b.status IN ({','.join('?' * len(ACTIVE_STATUSES))})
            """,
            (date, *ACTIVE_STATUSES),
        )
        return [(r["time"], r["duration"]) for r in await cur.fetchall()]
    finally:
        await db.close()


async def count_active_bookings(tg_id: int) -> int:
    db = await _conn()
    try:
        cur = await db.execute(
            f"SELECT COUNT(*) AS c FROM bookings WHERE user_tg_id = ? "
            f"AND status IN ({','.join('?' * len(ACTIVE_STATUSES))})",
            (tg_id, *ACTIVE_STATUSES),
        )
        row = await cur.fetchone()
        return row["c"]
    finally:
        await db.close()


async def create_booking(
    tg_id: int, name: str, phone: str, service_id: int, date: str, time: str
) -> Optional[int]:
    """Создаёт запись. Возвращает id или None, если слот уже занят."""
    db = await _conn()
    try:
        cur = await db.execute(
            "INSERT INTO bookings (user_tg_id, name, phone, service_id, date, time) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, name, phone, service_id, date, time),
        )
        await db.commit()
        return cur.lastrowid
    except aiosqlite.IntegrityError:
        # Сработал уникальный индекс на слот — кто-то успел раньше
        return None
    finally:
        await db.close()


async def get_booking(booking_id: int) -> Optional[dict]:
    db = await _conn()
    try:
        cur = await db.execute(
            """
            SELECT b.*, s.name AS service_name, s.duration_min, s.price
            FROM bookings b JOIN services s ON s.id = b.service_id
            WHERE b.id = ?
            """,
            (booking_id,),
        )
        row = await cur.fetchone()
        return _dict(row) if row else None
    finally:
        await db.close()


async def get_user_active_bookings(tg_id: int) -> list[dict]:
    db = await _conn()
    try:
        cur = await db.execute(
            f"""
            SELECT b.*, s.name AS service_name, s.price
            FROM bookings b JOIN services s ON s.id = b.service_id
            WHERE b.user_tg_id = ? AND b.status IN ({','.join('?' * len(ACTIVE_STATUSES))})
            ORDER BY b.date, b.time
            """,
            (tg_id, *ACTIVE_STATUSES),
        )
        return [_dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def set_status(booking_id: int, status: str) -> None:
    db = await _conn()
    try:
        await db.execute(
            "UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id)
        )
        await db.commit()
    finally:
        await db.close()


async def reschedule(booking_id: int, date: str, time: str) -> bool:
    """Переносит запись на новый слот. False, если слот занят."""
    db = await _conn()
    try:
        await db.execute(
            "UPDATE bookings SET date = ?, time = ?, reminded = 0 WHERE id = ?",
            (date, time, booking_id),
        )
        await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False
    finally:
        await db.close()


async def get_bookings_by_date(date: str) -> list[dict]:
    db = await _conn()
    try:
        cur = await db.execute(
            f"""
            SELECT b.*, s.name AS service_name, s.price
            FROM bookings b JOIN services s ON s.id = b.service_id
            WHERE b.date = ? AND b.status IN ({','.join('?' * len(ACTIVE_STATUSES))})
            ORDER BY b.time
            """,
            (date, *ACTIVE_STATUSES),
        )
        return [_dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def get_upcoming_bookings() -> list[dict]:
    db = await _conn()
    try:
        cur = await db.execute(
            f"""
            SELECT b.*, s.name AS service_name, s.price
            FROM bookings b JOIN services s ON s.id = b.service_id
            WHERE date(b.date) >= date('now', 'localtime')
              AND b.status IN ({','.join('?' * len(ACTIVE_STATUSES))})
            ORDER BY b.date, b.time
            """,
            ACTIVE_STATUSES,
        )
        return [_dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def get_bookings_for_reminder() -> list[dict]:
    """Записи, которым ещё не отправляли напоминание."""
    db = await _conn()
    try:
        cur = await db.execute(
            """
            SELECT b.*, s.name AS service_name
            FROM bookings b JOIN services s ON s.id = b.service_id
            WHERE b.status IN ('pending', 'confirmed') AND b.reminded = 0
            """
        )
        return [_dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def mark_reminded(booking_id: int) -> None:
    db = await _conn()
    try:
        await db.execute(
            "UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,)
        )
        await db.commit()
    finally:
        await db.close()


# ---------- График работы ----------
async def get_schedule() -> dict[int, dict]:
    """Возвращает {weekday: {is_open, open_t, close_t}}."""
    db = await _conn()
    try:
        cur = await db.execute("SELECT * FROM work_schedule ORDER BY weekday")
        result = {}
        for r in await cur.fetchall():
            result[r["weekday"]] = {
                "is_open": bool(r["is_open"]),
                "open_t": r["open_t"],
                "close_t": r["close_t"],
            }
        return result
    finally:
        await db.close()


async def toggle_day(weekday: int) -> None:
    db = await _conn()
    try:
        await db.execute(
            "UPDATE work_schedule SET is_open = 1 - is_open WHERE weekday = ?",
            (weekday,),
        )
        await db.commit()
    finally:
        await db.close()


async def set_day_hours(weekday: int, open_t: str, close_t: str) -> None:
    db = await _conn()
    try:
        await db.execute(
            "UPDATE work_schedule SET open_t = ?, close_t = ?, is_open = 1 "
            "WHERE weekday = ?",
            (open_t, close_t, weekday),
        )
        await db.commit()
    finally:
        await db.close()


# ---------- Настройки ----------
async def get_setting(key: str, default: str = "") -> str:
    db = await _conn()
    try:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else default
    finally:
        await db.close()


async def set_setting(key: str, value: str) -> None:
    db = await _conn()
    try:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()
    finally:
        await db.close()


# ---------- Управление услугами ----------
async def add_service(name: str, duration_min: int, price: int) -> None:
    db = await _conn()
    try:
        await db.execute(
            "INSERT INTO services (name, duration_min, price) VALUES (?, ?, ?)",
            (name, duration_min, price),
        )
        await db.commit()
    finally:
        await db.close()


async def update_service(service_id: int, **fields) -> None:
    allowed = {"name", "duration_min", "price"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    db = await _conn()
    try:
        await db.execute(
            f"UPDATE services SET {set_clause} WHERE id = ?",
            (*updates.values(), service_id),
        )
        await db.commit()
    finally:
        await db.close()


async def deactivate_service(service_id: int) -> None:
    db = await _conn()
    try:
        await db.execute(
            "UPDATE services SET is_active = 0 WHERE id = ?", (service_id,)
        )
        await db.commit()
    finally:
        await db.close()
