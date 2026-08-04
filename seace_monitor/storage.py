from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import Config

CONTRACT_FIELDS = ["idContrato", "codigo_contratacion", "estado", "objeto_contratacion", "entidad", "ruc_entidad", "departamento", "provincia", "distrito", "fecha_publicacion", "fecha_vencimiento", "tiempo_restante_texto", "moneda", "monto_referencial", "descripcion", "enlace_publico", "fecha_ultima_actualizacion", "fecha_vencimiento_raw"]
ITEM_FIELDS = ["idContrato", "idItem", "numero_item", "codigo_cubso", "descripcion_item", "cantidad", "unidad_medida", "moneda", "monto", "fecha_ultima_actualizacion"]


def _atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name): os.unlink(temp_name)


def load_state(config: Config) -> dict[str, Any]:
    defaults = {"initialized": False, "contratos_conocidos": [], "fecha_seed": None, "ultima_ejecucion": None,
        "ultima_ejecucion_exitosa": None, "ultimo_error": None, "fallos_consecutivos": 0, "total_contratos": 0,
        "fecha_ultima_notificacion": None, "fecha_ultima_alerta_watchdog": None, "departamentos_inicializados": []}
    defaults["ultimos_contratos_nuevos"] = []
    try:
        loaded = json.loads(config.state_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict) or not isinstance(loaded.get("contratos_conocidos", []), list): raise ValueError
        defaults.update(loaded)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        pass
    if defaults["initialized"] and not defaults["departamentos_inicializados"]:
        # Migración del monitor original, que solamente cubría Cusco.
        defaults["departamentos_inicializados"] = ["CUSCO"]
    return defaults


def save_state(config: Config, state: dict[str, Any]) -> None:
    _atomic(config.state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists(): return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    import io
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    def clean(value: Any) -> Any:
        if value is None:
            return ""
        return value.strip() if isinstance(value, str) else value

    writer.writerows([{field: clean(row.get(field)) for field in fields} for row in rows])
    _atomic(path, output.getvalue(), encoding="utf-8-sig")
