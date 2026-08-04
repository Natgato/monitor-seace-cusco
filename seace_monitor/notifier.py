from __future__ import annotations

from html import escape
from email.message import EmailMessage
import re
import smtplib
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


def send_messages(config: Config, messages: list[str], subject: str = "Monitor SEACE Cusco — nuevas oportunidades") -> None:
    if config.notification_channel == "gmail":
        _send_gmail(config, messages, subject)
        return
    if config.notification_channel not in {"telegram", "none"}:
        raise NotificationError(f"Canal de notificación desconocido: {config.notification_channel}")
    if config.notification_channel == "none":
        return
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


def build_email(config: Config, messages: list[str], subject: str = "Monitor SEACE Cusco — nuevas oportunidades") -> EmailMessage:
    if not config.gmail_address or not config.gmail_app_password or not config.alert_email_to:
        raise NotificationError("Faltan GMAIL_ADDRESS, GMAIL_APP_PASSWORD o ALERT_EMAIL_TO")
    html_body = "<hr>".join(messages)
    plain_body = re.sub(r"<[^>]+>", "", html_body).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.gmail_address
    message["To"] = config.alert_email_to
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")
    return message


def _send_gmail(config: Config, messages: list[str], subject: str) -> None:
    message = build_email(config, messages, subject)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(config.gmail_address, config.gmail_app_password.replace(" ", ""))
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise NotificationError(f"No se pudo enviar el correo: {exc}") from exc
