# Arquitectura

El proyecto separa el proceso automático de recolección y la aplicación web. Ambos se comunican únicamente mediante archivos persistentes en `data/`.

## Flujo de datos

```text
SEACE API → monitor Python → data/*.csv + estado.json → panel web
```

Telegram es un adaptador opcional. Su ausencia no impide consultar SEACE ni actualizar los archivos.

## Capas del panel web

- `web/src/domain`: entidades y reglas puras (`Contract`, `ContractItem`, `MonitorState`). No conoce HTML, CSV ni `fetch`.
- `web/src/application`: casos de uso para cargar el tablero, filtrar, obtener detalle y responder consultas locales.
- `web/src/infrastructure`: lectura de CSV/JSON y adaptación a entidades del dominio.
- `web/src/presentation`: controlador y vista DOM. No consulta archivos directamente ni contiene reglas del negocio.
- `web/src/main.js`: composición de dependencias.

Las dependencias apuntan hacia adentro: presentación e infraestructura dependen de aplicación/dominio; el dominio no depende de ninguna capa externa.

## Asistente

El asistente trabaja localmente sobre los datos recopilados. No es todavía un modelo generativo y no envía información a servicios externos. Una IA real puede añadirse después como un nuevo adaptador sin cambiar la vista ni las entidades.

## Ejecución del panel

El navegador no permite leer CSV mediante `file://`. Sirve la raíz del repositorio:

```powershell
python -m http.server 8000
```

Luego abre `http://localhost:8000/web/`.
