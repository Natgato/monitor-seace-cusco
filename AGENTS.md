# Repository Guidelines

## Project Structure & Module Organization

`seace_monitor/` contains the Python monitor, SEACE client, persistence, notifications, email templates, and PDF reporting. Persisted contracts, items, and monitor state live in `data/`; treat these as generated operational data. The browser dashboard is under `web/` and follows clean architecture: `domain/`, `application/`, `infrastructure/`, and `presentation/`, composed by `web/src/main.js`. Python tests are in `tests/`; JavaScript domain tests are in `tests-web/`. GitHub Actions workflows live in `.github/workflows/`, and generated report samples belong in `output/pdf/`. See `ARCHITECTURE.md` before changing layer boundaries.

## Build, Test, and Development Commands

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
npm run test:web
$env:NOTIFICATION_CHANNEL='none'; python -m seace_monitor.monitor
python -m http.server 8000
```

The first three commands prepare Python. The next two run all Python and web tests. Use `NOTIFICATION_CHANNEL=none` for safe local monitor runs without sending messages. The HTTP server exposes the dashboard at `http://localhost:8000/web/`. Run `python -m seace_monitor.daily_digest` to exercise daily report generation; keep notifications disabled unless intentionally testing email.

## Coding Style & Naming Conventions

Use four-space indentation, type hints, `snake_case` functions, and `PascalCase` classes in Python. Use two-space indentation, ES modules, `camelCase` identifiers, and kebab-case JavaScript filenames. Keep domain rules pure: browser domain/application code must not access DOM, CSV, or `fetch` directly. Prefer small functions, explicit exceptions, UTF-8 text, and Lima-aware timestamps. No formatter is enforced, so match adjacent code and run `git diff --check`.

## Testing Guidelines

Python uses `unittest`; name files `test_*.py` and methods `test_*`. Web tests use Node’s built-in test runner. Add regression tests for parsing, date handling, deduplication, notification privacy, and PDF generation. Tests must not contact SEACE, Gmail, or Telegram; use fixtures and mocks.

## Commit & Pull Request Guidelines

Use concise conventional subjects such as `feat: attach PDF report` or `fix: preserve contract deadline`. Reserve `chore: actualizar monitor SEACE [skip ci]` for automated data refreshes. Pull requests should explain behavior changes, list verification commands, link relevant issues, and include screenshots for dashboard or PDF layout changes. Keep generated-data-only changes separate from application code.

## Security & Configuration

Copy `.env.example` locally, but never commit `.env`, Gmail app passwords, recipient addresses, or Telegram tokens. Store production credentials as GitHub Actions secrets. Avoid logging secret values or complete SMTP configuration.
