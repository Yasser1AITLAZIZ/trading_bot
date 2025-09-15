<!-- .cursor/rules/14-DIRECTIVE-testing-ci.md -->
# 14 — Directive : Tests, Qualité & CI

## Tests
- **Unit** : stratégies, signaux, risk-checks.
- **Integration** : clients LLM (mocks), broker Binance (sandbox/mocks).
- **Golden** : sorties LLM stables sur prompts versionnés.
- **E2E (paper)** : du chargement data → décision → ordre simulé.

## Seuils
- Couverture **≥ 85%** (exclure glue difficile si justifié).
- `mypy --strict` sans erreurs; `ruff`, `black`, `isort` propres.

## Outils
- `pytest -q`, `hypothesis` pour tests par propriétés.
- `bandit`, `pip-audit`/`safety` pour sécurité deps.

## CI
- Job rapide (lint/type/test unit).
- Job complet (golden + e2e papier).
- Artefacts : rapports couverture + logs formatés.

---
