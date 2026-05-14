# Agent Cloud — developer automation (POSIX Make; use Git Bash on Windows).
.PHONY: help inventory openapi-routes schema-audit intelligence

help:
	@echo "Targets:"
	@echo "  make inventory       - Tree inventory (excludes .venv, node_modules, caches)"
	@echo "  make openapi-routes  - Markdown route matrix from api.main:app"
	@echo "  make schema-audit    - Heuristic Alembic vs models vs runtime DDL report"
	@echo "  make intelligence    - Run all three; writes under docs/generated/"

inventory:
	python scripts/repo_inventory.py --out docs/generated/repo_inventory.txt

openapi-routes:
	python scripts/openapi_route_matrix.py --out docs/generated/route_matrix.md

schema-audit:
	python scripts/schema_drift_audit.py --out docs/generated/schema_drift_audit.md

intelligence: inventory openapi-routes schema-audit
	@echo "Done. See docs/generated/"
