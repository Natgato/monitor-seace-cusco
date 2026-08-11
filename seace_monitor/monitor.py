from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any

from .client import SeaceClient, SeaceError
from .config import Config
from .email_templates import build_new_contracts_email
from .notifier import build_messages, send_messages
from .storage import CONTRACT_FIELDS, ITEM_FIELDS, load_state, read_csv, save_state, write_csv
from .timeutils import iso_now, iso_seace, parse_seace, remaining_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)


def contract_row(
    listing: dict[str, Any],
    detail: dict[str, Any] | None,
    stamp: str,
    requirement_url: str | None = None,
    requirement_checked: bool = False,
) -> dict[str, Any]:
    source = (detail or {}).get("uitContratoCompletoProjection", {}) | listing
    contract_id = str(listing["idContrato"])
    finish_raw = listing.get("fecFinCotizacion") or source.get("fecFinCotizacion")
    finish = iso_seace(finish_raw)
    items = (detail or {}).get("uitContratoItemProjectionList", [])
    item_location = items[0] if items else {}
    location = (
        item_location.get("nomDistrito")
        or item_location.get("nomDistritoExt")
        or source.get("nomDistrito")
        or source.get("nomDistritoExt")
        or listing.get("_requested_department")
        or ""
    )
    place = [part.strip() for part in str(location).split("/")]
    return {
        "idContrato": contract_id,
        "codigo_contratacion": source.get("nroDescripcion") or listing.get("desContratacion"),
        "estado": source.get("nomEstadoContrato"),
        "objeto_contratacion": source.get("nomObjetoContrato"),
        "entidad": source.get("nomEntidad"),
        "ruc_entidad": source.get("rucEntidad"),
        "departamento": place[0] if place and place[0] else listing.get("_requested_department"),
        "provincia": place[1] if len(place) > 1 else None,
        "distrito": place[2] if len(place) > 2 else None,
        "fecha_publicacion": iso_seace(source.get("fecPublica") or listing.get("fecPublica")),
        "fecha_vencimiento": finish,
        "tiempo_restante_texto": remaining_text(parse_seace(finish_raw)),
        "moneda": source.get("nomMoneda"),
        "monto_referencial": source.get("montoReferencial"),
        "descripcion": source.get("desObjetoContrato") or listing.get("desObjetoContrato"),
        "enlace_publico": f"https://prod6.seace.gob.pe/buscador-publico/contrataciones/{contract_id}",
        "enlace_requerimiento": requirement_url,
        "requerimiento_consultado": "1" if requirement_checked else "",
        "fecha_ultima_actualizacion": stamp,
        "fecha_vencimiento_raw": finish_raw,
        "cantidad_items": len(items),
    }


def item_rows(contract_id: str, detail: dict[str, Any], stamp: str) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(detail.get("uitContratoItemProjectionList", []), 1):
        rows.append(
            {
                "idContrato": contract_id,
                "idItem": item.get("idContratoItem") or item.get("idCubso") or "",
                "numero_item": index,
                "codigo_cubso": item.get("codCubso"),
                "descripcion_item": item.get("descripcionItem") or item.get("nomCubso"),
                "cantidad": item.get("cantidad"),
                "unidad_medida": item.get("nomUnidadMedida"),
                "moneda": item.get("nomMoneda"),
                "monto": item.get("precioTotal"),
                "fecha_ultima_actualizacion": stamp,
            }
        )
    return rows


def changed(listing: dict[str, Any], existing: dict[str, str] | None) -> bool:
    if not existing:
        return True
    return (
        str(listing.get("nomEstadoContrato") or "") != str(existing.get("estado") or "")
        or str(listing.get("fecFinCotizacion") or "") != str(existing.get("fecha_vencimiento_raw") or "")
        or iso_seace(listing.get("fecPublica")) != (existing.get("fecha_publicacion") or None)
    )


def _requirement_was_checked(row: dict[str, Any]) -> bool:
    return str(row.get("requerimiento_consultado") or "").strip().lower() in {"1", "true", "si", "sí"}


