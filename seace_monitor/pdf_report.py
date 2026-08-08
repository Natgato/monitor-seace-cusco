from __future__ import annotations

import hashlib
import io
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from html import escape
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Frame,
)

from .timeutils import LIMA

NAVY = colors.HexColor("#152A4E")
NAVY_SOFT = colors.HexColor("#2C4571")
GOLD = colors.HexColor("#B08D3E")
GOLD_LIGHT = colors.HexColor("#EFE6D2")
WARM = colors.HexColor("#F5F3EE")
TEXT = colors.HexColor("#1B2436")
TEXT_SOFT = colors.HexColor("#5B6472")
BORDER = colors.HexColor("#E2DED3")
RED = colors.HexColor("#B14A3D")
RED_BG = colors.HexColor("#F7E9E6")
AMBER = colors.HexColor("#A67A1D")
AMBER_BG = colors.HexColor("#F6EFDA")
BLUE = colors.HexColor("#2F5C8A")
BLUE_BG = colors.HexColor("#E8EFF5")

MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _register_fonts() -> tuple[str, str, str, str]:
    candidates = (
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ),
        (
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/georgia.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
        ),
    )
    from pathlib import Path

    for regular, bold, serif, serif_bold in candidates:
        if all(Path(path).exists() for path in (regular, bold, serif, serif_bold)):
            names = ("RadarSans", "RadarSansBold", "RadarSerif", "RadarSerifBold")
            for name, path in zip(names, (regular, bold, serif, serif_bold)):
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
            return names
    return "Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold"


SANS, SANS_BOLD, SERIF, SERIF_BOLD = _register_fonts()


def _plain(value: Any, fallback: str = "No informado") -> str:
    text = str(value or fallback).strip()
    return " ".join(text.split())


def _xml(value: Any, fallback: str = "No informado") -> str:
    return escape(_plain(value, fallback), quote=True)


def _normalized(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip().upper()


def _parse(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)).astimezone(LIMA) if value else None
    except (TypeError, ValueError):
        return None


def _date(value: Any, include_time: bool = False) -> str:
    moment = value if isinstance(value, datetime) else _parse(value)
    if moment is None:
        return "No informada"
    local = moment.astimezone(LIMA)
    base = f"{local.day:02d} {MONTHS[local.month - 1][:3]} {local.year}"
    if not include_time:
        return base
    suffix = "a. m." if local.hour < 12 else "p. m."
    return f"{base}, {local.hour % 12 or 12}:{local.minute:02d} {suffix}"


def _remaining(deadline: datetime | None, reference: datetime) -> str:
    if deadline is None:
        return "Sin plazo"
    total_minutes = max(0, int((deadline - reference).total_seconds() // 60))
    if total_minutes < 60:
        return f"{total_minutes} min"
    days, minutes = divmod(total_minutes, 1440)
    hours = minutes // 60
    return f"{days} d {hours} h" if days else f"{hours} h"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=SERIF_BOLD, fontSize=25, leading=29, textColor=NAVY, alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=SERIF, fontSize=12, leading=16, textColor=TEXT_SOFT),
        "slogan": ParagraphStyle("slogan", parent=base["Normal"], fontName=SANS_BOLD, fontSize=8.5, leading=12, textColor=NAVY, spaceBefore=5),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontName=SERIF_BOLD, fontSize=16, leading=19, textColor=NAVY, spaceAfter=3),
        "section_desc": ParagraphStyle("section_desc", parent=base["Normal"], fontName=SANS, fontSize=8.5, leading=12, textColor=TEXT_SOFT, spaceAfter=10),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName=SANS, fontSize=8.5, leading=13, textColor=TEXT),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName=SANS, fontSize=7.2, leading=10, textColor=TEXT_SOFT),
        "small_bold": ParagraphStyle("small_bold", parent=base["Normal"], fontName=SANS_BOLD, fontSize=7.2, leading=10, textColor=NAVY),
        "card_title": ParagraphStyle("card_title", parent=base["Normal"], fontName=SANS_BOLD, fontSize=8.2, leading=10.5, textColor=TEXT),
        "card_meta": ParagraphStyle("card_meta", parent=base["Normal"], fontName=SANS, fontSize=6.8, leading=9, textColor=TEXT_SOFT),
        "mono": ParagraphStyle("mono", parent=base["Normal"], fontName=SANS_BOLD, fontSize=6.7, leading=8.5, textColor=NAVY),
        "table": ParagraphStyle("table", parent=base["Normal"], fontName=SANS, fontSize=6.1, leading=7.5, textColor=TEXT),
        "table_bold": ParagraphStyle("table_bold", parent=base["Normal"], fontName=SANS_BOLD, fontSize=6.1, leading=7.5, textColor=NAVY),
        "table_link": ParagraphStyle("table_link", parent=base["Normal"], fontName=SANS_BOLD, fontSize=6.2, leading=7.5, textColor=NAVY, alignment=TA_CENTER),
        "center": ParagraphStyle("center", parent=base["Normal"], fontName=SANS, fontSize=7, leading=9, alignment=TA_CENTER, textColor=TEXT),
        "right": ParagraphStyle("right", parent=base["Normal"], fontName=SANS, fontSize=7, leading=9, alignment=TA_RIGHT, textColor=TEXT_SOFT),
    }


