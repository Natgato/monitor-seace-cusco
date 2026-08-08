from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import getaddresses
from html import escape
import re
import smtplib
from typing import Any

import requests

from .config import Config
from .timeutils import human_date


class NotificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: bytes
    maintype: str = "application"
    subtype: str = "octet-stream"


def email_recipients(value: str | None) -> list[str]:
    parsed = getaddresses([str(value or "").replace(";", ",")])
    recipients: list[str] = []
    seen: set[str] = set()
    for _, address in parsed:
        address = address.strip()
        normalized = address.lower()
        if "@" not in address or address.startswith("@") or address.endswith("@"):
            continue
        if normalized not in seen:
            seen.add(normalized)
            recipients.append(address)
    return recipients


def _value(row: dict[str, Any], name: str, label: str) -> str:
    return escape(str(row.get(name) or f"{label} no informado"))


def _contract_html(row: dict[str, Any]) -> str:
    lines = [
        f"<b>{_value(row, 'codigo_contratacion', 'Código')}</b>",
        f"Entidad: {_value(row, 'entidad', 'Entidad')}",
        f"Descripción: {_value(row, 'descripcion', 'Descripción')}",
        f"Vencimiento: {escape(human_date(row.get('fecha_vencimiento')))}",
    ]
    if row.get("tiempo_restante_texto"):
        lines.append(f"Tiempo restante: {escape(str(row['tiempo_restante_texto']))}")
    lines.extend(
        [
            f"Ítems: {row.get('cantidad_items', 0)}",
            f'<a href="{escape(str(row["enlace_publico"]), quote=True)}">Ver contratación en SEACE</a>',
        ]
    )
    return "\n".join(lines)


def build_messages(rows: list[dict[str, Any]], consulted_at: str, limit: int = 4000) -> list[str]:
    header = f"<b>Nuevas contrataciones SEACE en Cusco y Apurímac: {len(rows)}</b>\nConsulta: {escape(consulted_at)}"
    chunks, current = [], header
    for row in rows:
        block = "\n\n" + _contract_html(row)
        if len(header) + len(block) > limit:
            raise NotificationError("Un contrato individual supera el límite de Telegram")
        if len(current) + len(block) > limit:
            chunks.append(current)
            current = header + block
        else:
            current += block
    chunks.append(current)
    if len(chunks) > 1:
        chunks = [f"<b>Parte {index} de {len(chunks)}</b>\n{message}" for index, message in enumerate(chunks, 1)]
    return chunks


def send_messages(
    config: Config,
    messages: list[str],
    subject: str = "Radar Andino - nuevas oportunidades",
    attachments: list[EmailAttachment] | None = None,
) -> None:
    if config.notification_channel == "gmail":
        _send_gmail(config, messages, subject, attachments or [])
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
            response = requests.post(
                endpoint,
                json={
                    "chat_id": config.telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=(15, 30),
            )
            response.raise_for_status()
            if not response.json().get("ok"):
                raise NotificationError("Telegram rechazó el mensaje")
        except (requests.RequestException, ValueError) as exc:
            raise NotificationError(f"No se pudo enviar Telegram: {exc}") from exc


def build_email(
    config: Config,
    messages: list[str],
    subject: str = "Radar Andino - nuevas oportunidades",
    attachments: list[EmailAttachment] | None = None,
    recipient: str | None = None,
) -> EmailMessage:
    if not config.gmail_address or not config.gmail_app_password or not config.alert_email_to:
        raise NotificationError("Faltan GMAIL_ADDRESS, GMAIL_APP_PASSWORD o ALERT_EMAIL_TO")
    recipients = email_recipients(config.alert_email_to)
    selected_recipient = recipient or (recipients[0] if recipients else None)
    if not selected_recipient:
        raise NotificationError("ALERT_EMAIL_TO no contiene una dirección válida")
    html_body = "<hr>".join(messages)
    plain_body = re.sub(r"<[^>]+>", "", html_body).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.gmail_address
    message["To"] = selected_recipient
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")
    for attachment in attachments or []:
        message.add_attachment(
            attachment.content,
            maintype=attachment.maintype,
            subtype=attachment.subtype,
            filename=attachment.filename,
        )
    return message


def _send_gmail(
    config: Config,
    messages: list[str],
    subject: str,
    attachments: list[EmailAttachment],
) -> None:
    recipients = email_recipients(config.alert_email_to)
    if not recipients:
        raise NotificationError("ALERT_EMAIL_TO no contiene una dirección válida")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(config.gmail_address, config.gmail_app_password.replace(" ", ""))
            # Un mensaje individual por destinatario mantiene privadas las direcciones.
            for recipient in recipients:
                smtp.send_message(build_email(config, messages, subject, attachments, recipient))
    except (OSError, smtplib.SMTPException) as exc:
        raise NotificationError(f"No se pudo enviar el correo: {exc}") from exc
