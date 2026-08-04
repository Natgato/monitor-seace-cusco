from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

LIMA = ZoneInfo("America/Lima")
SEACE_FORMAT = "%d/%m/%Y %H:%M:%S"


def now() -> datetime:
    return datetime.now(LIMA)


def iso_now() -> str:
    return now().isoformat(timespec="seconds")


def parse_seace(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), SEACE_FORMAT).replace(tzinfo=LIMA)
    except ValueError:
        return None


def iso_seace(value: object) -> str | None:
    parsed = parse_seace(value)
    return parsed.isoformat(timespec="seconds") if parsed else None


def human_date(value: str | None) -> str:
    if not value:
        return "Fecha no informada"
    try:
        return datetime.fromisoformat(value).astimezone(LIMA).strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return "Fecha no informada"


def remaining_text(end: datetime | None, reference: datetime | None = None) -> str | None:
    if not end:
        return None
    seconds = int((end - (reference or now())).total_seconds())
    if seconds <= 0:
        return "Vencido"
    hours, _ = divmod(seconds, 3600)
    days, hours = divmod(hours, 24)
    return f"{days} d, {hours} h restantes" if days else f"{hours} h restantes"
