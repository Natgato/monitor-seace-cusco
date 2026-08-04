from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from .timeutils import LIMA

MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _text(value: Any, fallback: str = "No informado") -> str:
    return escape(str(value or fallback))


def _date_label(moment: datetime) -> str:
    local = moment.astimezone(LIMA)
    return f"{local.day} de {MONTHS[local.month - 1]} de {local.year}"


def _deadline_label(value: Any) -> str:
    try:
        local = datetime.fromisoformat(str(value)).astimezone(LIMA)
    except (TypeError, ValueError):
        return "Fecha no informada"
    suffix = "a. m." if local.hour < 12 else "p. m."
    hour = local.hour % 12 or 12
    return f"{local.day} {MONTHS[local.month - 1][:3]} {local.year}, {hour}:{local.minute:02d} {suffix}"


def _layout(title: str, eyebrow: str, intro: str, body: str, generated_at: datetime) -> str:
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>
body{{margin:0;background:#f3efe7;color:#14223a;font-family:Arial,Helvetica,sans-serif}} .wrap{{width:100%;padding:28px 10px}}
.card{{max-width:640px;margin:auto;background:#fff;border:1px solid #ded8cd;border-radius:14px;overflow:hidden}}
.header{{background:#102640;padding:28px 32px;color:#fff}} .brand{{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#c7a968;font-weight:bold}}
h1{{font-size:25px;line-height:1.2;margin:10px 0 8px}} .intro{{color:#dbe4ec;font-size:14px;line-height:1.55;margin:0}}
.content{{padding:26px 32px}} .section-title{{font-size:14px;letter-spacing:.7px;text-transform:uppercase;color:#80672e;margin:26px 0 12px}}
.stats{{width:100%;border-collapse:separate;border-spacing:6px}} .stat{{background:#f6f3ed;border:1px solid #e4ded2;border-radius:9px;padding:13px 8px;text-align:center}}
.stat strong{{display:block;font-size:22px;color:#102640}} .stat span{{font-size:10px;text-transform:uppercase;color:#667085}}
.opportunity{{border:1px solid #ded8cd;border-left:4px solid #c39a43;border-radius:8px;padding:15px;margin:0 0 12px}}
.tag{{display:inline-block;background:#e9f0f5;color:#244968;border-radius:12px;padding:4px 8px;font-size:10px;font-weight:bold;text-transform:uppercase}}
.code{{font-size:12px;color:#80672e;font-weight:bold;margin-left:6px}} .entity{{font-size:15px;font-weight:bold;margin:9px 0 5px}}
.description{{font-size:13px;color:#475467;line-height:1.45;margin:0 0 8px}} .meta{{font-size:12px;color:#667085;line-height:1.55}}
.button{{display:inline-block;background:#102640;color:#fff!important;text-decoration:none;border-radius:6px;padding:9px 13px;font-size:12px;font-weight:bold;margin-top:9px}}
.empty{{background:#f6f3ed;border-radius:8px;padding:16px;color:#667085;font-size:13px}} .note{{font-size:12px;color:#667085;line-height:1.5}}
.footer{{background:#f6f3ed;border-top:1px solid #e4ded2;padding:19px 32px;color:#667085;font-size:11px;line-height:1.5}}
@media(max-width:560px){{.header,.content,.footer{{padding-left:20px;padding-right:20px}} h1{{font-size:21px}}}}
</style></head><body><div class="wrap"><div class="card">
<div class="header"><div class="brand">{escape(eyebrow)}</div><h1>{escape(title)}</h1><p class="intro">{escape(intro)}</p></div>
<div class="content">{body}</div>
<div class="footer">Monitor SEACE — Cusco y Apurímac<br>Generado el {_date_label(generated_at)} a las {generated_at.astimezone(LIMA).strftime('%I:%M %p')}. Datos obtenidos del buscador público de SEACE.</div>
</div></div></body></html>"""


def _opportunity(row: dict[str, Any], item_count: int | None = None) -> str:
    url = escape(str(row.get("enlace_publico") or "https://prod6.seace.gob.pe/buscador-publico/"), quote=True)
    region = _text(row.get("departamento"), "Región")
    code = _text(row.get("codigo_contratacion"), "Sin código")
    count = item_count if item_count is not None else int(row.get("cantidad_items") or 0)
    deadline = _deadline_label(row.get("fecha_vencimiento"))
    remaining = row.get("tiempo_restante_texto")
    timing = f" · {_text(remaining)}" if remaining else ""
    return f"""<div class="opportunity">
<span class="tag">{region}</span><span class="code">{code}</span>
<div class="entity">{_text(row.get('entidad'), 'Entidad no informada')}</div>
<p class="description">{_text(row.get('descripcion'), 'Descripción no informada')}</p>
<div class="meta">Vence: {escape(deadline)}{timing}<br>Ítems registrados: {count}</div>
<a class="button" href="{url}">Ver oportunidad en SEACE</a></div>"""


def build_new_contracts_email(rows: list[dict[str, Any]], generated_at: datetime) -> str:
    cards = "".join(_opportunity(row) for row in rows[:10])
    if len(rows) > 10:
        cards += f'<p class="note">Hay {len(rows) - 10} oportunidades adicionales. Se incluirán en el resumen diario.</p>'
    body = f'<div class="section-title">Nuevas publicaciones detectadas</div>{cards}'
    return _layout(
        f"{len(rows)} nueva{'s' if len(rows) != 1 else ''} oportunidad{'es' if len(rows) != 1 else ''}",
        "Alerta inmediata",
        "El monitor encontró nuevas contrataciones públicas en Cusco o Apurímac.",
        body,
        generated_at,
    )


def build_daily_email(
    rows: list[dict[str, Any]],
    items_by_contract: dict[str, int],
    generated_at: datetime,
) -> str:
    today = generated_at.astimezone(LIMA).date().isoformat()
    published_today = [row for row in rows if str(row.get("fecha_publicacion") or "")[:10] == today]
    upcoming = sorted(rows, key=lambda row: row.get("fecha_vencimiento") or "9999")[:6]
    entities = len({str(row.get("ruc_entidad") or row.get("entidad") or "") for row in rows})
    cusco = sum(1 for row in rows if str(row.get("departamento") or "").upper() == "CUSCO")
    apurimac = len(rows) - cusco
    stats = f"""<table class="stats" role="presentation"><tr>
<td class="stat"><strong>{len(rows)}</strong><span>Vigentes</span></td>
<td class="stat"><strong>{len(published_today)}</strong><span>Publicadas hoy</span></td>
<td class="stat"><strong>{cusco}</strong><span>Cusco</span></td>
<td class="stat"><strong>{apurimac}</strong><span>Apurímac</span></td>
</tr></table><p class="note">{entities} entidades públicas con oportunidades abiertas.</p>"""
    deadline_cards = "".join(
        _opportunity(row, items_by_contract.get(str(row.get("idContrato")), 0)) for row in upcoming
    ) or '<div class="empty">No hay oportunidades vigentes registradas.</div>'
    new_cards = "".join(
        _opportunity(row, items_by_contract.get(str(row.get("idContrato")), 0)) for row in published_today[:5]
    ) or '<div class="empty">Hoy todavía no se registraron nuevas publicaciones.</div>'
    body = (
        stats
        + '<div class="section-title">Próximos vencimientos</div>' + deadline_cards
        + '<div class="section-title">Publicadas hoy</div>' + new_cards
        + '<p class="note">Este resumen se genera desde los datos ya guardados por el monitor; realiza 0 solicitudes adicionales a SEACE.</p>'
    )
    return _layout(
        "Resumen diario de oportunidades",
        "Monitor regional SEACE",
        f"Panorama de contrataciones vigentes para Cusco y Apurímac — {_date_label(generated_at)}.",
        body,
        generated_at,
    )
