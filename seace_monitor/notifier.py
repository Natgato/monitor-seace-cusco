from __future__ import annotations

from html import escape
from typing import Any

import requests

from .config import Config
from .timeutils import human_date


class NotificationError(RuntimeError): pass


def _value(row: dict[str, Any], name: str, label: str) -> str:
    return escape(str(row.get(name) or f"{label} no informado"))


def _contract_html(row: dict[str, Any]) -> str:
    lines = [f"<b>{_value(row, 'codigo_contratacion', 'Código')}</b>", f"Entidad: {_value(row, 'entidad', 'Entidad')}",
        f"Descripción: {_value(row, 'descripcion', 'Descripción')}", f"Vencimiento: {escape(human_date(row.get('fecha_vencimiento')))}"]
    if row.get("tiempo_restante_texto"): lines.append(f"Tiempo restante: {escape(str(row['tiempo_restante_texto']))}")
    lines.extend([f"Ítems: {row.get('cantidad_items', 0)}", f"<a href=\"{escape(str(row['enlace_publico']), quote=True)}\">Ver contratación en SEACE</a>"])
    return "\n".join(lines)


def build_messages(rows: list[dict[str, Any]], consulted_at: str, limit: int = 4000) -> list[str]:
    header = f"<b>Nuevas contrataciones SEACE en Cusco: {len(rows)}</b>\nConsulta: {escape(consulted_at)}"
    chunks, current = [], header
    for row in rows:
        block = "\n\n" + _contract_html(row)
        if len(header) + len(block) > limit: raise NotificationError("Un contrato individual supera el límite de Telegram")
        if len(current) + len(block) > limit:
            chunks.append(current); current = header + block
        else: current += block
    chunks.append(current)
    if len(chunks) > 1:
        chunks = [f"<b>Parte {index} de {len(chunks)}</b>\n{message}" for index, message in enumerate(chunks, 1)]
    return chunks


def send_messages(config: Config, messages: list[str]) -> None:
    if not config.telegram_token or not config.telegram_chat_id:
        raise NotificationError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
    endpoint = f"https://api.telegram.org/bot{config.telegram_token}/sendMessage"
    for message in messages:
        try:
            response = requests.post(endpoint, json={"chat_id": config.telegram_chat_id, "text": message,
                "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=(15, 30))
            response.raise_for_status()
            if not response.json().get("ok"): raise NotificationError("Telegram rechazó el mensaje")
        except (requests.RequestException, ValueError) as exc:
            raise NotificationError(f"No se pudo enviar Telegram: {exc}") from exc