class GoldRule(Flowable):
    def __init__(self, width: float = 30 * mm):
        super().__init__()
        self.width = width
        self.height = 2

    def draw(self) -> None:
        self.canv.setFillColor(GOLD)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


def _draw_mark(canvas: Any, x: float, y: float, size: float = 18) -> None:
    radius = size / 2
    canvas.saveState()
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(0.8)
    canvas.circle(x + radius, y + radius, radius - 1, fill=0, stroke=1)
    canvas.setFillColor(GOLD_LIGHT)
    canvas.wedge(x + 1, y + 1, x + size - 1, y + size - 1, 45, 50, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.setStrokeColor(NAVY)
    canvas.line(x + 4, y + 5, x + 8, y + 10)
    canvas.line(x + 8, y + 10, x + 11, y + 7)
    canvas.line(x + 11, y + 7, x + 15, y + 12)
    canvas.line(x + 4, y + 5, x + 15, y + 5)
    canvas.setStrokeColor(GOLD)
    canvas.line(x + radius, y + 3, x + radius, y + size - 3)
    canvas.restoreState()


def _header_footer(canvas: Any, doc: Any) -> None:
    width, height = A4
    canvas.saveState()
    _draw_mark(canvas, 18 * mm, height - 19 * mm, 16)
    canvas.setFont(SERIF_BOLD, 10.5)
    canvas.setFillColor(NAVY)
    canvas.drawString(26 * mm, height - 14.8 * mm, "RADAR")
    canvas.setFillColor(GOLD)
    canvas.drawString(42 * mm, height - 14.8 * mm, "ANDINO")
    canvas.setFont(SANS, 5.5)
    canvas.setFillColor(TEXT_SOFT)
    canvas.drawString(26 * mm, height - 18 * mm, "INTELIGENCIA DE OPORTUNIDADES PÚBLICAS")
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.1)
    canvas.line(18 * mm, height - 22 * mm, width - 18 * mm, height - 22 * mm)

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 17 * mm, width - 18 * mm, 17 * mm)
    canvas.setFont(SANS, 5.5)
    canvas.setFillColor(TEXT_SOFT)
    canvas.drawString(18 * mm, 12.5 * mm, "Servicio informativo independiente. Verifique bases y cronogramas en SEACE.")
    canvas.setFont(SANS_BOLD, 6.5)
    canvas.setFillColor(NAVY)
    canvas.drawRightString(width - 18 * mm, 12.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _stat_cards(values: list[tuple[str, int]], styles: dict[str, ParagraphStyle]) -> Table:
    cards = []
    for label, value in values:
        cards.append(
            Table(
                [[_paragraph(str(value), ParagraphStyle("statn", fontName=SERIF_BOLD, fontSize=18, leading=20, textColor=NAVY))],
                 [_paragraph(escape(label.upper()), ParagraphStyle("statl", fontName=SANS, fontSize=6.3, leading=8, textColor=TEXT_SOFT))]],
                colWidths=[43 * mm],
                rowHeights=[18 * mm, 7 * mm],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), WARM),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                    ("LINEABOVE", (0, 0), (-1, 0), 2, GOLD),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]),
            )
        )
    return Table([cards[:3], cards[3:6]], colWidths=[46 * mm] * 3, rowHeights=[29 * mm] * 2, hAlign="LEFT", style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))


