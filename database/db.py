import aiosqlite

from config import config, DEFAULT_SERVICES, DEFAULT_SLOT_STEP

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id       INTEGER PRIMARY KEY,
    name        TEXT,
    phone       TEXT,
    is_blocked  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS services (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    price        INTEGER NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL,
    service_id  INTEGER NOT NULL,
    date        TEXT NOT NULL,          -- YYYY-MM-DD
    time        TEXT NOT NULL,          -- HH:MM
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending/confirmed/cancelled/done
    reminded    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (user_tg_id) REFERENCES users(tg_id)
);

-- Не допускаем двух активных записей на один слот (двойное бронирование).
CREATE UNIQUE INDEX IF NOT EXISTS idx_slot_unique
    ON bookings(date, time)
    WHERE status IN ('pending', 'confirmed');

-- График работы по дням недели (0=Пн ... 6=Вс)
CREATE TABLE IF NOT EXISTS work_schedule (
    weekday INTEGER PRIMARY KEY,
    is_open INTEGER NOT NULL DEFAULT 1,
    open_t  TEXT NOT NULL,   -- 'HH:MM'
    close_t TEXT NOT NULL
);

-- Прочие настройки (ключ-значение)
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(config.db_path) as db:
        await db.executescript(SCHEMA)
        # Засеиваем услуги, если таблица пустая
        cur = await db.execute("SELECT COUNT(*) FROM services")
        (count,) = await cur.fetchone()
        if count == 0:
            await db.executemany(
                "INSERT INTO services (name, duration_min, price) VALUES (?, ?, ?)",
                DEFAULT_SERVICES,
            )

        # Засеиваем график работы из config, если таблица пустая
        cur = await db.execute("SELECT COUNT(*) FROM work_schedule")
        (sched_count,) = await cur.fetchone()
        if sched_count == 0:
            rows = []
            for wd in range(7):
                hours = config.work_hours.get(wd)
                if hours is None:
                    rows.append((wd, 0, "10:00", "20:00"))
                else:
                    open_t, close_t = hours
                    rows.append(
                        (wd, 1, open_t.strftime("%H:%M"), close_t.strftime("%H:%M"))
                    )
            await db.executemany(
                "INSERT INTO work_schedule (weekday, is_open, open_t, close_t) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )

        # Значения по умолчанию для настроек
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('slot_step', ?)",
            (str(DEFAULT_SLOT_STEP),),
        )
        await db.commit()
