from __future__ import annotations

from datetime import datetime, timedelta
import sys

from .config import Config
from .notifier import send_messages
from .storage import load_state, save_state
from .timeutils import LIMA, iso_now, now


def run() -> None:
    config, state = Config(), load_state(Config())
    if not config.notifications_enabled: return
    if not state.get("initialized") or not state.get("ultima_ejecucion_exitosa"): return
    last_ok = datetime.fromisoformat(state["ultima_ejecucion_exitosa"]).astimezone(LIMA)
    last_alert = datetime.fromisoformat(state["fecha_ultima_alerta_watchdog"]).astimezone(LIMA) if state.get("fecha_ultima_alerta_watchdog") else None
    threshold = timedelta(hours=config.watchdog_threshold_hours)
    if now() - last_ok > threshold and (not last_alert or now() - last_alert > threshold):
        send_messages(config, [f"<b>Alerta watchdog SEACE</b>\nEl monitor no registra una ejecución exitosa desde {state['ultima_ejecucion_exitosa']}."], subject="Alerta — monitor SEACE sin ejecuciones exitosas")
        state["fecha_ultima_alerta_watchdog"] = iso_now(); save_state(config, state)


if __name__ == "__main__":
    try: run()
    except Exception: sys.exit(1)
