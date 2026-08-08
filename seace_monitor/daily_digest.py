from __future__ import annotations

import logging
import sys
import unicodedata
from datetime import datetime
from typing import Any

from .config import Config
from .email_templates import build_daily_email
from .notifier import EmailAttachment, send_messages
from .pdf_report import build_daily_pdf
from .storage import read_csv
from .timeutils import LIMA, now

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)


def _normalized(value: Any) -> str:
    plain = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in plain if not unicodedata.combining(char)).strip().upper()


def _parsed(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)).astimezone(LIMA) if value else None
    except ValueError:
        return None


def select_open_regional(rows: list[dict[str, Any]], reference: datetime) -> list[dict[str, Any]]:
    allowed = {"CUSCO", "APURIMAC"}
    selected = []
    for row in rows:
        deadline = _parsed(row.get("fecha_vencimiento"))
        if _normalized(row.get("departamento")) not in allowed:
            continue
        if _normalized(row.get("estado")) != "VIGENTE":
            continue
        if deadline is not None and deadline <= reference:
            continue
        selected.append(row)
    return selected


def run() -> None:
    config = Config()
    generated_at = now()
    rows = select_open_regional(read_csv(config.contracts_path), generated_at)
    item_counts: dict[str, int] = {}
    for item in read_csv(config.items_path):
        contract_id = str(item.get("idContrato") or "")
        item_counts[contract_id] = item_counts.get(contract_id, 0) + 1

    html = build_daily_email(rows, item_counts, generated_at)
    pdf = build_daily_pdf(rows, item_counts, generated_at, config.report_recipient_name)
    filename = f"Radar-Andino-Cusco-Apurimac-{generated_at.strftime('%Y-%m-%d')}.pdf"
    send_messages(
        config,
        [html],
        subject=f"Radar Andino - resumen diario - {generated_at.strftime('%d/%m/%Y')}",
        attachments=[EmailAttachment(filename=filename, content=pdf, subtype="pdf")],
    )
    LOG.info(
        "Resumen procesado con %s oportunidades vigentes; PDF=%s bytes; solicitudes SEACE=0",
        len(rows),
        len(pdf),
    )


if __name__ == "__main__":
    try:
        run()
    except Exception:
        LOG.exception("No se pudo enviar el resumen diario")
        sys.exit(1)
