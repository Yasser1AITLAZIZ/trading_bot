<!-- .cursor/rules/11-DIRECTIVE-genai-strategy.md -->
# 11 — Directive : Orchestration GenAI & Stratégies

## Abstraction LLM
- Interface `LLMClient` : `generate()`, `score()`, `structured()`.
- Backends interchangeables (OpenAI, Claude, Gemini) via **factory** + config.

## Prompts & Déterminisme
- Prompts **délimités** (```), rôle clair, contraintes, format de sortie (JSON/PNydantic).
- **Température basse** par défaut pour la stabilité; few-shots versionnés (goldens).
- **Validation** du format (pydantic), rejet si schema invalide.

## Stratégies Plug-in
- `Strategy` (Protocol) → `decide(signals: Signals) -> Decision`.
- `StrategySpec` : objectifs, contraintes (max drawdown/SL/TP), métriques.
- **LLM-as-judge** (optionnel) pour scorer une proposition de trade avec explication concise (≤ 100 tokens).

## Coûts, Sécurité, Fallback
- Timeouts, taux max tokens, quotas par provider, circuit-breaker.
- **Fallback** ordonné : provider A → B → mode **rule-based minimal** si panne.
- Journaliser inputs/outputs LLM (masquage données sensibles).

## Traçabilité
- Log des décisions : features clés, stratégie, justification courte, hash de prompt/templates.

---
