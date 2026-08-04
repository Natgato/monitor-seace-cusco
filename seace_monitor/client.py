from __future__ import annotations

import time
from typing import Any

import requests

from .config import Config
from .timeutils import parse_seace

BASE = "https://prod6.seace.gob.pe/v1/s8uit-services/buscadorpublico"


class SeaceError(RuntimeError):
    pass


def belongs_to_year(item: dict[str, Any], year: int) -> bool:
    published = parse_seace(item.get("fecPublica"))
    if published is None:
        raise SeaceError(f"Contrato {item.get('idContrato', '?')} sin fecha de publicación válida")
    return published.year == year


class SeaceClient:
    def __init__(self, config: Config):
        self.config = config
        self.http_attempts = 0
        self.search_requests = 0
        self.detail_requests = 0
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "monitor-seace-regional/1.0"})

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self.http_attempts += 1
                response = self.session.get(
                    f"{BASE}/{path}",
                    params=params,
                    timeout=(self.config.connect_timeout, self.config.read_timeout),
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise SeaceError(f"HTTP {response.status_code}")
                response.raise_for_status()
                if "json" not in response.headers.get("Content-Type", "").lower():
                    raise SeaceError("SEACE devolvió una respuesta que no es JSON")
                payload = response.json()
                if not isinstance(payload, dict):
                    raise SeaceError("SEACE devolvió un JSON con formato inesperado")
                return payload
            except (requests.RequestException, ValueError, SeaceError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        raise SeaceError(f"No se pudo consultar SEACE: {last_error}")

    def search_page(self, page: int, department_code: int) -> dict[str, Any]:
        self.search_requests += 1
        return self._get(
            "contrataciones/buscador",
            {
                "codigo_departamento": department_code,
                "lista_estado_contrato": 2,
                "lista_codigo_objeto": "1,2",
                "palabra_clave": "",
                "orden": 2,
                "page": page,
                "page_size": self.config.page_size,
                "anio": self.config.year,
            },
        )

    def fetch_all(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for department_code, department_name in self.config.departments:
            for page in range(1, self.config.max_pages + 1):
                payload = self.search_page(page, department_code)
                data, pageable = payload.get("data"), payload.get("pageable")
                if not isinstance(data, list) or not isinstance(pageable, dict):
                    raise SeaceError("Estructura inesperada en respuesta del buscador")
                total = pageable.get("totalElements")
                if not isinstance(total, int) or total < 0:
                    raise SeaceError("totalElements inválido en respuesta del buscador")
                expected_pages = (total + self.config.page_size - 1) // self.config.page_size
                for item in data:
                    if not isinstance(item, dict) or item.get("idContrato") is None:
                        raise SeaceError("Contrato sin idContrato en respuesta del buscador")
                    if not belongs_to_year(item, self.config.year):
                        continue
                    key = str(item["idContrato"])
                    if key not in seen:
                        seen.add(key)
                        record = dict(item)
                        record["_requested_department"] = department_name
                        records.append(record)
                if page >= expected_pages:
                    break
                time.sleep(self.config.page_delay_seconds)
            else:
                raise SeaceError(
                    f"Se alcanzó el máximo de {self.config.max_pages} páginas para {department_name}"
                )
        return records

    def detail(self, contract_id: str) -> dict[str, Any]:
        self.detail_requests += 1
        payload = self._get("contrataciones/listar-completo", {"id_contrato": contract_id})
        if not isinstance(payload.get("uitContratoCompletoProjection"), dict):
            raise SeaceError(f"Detalle inesperado para contrato {contract_id}")
        if not isinstance(payload.get("uitContratoItemProjectionList", []), list):
            raise SeaceError(f"Ítems inesperados para contrato {contract_id}")
        return payload
