# Monitor SEACE Cusco

Monitor horario de contrataciones vigentes de Cusco en SEACE. Guarda CSV actualizados y ofrece un panel para consultar oportunidades. No usa autenticación, navegador ni descarga documentos.

El panel en `web/` presenta métricas, radar de vencimientos, filtros, detalle de ítems y un asistente local. Su lógica sigue arquitectura limpia; consulta [ARCHITECTURE.md](ARCHITECTURE.md).

## Configuración de GitHub

1. En **Settings → Actions → General**, selecciona **Read and write permissions**.
2. Ejecuta **Actions → Monitor SEACE → Run workflow**. La primera ejecución crea el seed.

Las notificaciones están desactivadas por defecto. El canal recomendado es Gmail:

1. Activa la verificación en dos pasos de la cuenta remitente y crea una contraseña de aplicación.
2. Crea los Secrets `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` y `ALERT_EMAIL_TO`.
3. Crea la variable de repositorio `NOTIFICATION_CHANNEL=gmail`.

El monitor se ejecuta una vez por hora, al minuto 17. `workflow_dispatch` permite una ejecución manual adicional únicamente cuando el usuario la solicita.

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

## Panel web local

Desde la raíz ejecuta `python -m http.server 8000` y abre `http://localhost:8000/web/`. El panel lee los archivos de `data/` y no contiene contrataciones simuladas.

Pruebas del panel: `npm run test:web`.