def _section_header(title: str, description: str, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    return [_paragraph(escape(title), styles["section"]), _paragraph(escape(description), styles["section_desc"])]


def _cover(
    rows: list[dict[str, Any]],
    items_by_contract: dict[str, int],
    generated_at: datetime,
    recipient_name: str,
    report_id: str,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    today = generated_at.date().isoformat()
    published_today = sum(1 for row in rows if str(row.get("fecha_publicacion") or "")[:10] == today)
    due_24 = sum(1 for row in rows if (deadline := _parse(row.get("fecha_vencimiento"))) and deadline <= generated_at + timedelta(hours=24))
    entities = len({_plain(row.get("ruc_entidad") or row.get("entidad"), "") for row in rows})
    cusco = sum(1 for row in rows if _normalized(row.get("departamento")) == "CUSCO")
    item_total = sum(items_by_contract.get(str(row.get("idContrato")), 0) for row in rows)
    story: list[Flowable] = [
        Spacer(1, 3 * mm),
        _paragraph("RESUMEN DIARIO DE OPORTUNIDADES", ParagraphStyle("eyebrow", fontName=SANS_BOLD, fontSize=7.5, leading=10, textColor=GOLD, tracking=1.2)),
        _paragraph("Radar Andino", styles["title"]),
        _paragraph("Contrataciones públicas vigentes en Cusco y Apurímac", styles["subtitle"]),
        _paragraph("DETECTAR <font color='#B08D3E'>·</font> PRIORIZAR <font color='#B08D3E'>·</font> PARTICIPAR", styles["slogan"]),
        Spacer(1, 2 * mm),
        GoldRule(),
        Spacer(1, 5 * mm),
    ]
    meta = [
        ["Informe preparado para", _xml(recipient_name)],
        ["Edición", f"Diaria - {_date(generated_at)}"],
        ["Cobertura", "Cusco y Apurímac"],
        ["Actualizado", _date(generated_at, include_time=True) + " (hora Perú)"],
        ["Fuente", "Buscador público de SEACE"],
    ]
    meta_table = Table(
        [[_paragraph(escape(key.upper()), styles["small"]), _paragraph(value, styles["small_bold"])] for key, value in meta],
        colWidths=[47 * mm, 94 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WARM),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]),
    )
    story.extend([
        meta_table,
        Spacer(1, 6 * mm),
        _stat_cards([
            ("Oportunidades vigentes", len(rows)),
            ("En Cusco", cusco),
            ("En Apurímac", len(rows) - cusco),
            ("Publicadas hoy", published_today),
            ("Vencen en 24 horas", due_24),
            ("Entidades públicas", entities),
        ], styles),
        Spacer(1, 4 * mm),
        _paragraph(
            f"Radar Andino consolidó <b>{len(rows)}</b> oportunidades con plazo abierto y <b>{item_total}</b> ítems registrados. "
            f"Hay <b>{due_24}</b> {'proceso' if due_24 == 1 else 'procesos'} que requieren revisión durante las próximas 24 horas.",
            styles["body"],
        ),
        Spacer(1, 6 * mm),
    ])
    consolidation = Table(
        [[_paragraph("DATOS CONSOLIDADOS AUTOMÁTICAMENTE", styles["small_bold"])],
         [_paragraph(f"Identificador: <b>{escape(report_id)}</b><br/>Registros procesados: <b>{len(rows)}</b><br/>Fuente: buscador público de SEACE", styles["small"])]],
        colWidths=[141 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WARM),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 2, GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    )
    story.append(consolidation)
    return story


