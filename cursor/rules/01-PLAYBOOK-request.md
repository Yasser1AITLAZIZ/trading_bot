<!-- .cursor/rules/01-PLAYBOOK-request.md -->
# 01 — Playbook : Demande de feature / refacto

> Remplacer ce paragraphe par **la demande métier** et **la valeur attendue**.

## P0 — Recon
- Scanner repo, deps, configs, scripts, CI, tests.
- Produire un **digest ≤ 150 lignes** (faits, liens vers fichiers).

## P1 — Plan & Stratégie
- Reformuler l’objectif + **critères de réussite** (testables).
- Lister **surface d’impact** (fichiers, workflows).
- Proposer stratégie alignée à l’existant + **rollback**.

## P2 — Implémentation
- Commits **petits et explicites**.
- Commandes reproductibles avec timeouts.
- Pas de secrets en clair; configuration via `.env`/pydantic.

## P3 — Vérification
- `ruff`, `black --check`, `isort --check`, `mypy --strict`, `pytest -q`.
- Smoke test du flux critique.

## P4 — Rapport
- Changements, preuves (logs/checks/tests), impacts.
- Statut `✅ / ⚠️ / ⛔` + prochaines étapes.

---
