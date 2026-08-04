from __future__ import annotations

import logging
import sys
from typing import Any

from .client import SeaceClient
from .config import Config
from .notifier import build_messages, send_messages
from .storage import CONTRACT_FIELDS, ITEM_FIELDS, load_state, read_csv, save_state, write_csv
from .timeutils import iso_now, iso_seace, parse_seace, remaining_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)


def contract_row(listing: dict[str, Any], detail: dict[str, Any] | None, stamp: str) -> dict[str, Any]:
    source = (detail or {}).get("uitContratoCompletoProjection", {}) | listing
    contract_id = str(listing["idContrato"])
    finish_raw = listing.get("fecFinCotizacion") or source.get("fecFinCotizacion")
    finish = iso_seace(finish_raw)
    location = source.get("nomDistrito") or source.get("nomDistritoExt") or ""
    place = str(location).split("/")
    items = (detail or {}).get("uitContratoItemProjectionList", [])
    return {"idContrato": contract_id, "codigo_contratacion": source.get("nroDescripcion") or listing.get("desContratacion"),
        "estado": source.get("nomEstadoContrato"), "objeto_contratacion": source.get("nomObjetoContrato"), "entidad": source.get("nomEntidad"),
        "ruc_entidad": source.get("rucEntidad"), "departamento": place[0] if place else "CUSCO", "provincia": place[1] if len(place)>1 else None,
        "distrito": place[2] if len(place)>2 else None, "fecha_publicacion": iso_seace(source.get("fecPublica") or listing.get("fecPublica")),
        "fecha_vencimiento": finish, "tiempo_restante_texto": remaining_text(parse_seace(finish_raw)), "moneda": source.get("nomMoneda"),
        "monto_referencial": source.get("montoReferencial"), "descripcion": source.get("desObjetoContrato") or listing.get("desObjetoContrato"),
        "enlace_publico": f"https://prod6.seace.gob.pe/buscador-publico/contrataciones/{contract_id}", "fecha_ultima_actualizacion": stamp,
        "fecha_vencimiento_raw": finish_raw, "cantidad_items": len(items)}


def item_rows(contract_id: str, detail: dict[str, Any], stamp: str) -> list[dict[str, Any]]:
    rows=[]
    for index, item in enumerate(detail.get("uitContratoItemProjectionList", []), 1):
        rows.append({"idContrato": contract_id, "idItem": item.get("idContratoItem") or item.get("idCubso") or "", "numero_item": index,
          "codigo_cubso": item.get("codCubso"), "descripcion_item": item.get("descripcionItem") or item.get("nomCubso"), "cantidad": item.get("cantidad"),
          "unidad_medida": item.get("nomUnidadMedida"), "moneda": item.get("nomMoneda"), "monto": item.get("precioTotal"), "fecha_ultima_actualizacion": stamp})
    return rows


def changed(listing: dict[str, Any], existing: dict[str, str] | None) -> bool:
    if not existing: return True
    return (
        str(listing.get("nomEstadoContrato") or "") != str(existing.get("estado") or "")
        or str(listing.get("fecFinCotizacion") or "") != str(existing.get("fecha_vencimiento_raw") or "")
        or iso_seace(listing.get("fecPublica")) != (existing.get("fecha_publicacion") or None)
    )


def run() -> None:
    config, stamp = Config(), iso_now()
    state = load_state(config)
    try:
        listings = SeaceClient(config).fetch_all() # no writes until pagination succeeds
        existing_rows = {row["idContrato"]: row for row in read_csv(config.contracts_path)}
        existing_items = read_csv(config.items_path)
        rows, changed_ids, details = dict(existing_rows), set(), {}
        for listing in listings:
            contract_id = str(listing["idContrato"])
            if changed(listing, existing_rows.get(contract_id)):
                details[contract_id] = SeaceClient(config).detail(contract_id)
                rows[contract_id] = contract_row(listing, details[contract_id], stamp)
                changed_ids.add(contract_id)
            else:
                rows[contract_id] = existing_rows[contract_id]
        listed_ids = {str(x["idContrato"]) for x in listings}
        rows = {key: value for key, value in rows.items() if key in listed_ids}
        known = {str(value) for value in state["contratos_conocidos"]}
        new_ids = listed_ids - known
        new_rows = [rows[key] for key in sorted(new_ids)]
        if not state["initialized"]:
            # Seed never sends individual alerts.
            write_csv(config.contracts_path, CONTRACT_FIELDS, sorted(rows.values(), key=lambda x: x.get("fecha_publicacion") or "", reverse=True))
            all_items = [x for x in existing_items if x["idContrato"] in listed_ids and x["idContrato"] not in changed_ids]
            all_items.extend(row for cid, detail in details.items() for row in item_rows(cid, detail, stamp))
            write_csv(config.items_path, ITEM_FIELDS, all_items)
            state.update({"initialized": True, "contratos_conocidos": sorted(known | listed_ids), "fecha_seed": stamp, "ultima_ejecucion": stamp,
                "ultima_ejecucion_exitosa": stamp, "ultimo_error": None, "fallos_consecutivos": 0, "total_contratos": len(listed_ids)})
            send_messages(config, [f"<b>Monitor SEACE inicializado correctamente.</b>\nSe registraron {len(listed_ids)} contrataciones vigentes de Cusco.\nDesde la próxima ejecución solo recibirás avisos de contrataciones nuevas."])
            save_state(config, state); return
        # Send before state/CSV persistence: notification errors leave all data untouched for retry.
        if new_rows: send_messages(config, build_messages(new_rows, stamp))
        write_csv(config.contracts_path, CONTRACT_FIELDS, sorted(rows.values(), key=lambda x: x.get("fecha_publicacion") or "", reverse=True))
        all_items = [x for x in existing_items if x["idContrato"] in listed_ids and x["idContrato"] not in changed_ids]
        all_items.extend(row for cid, detail in details.items() for row in item_rows(cid, detail, stamp))
        write_csv(config.items_path, ITEM_FIELDS, all_items)
        state.update({"contratos_conocidos": sorted(known | listed_ids), "ultima_ejecucion": stamp, "ultima_ejecucion_exitosa": stamp,
            "ultimo_error": None, "fallos_consecutivos": 0, "total_contratos": len(listed_ids), "fecha_ultima_notificacion": stamp if new_rows else state.get("fecha_ultima_notificacion")})
        save_state(config, state)
    except Exception as exc:
        LOG.exception("Ejecución fallida")
        # Error metadata is the only permitted write on failure; datasets remain intact.
        state.update({"ultima_ejecucion": stamp, "ultimo_error": str(exc), "fallos_consecutivos": int(state.get("fallos_consecutivos", 0))+1})
        save_state(config, state)
        raise


if __name__ == "__main__":
    try: run()
    except Exception: sys.exit(1)