def _priority_card(row: dict[str, Any], item_count: int, reference: datetime, color: colors.Color, bg: colors.Color, styles: dict[str, ParagraphStyle]) -> Table:
    deadline = _parse(row.get("fecha_vencimiento"))
    region = _plain(row.get("departamento"), "Región").title()
    url = escape(_plain(row.get("enlace_publico"), "https://prod6.seace.gob.pe/buscador-publico/"), quote=True)
    left = [
        _paragraph(f"<font color='#B08D3E'>{escape(region.upper())}</font> &nbsp; <font name='{SANS_BOLD}'>{_xml(row.get('codigo_contratacion'), 'Sin código')}</font>", styles["mono"]),
        _paragraph(_xml(row.get("descripcion"), "Descripción no informada"), styles["card_title"]),
        _paragraph(f"{_xml(row.get('entidad'), 'Entidad no informada')}<br/>{_xml(row.get('provincia'), 'Provincia no informada')} - {_xml(row.get('distrito'), 'Distrito no informado')}", styles["card_meta"]),
        _paragraph("<b>Acción sugerida:</b> revisar las bases y confirmar capacidad de atención.", ParagraphStyle("action", parent=styles["card_meta"], textColor=NAVY, backColor=GOLD_LIGHT, borderPadding=3, spaceBefore=3)),
    ]
    right = [
        _paragraph("TIEMPO RESTANTE", ParagraphStyle("cap", parent=styles["small"], fontSize=5.8, alignment=TA_RIGHT)),
        _paragraph(_remaining(deadline, reference), ParagraphStyle("remain", fontName=SERIF_BOLD, fontSize=13, leading=15, textColor=color, alignment=TA_RIGHT)),
        _paragraph(f"Vence: {_date(deadline, include_time=True)}<br/>{item_count} {'ítem' if item_count == 1 else 'ítems'}", ParagraphStyle("due", parent=styles["small"], fontSize=6.2, alignment=TA_RIGHT)),
        _paragraph(f'<link href="{url}" color="#152A4E"><u>Abrir en SEACE</u></link>', ParagraphStyle("link", parent=styles["small_bold"], alignment=TA_RIGHT, spaceBefore=3)),
    ]
    return Table(
        [[left, right]],
        colWidths=[103 * mm, 38 * mm],
        style=TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEBEFORE", (0, 0), (0, 0), 2.5, color),
            ("LINEBEFORE", (1, 0), (1, 0), 0.5, BORDER),
            ("BACKGROUND", (1, 0), (1, 0), bg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 9),
            ("RIGHTPADDING", (0, 0), (0, 0), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (1, 0), (1, 0), 7),
            ("RIGHTPADDING", (1, 0), (1, 0), 7),
        ]),
    )


