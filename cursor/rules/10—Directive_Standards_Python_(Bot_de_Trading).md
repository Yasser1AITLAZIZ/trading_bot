Version & Structure

Python ≥ 3.9.11, layout src/ + pyproject.toml.

Modules :

src/
  core/        # types, settings (pydantic-settings), utils, logging (structlog)
  data/        # ingestion, validation, features (RSI/MA/ATR), caches
  strategy/    # interfaces + implémentations (plug-ins)
  llm/         # clients LLM (OpenAI/Claude/Gemini) via abstraction commune
  execution/   # brokers (Binance), risk, order router (paper/live)
  app.py       # orchestrateur CLI (typer ou argparse)
tests/         # unit, integration, golden (LLM), e2e papier

Qualité & Sécurité

Typing strict (mypy --strict), docstrings Google/Numpy, ruff, black, isort.

Logs structurés (latences, IDs corrélés).

Exceptions métier (OrderRejected, DataStale, RiskLimitExceeded) + retries exponentiels bornés.

Config & Secrets

Pydantic Settings, profils (DEV/TEST/LIVE), .env ignoré par git.

Jamais de clés en clair. Mock pour tests.

Orchestration

Pipeline pur (pas d’état caché) ; fonctions idempotentes.

Timezones UTC, horodatage monotone, tolérance aux trous de données.