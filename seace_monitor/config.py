from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _integer(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _decimal(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    year: int = _integer("SEACE_YEAR", 2026)
    max_pages: int = _integer("SEACE_MAX_PAGES", 50)
    page_size: int = _integer("SEACE_PAGE_SIZE", 50)
    page_delay_seconds: float = _decimal("SEACE_PAGE_DELAY_SECONDS", 0.7)
    connect_timeout: int = _integer("SEACE_CONNECT_TIMEOUT", 15)
    read_timeout: int = _integer("SEACE_READ_TIMEOUT", 30)
    watchdog_threshold_hours: int = _integer("WATCHDOG_THRESHOLD_HOURS", 3)
    notification_channel: str = os.getenv("NOTIFICATION_CHANNEL", "none").strip().lower()
    telegram_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    gmail_address: str | None = os.getenv("GMAIL_ADDRESS")
    gmail_app_password: str | None = os.getenv("GMAIL_APP_PASSWORD")
    alert_email_to: str | None = os.getenv("ALERT_EMAIL_TO")
    state_path: Path = ROOT / "data" / "estado.json"
    contracts_path: Path = ROOT / "data" / "contrataciones.csv"
    items_path: Path = ROOT / "data" / "items.csv"

    @property
    def notifications_enabled(self) -> bool:
        return self.notification_channel != "none"