def _tier(
    title: str,
    description: str,
    rows: list[dict[str, Any]],
    color: colors.Color,
    bg: colors.Color,
    item_counts: dict[str, int],
    reference: datetime,
    styles: dict[str, ParagraphStyle],
    max_cards: int = 3,
) -> list[Flowable]:
    header = Table(
        [[_paragraph(f"<b>{escape(title)}</b><br/><font size='6'>{escape(description)}</font>", ParagraphStyle("tier", parent=styles["small"], textColor=NAVY)),
          _paragraph(f"{len(rows)} OPORTUNIDADES", ParagraphStyle("tiercount", parent=styles["small_bold"], textColor=color, alignment=TA_RIGHT))]],
        colWidths=[103 * mm, 38 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WARM),
            ("LINEBEFORE", (0, 0), (0, 0), 2.5, color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )
    result: list[Flowable] = [header, Spacer(1, 2 * mm)]
    if not rows:
        result.append(_paragraph("No hay oportunidades en este nivel de urgencia.", styles["section_desc"]))
        return result
    for row in rows[:max_cards]:
        result.extend([
            KeepTogether([_priority_card(row, item_counts.get(str(row.get("idContrato")), 0), reference, color, bg, styles)]),
            Spacer(1, 2 * mm),
        ])
    if len(rows) > max_cards:
        result.append(_paragraph(f"Hay {len(rows) - max_cards} oportunidades adicionales en esta categoría; aparecen en el listado completo.", styles["small"]))
        result.append(Spacer(1, 2 * mm))
    return result


def _published_table(rows: list[dict[str, Any]], item_counts: dict[str, int], styles: dict[str, ParagraphStyle]) -> Flowable:
    headers = ["Región", "Código", "Entidad", "Descripción", "Publicación", "Vencimiento", "Ít.", "Enlace"]
    data: list[list[Any]] = [[_paragraph(escape(label), ParagraphStyle("th", fontName=SANS_BOLD, fontSize=5.7, leading=7, textColor=colors.white)) for label in headers]]
    for row in rows:
        url = escape(_plain(row.get("enlace_publico"), "https://prod6.seace.gob.pe/buscador-publico/"), quote=True)
        data.append([
            _paragraph(_xml(row.get("departamento"), "-"), styles["table_bold"]),
            _paragraph(_xml(row.get("codigo_contratacion"), "-"), styles["table_bold"]),
            _paragraph(_xml(row.get("entidad"), "-"), styles["table"]),
            _paragraph(_xml(row.get("descripcion"), "-"), styles["table"]),
            _paragraph(_date(row.get("fecha_publicacion")), styles["table"]),
            _paragraph(_date(row.get("fecha_vencimiento")), styles["table"]),
            _paragraph(str(item_counts.get(str(row.get("idContrato")), 0)), styles["center"]),
            _paragraph(f'<link href="{url}" color="#152A4E"><u>Abrir</u></link>', styles["table_link"]),
        ])
    return Table(
        data,
        repeatRows=1,
        colWidths=[14 * mm, 24 * mm, 29 * mm, 40 * mm, 18 * mm, 18 * mm, 8 * mm, 13 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WARM]),
            ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]),
    )


def _region_block(name: str, rows: list[dict[str, Any]], reference: datetime, styles: dict[str, ParagraphStyle], color: colors.Color) -> Table:
    today = reference.date().isoformat()
    published = sum(1 for row in rows if str(row.get("fecha_publicacion") or "")[:10] == today)
    due = sum(1 for row in rows if (deadline := _parse(row.get("fecha_vencimiento"))) and deadline <= reference + timedelta(hours=48))
    entities = len({_plain(row.get("ruc_entidad") or row.get("entidad"), "") for row in rows})
    provinces = Counter(_plain(row.get("provincia"), "Sin provincia") for row in rows)
    objects = Counter(_plain(row.get("objeto_contratacion"), "Otros").title() for row in rows)
    stats = Table(
        [[_paragraph(f"<b>{value}</b><br/><font size='5'>{label.upper()}</font>", ParagraphStyle("rs", parent=styles["center"], fontName=SERIF_BOLD, fontSize=12, leading=13, textColor=NAVY)) for label, value in (("Total", len(rows)), ("Publicadas hoy", published), ("Próximas a vencer", due), ("Entidades", entities))]],
        colWidths=[35 * mm] * 4,
        style=TableStyle([("BOX", (0, 0), (-1, -1), 0.5, BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER), ("BACKGROUND", (0, 0), (-1, -1), WARM), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]),
    )
    detail_lines = ["<b>Provincias con más oportunidades</b>"]
    maximum = max(provinces.values(), default=1)
    for province, count in provinces.most_common(5):
        blocks = "|" * max(1, round((count / maximum) * 10))
        detail_lines.append(f"{escape(province)} &nbsp; <font color='{color.hexval()}'>{blocks}</font> &nbsp; {count}")
    detail_lines.append("<br/><b>Tipo de contratación</b>")
    detail_lines.extend(f"{escape(label)}: {count}" for label, count in objects.most_common(4))
    body = _paragraph("<br/>".join(detail_lines), ParagraphStyle("regiondetail", parent=styles["small"], leading=11))
    header = _paragraph(f"<font color='white'><b>{escape(name)}</b> &nbsp; {len(rows)} oportunidades vigentes</font>", ParagraphStyle("rh", fontName=SERIF_BOLD, fontSize=11, leading=14, textColor=colors.white))
    return Table(
        [[header], [stats], [body]],
        colWidths=[141 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (0, 0), 7),
            ("BOTTOMPADDING", (0, 0), (0, 0), 7),
            ("TOPPADDING", (0, 1), (0, -1), 8),
            ("BOTTOMPADDING", (0, 1), (0, -1), 8),
        ]),
    )