def hydrate_requirement_links(
    client: SeaceClient,
    rows: dict[str, dict[str, Any]],
    contract_ids: list[str],
) -> int:
    """Resolve optional requirement files without making them critical to the monitor run."""
    completed = 0
    for contract_id in contract_ids:
        try:
            rows[contract_id]["enlace_requerimiento"] = client.requirement_url(contract_id) or ""
            rows[contract_id]["requerimiento_consultado"] = "1"
            completed += 1
        except SeaceError as exc:
            LOG.warning("No se pudo consultar el requerimiento de %s: %s", contract_id, exc)
    return completed


def requirement_backfill_ids(
    rows: dict[str, dict[str, Any]],
    excluded_ids: set[str],
    reference: datetime,
    limit: int,
) -> list[str]:
    """Prioritize open deadlines; expired contracts never consume file requests."""
    candidates: list[str] = []
    for contract_id, row in rows.items():
        if contract_id in excluded_ids or _requirement_was_checked(row):
            continue
        raw_deadline = row.get("fecha_vencimiento")
        if raw_deadline:
            try:
                if datetime.fromisoformat(str(raw_deadline)) <= reference:
                    continue
            except ValueError:
                pass
        candidates.append(contract_id)
    return sorted(
        candidates,
        key=lambda contract_id: rows[contract_id].get("fecha_vencimiento") or "9999",
    )[:max(limit, 0)]


def _send_new_alert(config: Config, new_rows: list[dict[str, Any]], stamp: str) -> None:
    if config.notification_channel == "gmail":
        html = build_new_contracts_email(new_rows, datetime.fromisoformat(stamp))
        subject = f"Nuevas oportunidades SEACE ({len(new_rows)}) — Cusco y Apurímac"
        send_messages(config, [html], subject=subject)
    else:
        send_messages(config, build_messages(new_rows, stamp))


