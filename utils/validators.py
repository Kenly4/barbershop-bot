import re

_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{9,14}\d$")


def normalize_phone(raw: str) -> str | None:
    """Проверяет и нормализует телефон. Возвращает +7XXXXXXXXXX или None."""
    raw = raw.strip()
    if not _PHONE_RE.match(raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    elif not (10 <= len(digits) <= 15):
        return None
    return "+" + digits


def valid_name(raw: str) -> bool:
    raw = raw.strip()
    return 2 <= len(raw) <= 40 and bool(re.match(r"^[A-Za-zА-Яа-яЁё\s\-]+$", raw))
