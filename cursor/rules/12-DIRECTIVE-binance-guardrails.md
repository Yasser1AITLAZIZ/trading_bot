<!-- .cursor/rules/12-DIRECTIVE-binance-guardrails.md -->
# 12 — Directive : Garde-fous Binance

## Modes d’Exécution
- **TESTNET / Paper trading par défaut**.
- Passage **LIVE** uniquement via **opt-in explicite** (`BINANCE_MODE=live`) + double confirmation en config.

## Secrets & Réseau
- Clés via env/secret manager; **jamais** en clair ou logs.
- Respect des limites API; retries bornés; horodatage stable.

## Contrôles Avant Ordre
- **Risque** : `risk_per_trade ≤ 1%` (paramétrable), tailles min/max, validation symbol/lot/tick.
- **Idempotence** : `clientOrderId` dérivé (horodatage + hash).
- **Concordance** : vérifier solde disponible, statut marché, latence.

## Journalisation & Alertes
- Log requêtes/réponses SANS clés; codes d’erreurs; latences; échecs.
- Alerte si : slippage anormal, latence > seuil, nombre d’échecs, déviation prix.

## Post-Trade
- Reconciliation ordres/positions, PnL calculé, anomalies remontées.
- **Kill-switch** (désactivation live si seuil de perte dépassé).

---