def _full_listing(rows: Iterable[dict[str, Any]], item_counts: dict[str, int], styles: dict[str, ParagraphStyle]) -> Table:
    headers = ["Región", "Código", "Entidad", "Descripción resumida", "Provincia", "Publicación", "Vence", "Ít.", "Link"]
    brand_row = [
        _paragraph(
            "<b>RADAR ANDINO</b> <font color='#B08D3E'>·</font> LISTADO VIGENTE",
            ParagraphStyle("flbrand", fontName=SANS, fontSize=6, leading=7, textColor=NAVY),
        )
    ] + [""] * (len(headers) - 1)
    data: list[list[Any]] = [
        brand_row,
        [_paragraph(escape(label), ParagraphStyle("flh", fontName=SANS_BOLD, fontSize=5.2, leading=6.4, textColor=colors.white)) for label in headers],
    ]
    for row in rows:
        url = escape(_plain(row.get("enlace_publico"), "https://prod6.seace.gob.pe/buscador-publico/"), quote=True)
        description = _plain(row.get("descripcion"), "-")
        if len(description) > 170:
            description = description[:167].rstrip() + "..."
        entity = _plain(row.get("entidad"), "-")
        if len(entity) > 80:
            entity = entity[:77].rstrip() + "..."
        data.append([
            _paragraph(_xml(row.get("departamento"), "-"), styles["table_bold"]),
            _paragraph(_xml(row.get("codigo_contratacion"), "-"), styles["table_bold"]),
            _paragraph(escape(entity), styles["table"]),
            _paragraph(escape(description), styles["table"]),
            _paragraph(_xml(row.get("provincia"), "-"), styles["table"]),
            _paragraph(_date(row.get("fecha_publicacion")), styles["table"]),
            _paragraph(_date(row.get("fecha_vencimiento")), styles["table"]),
            _paragraph(str(item_counts.get(str(row.get("idContrato")), 0)), styles["center"]),
            _paragraph(f'<link href="{url}" color="#152A4E"><u>Abrir</u></link>', styles["table_link"]),
        ])
    return Table(
        data,
        repeatRows=2,
        splitByRow=1,
        colWidths=[16 * mm, 21 * mm, 27 * mm, 38 * mm, 18 * mm, 16 * mm, 16 * mm, 7 * mm, 11 * mm],
        style=TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), WARM),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, GOLD),
            ("BACKGROUND", (0, 1), (-1, 1), NAVY),
            ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, WARM]),
            ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.4),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]),
    )