def run() -> None:
    config, stamp = Config(), iso_now()
    state = load_state(config)
    try:
        client = SeaceClient(config)
        listings = client.fetch_all()  # No se escribe nada hasta completar toda la paginación.
        existing_rows = {row["idContrato"]: row for row in read_csv(config.contracts_path)}
        existing_items = read_csv(config.items_path)
        rows, changed_ids, details = dict(existing_rows), set(), {}
        for listing in listings:
            contract_id = str(listing["idContrato"])
            if changed(listing, existing_rows.get(contract_id)):
                details[contract_id] = client.detail(contract_id)
                existing = existing_rows.get(contract_id, {})
                rows[contract_id] = contract_row(
                    listing,
                    details[contract_id],
                    stamp,
                    existing.get("enlace_requerimiento") or None,
                    _requirement_was_checked(existing),
                )
                changed_ids.add(contract_id)
            else:
                preserved = dict(existing_rows[contract_id])
                if not preserved.get("departamento"):
                    preserved["departamento"] = listing.get("_requested_department")
                rows[contract_id] = preserved

        listed_ids = {str(item["idContrato"]) for item in listings}
        rows = {key: value for key, value in rows.items() if key in listed_ids}
        known = {str(value) for value in state["contratos_conocidos"]}
        configured_departments = {name for _, name in config.departments}
        initialized_departments = {str(name).upper() for name in state["departamentos_inicializados"]}
        new_departments = configured_departments - initialized_departments
        regional_seed_ids = {
            str(item["idContrato"])
            for item in listings
            if str(item.get("_requested_department") or "").upper() in new_departments
        }
        new_ids = (listed_ids - known) - regional_seed_ids
        immediate_ids = sorted(new_ids) if state["initialized"] else []
        hydrate_requirement_links(client, rows, immediate_ids)

        pending_backfill = requirement_backfill_ids(
            rows,
            new_ids,
            datetime.fromisoformat(stamp),
            config.file_backfill_limit,
        )
        backfilled = hydrate_requirement_links(client, rows, pending_backfill)
        new_rows = [rows[key] for key in sorted(new_ids)]
        LOG.info(
            "Peticiones SEACE: listado=%s detalle=%s archivos=%s (relleno=%s) intentos_http=%s",
            client.search_requests,
            client.detail_requests,
            client.file_requests,
            backfilled,
            client.http_attempts,
        )
        if new_departments and state["initialized"]:
            LOG.info(
                "Inicialización silenciosa de %s: %s contratos históricos no generarán alerta",
                ", ".join(sorted(new_departments)),
                len(regional_seed_ids),
            )

        all_items = [
            item
            for item in existing_items
            if item["idContrato"] in listed_ids and item["idContrato"] not in changed_ids
        ]
        all_items.extend(row for cid, detail in details.items() for row in item_rows(cid, detail, stamp))
        item_counts: dict[str, int] = {}
        for item in all_items:
            item_id = str(item.get("idContrato") or "")
            item_counts[item_id] = item_counts.get(item_id, 0) + 1
        for row in new_rows:
            row["cantidad_items"] = item_counts.get(str(row.get("idContrato")), row.get("cantidad_items", 0))

        if not state["initialized"]:
            write_csv(
                config.contracts_path,
                CONTRACT_FIELDS,
                sorted(rows.values(), key=lambda row: row.get("fecha_publicacion") or "", reverse=True),
            )
            write_csv(config.items_path, ITEM_FIELDS, all_items)
            state.update(
                {
                    "initialized": True,
                    "departamentos_inicializados": sorted(configured_departments),
                    "contratos_conocidos": sorted(known | listed_ids),
                    "fecha_seed": stamp,
                    "ultima_ejecucion": stamp,
                    "ultima_ejecucion_exitosa": stamp,
                    "ultimo_error": None,
                    "fallos_consecutivos": 0,
                    "total_contratos": len(listed_ids),
                    "ultimos_contratos_nuevos": [],
                }
            )
            if config.notifications_enabled:
                send_messages(
                    config,
                    [
                        "<b>Monitor SEACE inicializado correctamente.</b><br>"
                        f"Se registraron {len(listed_ids)} contrataciones de Cusco y Apurímac. "
                        "Desde la próxima ejecución solo se avisarán publicaciones nuevas."
                    ],
                    subject="Monitor SEACE — inicialización completada",
                )
            save_state(config, state)
            return

        # Si falla la notificación, no se persisten cambios para poder reintentarla.
        if new_rows and config.notifications_enabled:
            _send_new_alert(config, new_rows, stamp)
        known_after_run = known | regional_seed_ids
        if config.notifications_enabled:
            known_after_run |= new_ids
        write_csv(
            config.contracts_path,
            CONTRACT_FIELDS,
            sorted(rows.values(), key=lambda row: row.get("fecha_publicacion") or "", reverse=True),
        )
        write_csv(config.items_path, ITEM_FIELDS, all_items)
        state.update(
            {
                "departamentos_inicializados": sorted(initialized_departments | configured_departments),
                # Una ejecución diagnóstica sin canal no consume alertas pendientes.
                "contratos_conocidos": sorted(known_after_run),
                "ultima_ejecucion": stamp,
                "ultima_ejecucion_exitosa": stamp,
                "ultimo_error": None,
                "fallos_consecutivos": 0,
                "total_contratos": len(listed_ids),
                "fecha_ultima_notificacion": (
                    stamp if new_rows and config.notifications_enabled else state.get("fecha_ultima_notificacion")
                ),
                "ultimos_contratos_nuevos": sorted(new_ids),
            }
        )
        save_state(config, state)
    except Exception as exc:
        LOG.exception("Ejecución fallida")
        state.update(
            {
                "ultima_ejecucion": stamp,
                "ultimo_error": str(exc),
                "fallos_consecutivos": int(state.get("fallos_consecutivos", 0)) + 1,
            }
        )
        save_state(config, state)
        raise


if __name__ == "__main__":
    try:
        run()
    except Exception:
        sys.exit(1)
