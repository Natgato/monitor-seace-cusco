from __future__ import annotations

import sys

from .config import Config
from .notifier import send_messages
from .timeutils import iso_now


def run() -> None:
    config = Config()
    send_messages(
        config,
        [f"<b>Correo configurado correctamente</b><br>El Monitor SEACE Cusco puede enviar alertas.<br>Prueba realizada: {iso_now()}"],
        subject="Prueba correcta — Monitor SEACE Cusco",
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"Error enviando el correo de prueba: {exc}", file=sys.stderr)
        sys.exit(1)