def build_daily_pdf(
    contracts: list[dict[str, Any]],
    items_by_contract: dict[str, int],
    generated_at: datetime,
    recipient_name: str = "Suscriptor de Radar Andino",
) -> bytes:
    """Create the Radar Andino daily report entirely from already persisted data."""
    reference = generated_at.astimezone(LIMA)
    rows = sorted(contracts, key=lambda row: row.get("fecha_vencimiento") or "9999")
    signature = "|".join(str(row.get("idContrato")) for row in rows)
    digest = hashlib.sha256(f"{reference.isoformat()}|{signature}".encode("utf-8")).hexdigest()[:6].upper()
    report_id = f"RA-CUS-APU-{reference.strftime('%Y%m%d')}-{digest}"
    styles = _styles()
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=27 * mm,
        bottomMargin=21 * mm,
        title=f"Radar Andino - Resumen diario {_date(reference)}",
        author="Radar Andino",
        subject="Oportunidades públicas vigentes en Cusco y Apurímac",
    )
    def page_frame(frame_id: str) -> Frame:
        return Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id=frame_id,
            leftPadding=6,
            rightPadding=6,
            topPadding=6,
            bottomPadding=6,
        )

    doc.addPageTemplates([
        PageTemplate(id="Report", frames=[page_frame("report-frame")], onPage=_header_footer),
    ])

    story: list[Flowable] = []
    story.extend(_cover(rows, items_by_contract, reference, recipient_name, report_id, styles))
    story.append(PageBreak())

    story.extend(_section_header("Radar de acción del día", "Oportunidades agrupadas por urgencia para facilitar la revisión y priorización.", styles))
    urgent = [row for row in rows if (deadline := _parse(row.get("fecha_vencimiento"))) and deadline <= reference + timedelta(hours=24)]
    review = [row for row in rows if (deadline := _parse(row.get("fecha_vencimiento"))) and reference + timedelta(hours=24) < deadline <= reference + timedelta(hours=48)]
    plan = [row for row in rows if (deadline := _parse(row.get("fecha_vencimiento"))) is None or deadline > reference + timedelta(hours=48)]
    story.extend(_tier("Actuar hoy", "Vence en menos de 24 horas", urgent, RED, RED_BG, items_by_contract, reference, styles))
    story.extend(_tier("Revisar ahora", "Vence entre 24 y 48 horas", review, AMBER, AMBER_BG, items_by_contract, reference, styles))
    story.extend(_tier("Planificar", "Vence después de 48 horas", plan, BLUE, BLUE_BG, items_by_contract, reference, styles, max_cards=1))
    story.append(PageBreak())

    today = reference.date().isoformat()
    published_today = [row for row in rows if str(row.get("fecha_publicacion") or "")[:10] == today]
    story.extend(_section_header("Publicadas hoy", f"Nuevas contrataciones registradas durante la jornada del {_date(reference)}.", styles))
    if published_today:
        story.append(_published_table(published_today, items_by_contract, styles))
        story.append(Spacer(1, 4 * mm))
        story.append(_paragraph(f"Se detectaron {len(published_today)} publicaciones nuevas durante la jornada.", styles["body"]))
    else:
        story.append(Table([[_paragraph("Hoy todavía no se registraron nuevas publicaciones con plazo abierto.", styles["body"])]], colWidths=[141 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), WARM), ("BOX", (0, 0), (-1, -1), 0.5, BORDER), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12)])))
    if published_today:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 9 * mm))

    story.extend(_section_header("Resumen por región", "Panorama comparativo de la actividad de contrataciones en Cusco y Apurímac.", styles))
    cusco_rows = [row for row in rows if _normalized(row.get("departamento")) == "CUSCO"]
    apurimac_rows = [row for row in rows if _normalized(row.get("departamento")) == "APURIMAC"]
    story.extend([
        KeepTogether([_region_block("Cusco", cusco_rows, reference, styles, NAVY)]),
        Spacer(1, 7 * mm),
        KeepTogether([_region_block("Apurímac", apurimac_rows, reference, styles, GOLD)]),
        PageBreak(),
    ])

    story.extend([
        Table(
            [[_paragraph(
                "ANEXO OPERATIVO <font color='#B08D3E'>·</font> CUSCO Y APURÍMAC",
                ParagraphStyle("appendix_eyebrow", fontName=SANS_BOLD, fontSize=7, leading=9, textColor=NAVY),
            )]],
            colWidths=[141 * mm],
            style=TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 1, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 6 * mm),
    ])
    story.extend(_section_header("Listado completo de oportunidades vigentes", "Procesos con plazo abierto, ordenados por fecha de vencimiento. Los enlaces llevan a la ficha pública de SEACE.", styles))
    if rows:
        story.append(_full_listing(rows, items_by_contract, styles))
    else:
        story.append(_paragraph("No hay oportunidades vigentes registradas para Cusco o Apurímac.", styles["body"]))
    doc.build(story)
    return buffer.getvalue()
