# Monitor SEACE Cusco

Monitor horario de contrataciones vigentes de Cusco en SEACE. Guarda un CSV actualizado y avisa por Telegram únicamente por contrataciones nuevas. No usa autenticación, navegador ni descarga documentos.

## Configuración de GitHub

1. En **Settings → Actions → General**, selecciona **Read and write permissions**.
2. En **Settings → Secrets and variables → Actions**, crea `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
3. Ejecuta **Actions → Monitor SEACE → Run workflow**. La primera ejecución crea el seed y manda un único aviso de inicialización.

Después se ejecuta aproximadamente cada hora. Las horas guardadas usan `America/Lima` (UTC-5). El cron de GitHub puede retrasarse algunos minutos.

## Uso local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env # carga las variables en tu entorno; no subas .env
$env:TELEGRAM_BOT_TOKEN = '...'
$env:TELEGRAM_CHAT_ID = '...'
python -m seace_monitor.monitor
```

Datos persistentes: `data/contrataciones.csv`, `data/items.csv` y `data/estado.json`. Los CSV se escriben de forma atómica, con UTF-8 BOM y upsert por contrato/ítem.
