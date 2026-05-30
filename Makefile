# Agent Cloud — developer automation (POSIX Make; use Git Bash on Windows).
.PHONY: help inventory openapi-routes schema-audit intelligence migration-intel doctor readiness wave1-infra clean-stale user-research

help:
	@echo "Targets:"
	@echo "  make doctor         - Local dev health preflight (py -3.11 scripts/dev_doctor.py)"
	@echo "  make readiness      - Alpha tester readiness smoke"
	@echo "  make wave1-infra    - Wave 1 schema + API regression (scripts/wave1_infra_check.py)"
	@echo "  make clean-stale    - Kill hung dashboard Node processes"
	@echo "  make user-research  - First 5 users PMF scorecard rollup"
	@echo "  make inventory       - Tree inventory (excludes .venv, node_modules, caches)"
	@echo "  make openapi-routes  - Markdown route matrix from api.main:app"
	@echo "  make schema-audit    - Heuristic Alembic vs models vs runtime DDL report"
	@echo "  make intelligence    - Run all three; writes under docs/generated/"
	@echo "  make migration-intel - Phase 1–2 graphs + classification under docs/migration/"

inventory:
	python scripts/repo_inventory.py --out docs/generated/repo_inventory.txt

openapi-routes:
	python scripts/openapi_route_matrix.py --out docs/generated/route_matrix.md

schema-audit:
	python scripts/schema_drift_audit.py --out docs/generated/schema_drift_audit.md

intelligence: inventory openapi-routes schema-audit
	@echo "Done. See docs/generated/"

migration-intel:
	python scripts/build_migration_intel.py
	@echo "Done. See docs/migration/"

doctor:
	py -3.11 scripts/dev_doctor.py --deep

readiness:
	py -3.11 scripts/dev_doctor.py --readiness

wave1-infra:
	py -3.11 scripts/wave1_infra_check.py

clean-stale:
	py -3.11 scripts/dev_doctor.py --clean

user-research:
	py -3.11 scripts/user_research_report.py --days 30
