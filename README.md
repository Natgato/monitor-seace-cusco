# Monitor SEACE Cusco y Apurímac

Monitor horario de contrataciones vigentes de Cusco y Apurímac en SEACE. Guarda CSV actualizados y ofrece un panel para consultar oportunidades. No usa autenticación en SEACE, navegador ni descarga documentos.

El panel en `web/` presenta métricas, radar de vencimientos, filtros, detalle de ítems y un asistente local. Su lógica sigue arquitectura limpia; consulta [ARCHITECTURE.md](ARCHITECTURE.md).

## Configuración de GitHub

1. En **Settings → Actions → General**, selecciona **Read and write permissions**.
2. Crea los Secrets `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` y `ALERT_EMAIL_TO`. Para varios destinatarios, separa los correos de `ALERT_EMAIL_TO` con comas o punto y coma.
3. Crea la variable de repositorio `NOTIFICATION_CHANNEL=gmail`.
   Opcionalmente crea `REPORT_RECIPIENT_NAME` con el nombre que aparecerá en la portada del informe.
4. Ejecuta **Actions → Probar correo → Run workflow**. Esta prueba no consulta SEACE.
5. Ejecuta **Actions → Monitor SEACE → Run workflow** para actualizar los datos.

`GMAIL_APP_PASSWORD` es la contraseña de aplicación de 16 caracteres de Google, no la contraseña normal de Gmail.

## Frecuencia y correos

El monitor consulta SEACE una vez por hora, al minuto 17. Las horas usan `America/Lima` y GitHub puede iniciar el cron con algunos minutos de retraso.

Hay dos correos distintos:

- **Alerta inmediata:** el monitor horario la envía únicamente cuando detecta contratos nuevos, con enlace, entidad, región, vencimiento e ítems.
- **Resumen diario:** se envía a las **7:05 a. m. (America/Lima)** con vigentes, publicaciones del día y próximos vencimientos. Incluye un informe PDF profesional de Radar Andino con resumen ejecutivo, prioridades, regiones, listado completo y enlaces directos a SEACE. Lee los CSV guardados y realiza **0 solicitudes adicionales a SEACE**. También puede probarse manualmente desde **Actions → Resumen diario por correo**.

Si hay varios destinatarios, el sistema envía un mensaje separado a cada uno para no revelar las demás direcciones.

Al incorporar una región por primera vez, sus contratos históricos se registran silenciosamente. A partir de la siguiente ejecución, las nuevas publicaciones sí generan alertas.

## Uso local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:NOTIFICATION_CHANNEL = 'none'
python -m seace_monitor.monitor
```

Configuración regional predeterminada: `SEACE_DEPARTMENTS=8:CUSCO,3:APURIMAC`.

Datos persistentes: `data/contrataciones.csv`, `data/items.csv` y `data/estado.json`. Los CSV se escriben de forma atómica, con UTF-8 BOM y upsert por contrato/ítem.

## Panel web local

Desde la raíz ejecuta `python -m http.server 8000` y abre `http://localhost:8000/web/`. El panel lee los archivos de `data/` y no contiene contrataciones simuladas.

Pruebas del panel: `npm run test:web`.
