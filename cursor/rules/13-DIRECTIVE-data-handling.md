<!-- .cursor/rules/13-DIRECTIVE-data-handling.md -->
# 13 — Directive : Données Historiques & Features

## Schéma Attendu (OHLCV)
`timestamp (UTC), open, high, low, close, volume, symbol`.

## Qualité & Validation
- Vérifier **continuité temporelle**, pas de duplicats, alignement résolutions.
- Tests de **fraîcheur**, bornes, distributions; outliers gérés explicitement.

## Features
- RSI/MA/EMA/ATR, volatilité, retours log, signaux de tendance.
- Pipelines **purs** (pas d’état global), caches avec **TTL**.

## Reproductibilité
- Fixer sources, versions, seeds; journaliser métadonnées (symbol, interval, range).
- **Pas** de fuite d’info inter-split (train/val/test stricts par temps).

---
