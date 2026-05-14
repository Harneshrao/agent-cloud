"""
Agent Cloud API — multi-agent marketplace, tasks, workflows, and platform routes.

Landing page analyzer routes have been removed.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.body_size_limit import BodySizeLimitMiddleware
from api.middleware.rate_limit import AuthRateLimitMiddleware
from api.middleware.token_bucket_rate_limit import TokenBucketRateLimitMiddleware
from api.middleware.trace_context import TraceContextMiddleware
from api.migration_check import assert_migrations_applied
from api.rate_limit import RateLimitMiddleware

# --- Core platform & auth ---
from api.auth_api import router as auth_router

# --- Marketplace & agents (order: store/run before ecosystem /top, /trending) ---
from api.agent_store_api import agent_run_alias_router, router as agent_store_router
from api.agent_marketplace_api import developers_router, router as agent_ecosystem_router
from api.marketplace_api import router as marketplace_browse_router

# --- Installations & dashboard (product paths) ---
from api.agents_installations_product_api import router as agents_installations_product_router
from api.agent_installations_api import dashboard_router, router_schedules as installations_schedules_router

# --- Developer economy (publish, versions, payouts) ---
from api.developers_economy_api import router as developers_economy_router

# --- Workflows, demo, war room, scheduler, system ---
from api.workflow_api import router as workflow_router
from api.demo_api import router as demo_router
from api.war_room_api import router as war_room_router
from api.scheduler_api import router as legacy_scheduler_router
from api.task_scheduler_api import router as task_scheduler_router
from api.system_api import router as system_router

# --- API keys, events, webhooks, projects, teams, billing ---
from api.api_keys_api import router as api_keys_router
from api.event_api import router as event_router
from api.webhook_api import router as webhook_router
from api.projects_api import router as projects_router
from api.teams_api import router as teams_router
from api.plans_api import router as plans_router
from api.usage_api import router as usage_router

# --- Agents v2, templates, packages, simulation, autonomous ---
from api.agents_v2_api import router as agents_v2_router
from api.templates_api import router as templates_router
from api.packages_api import router as packages_router
from api.simulation_api import router as simulation_router
from api.autonomous_policies_api import router as autonomous_router

# --- Agent instances & marketplace extras ---
from api.agent_instances_api import router as agent_instances_router
from api.agents_api import router as agents_registry_router


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    from agent_runtime.loader import discover_agents

    discover_agents()
    assert_migrations_applied()
    logging.getLogger("uvicorn.error").info(
        "PostgreSQL OK: DATABASE_URL loaded from environment; migration check passed."
    )
    yield


app = FastAPI(title="Agent Cloud API", version="2.0.0", lifespan=_lifespan)

app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(AuthRateLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
_cors = _cors_allow_origins()
_cors_creds = os.environ.get("CORS_ALLOW_CREDENTIALS", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=_cors_creds,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trace + optional token-bucket (last registered = outermost; runs first on request)
app.add_middleware(TokenBucketRateLimitMiddleware)
app.add_middleware(TraceContextMiddleware)

# Auth (Google OAuth lives in api/auth_google.py — enable when DB helpers are wired)
app.include_router(auth_router)

# Marketplace discovery & run (static paths first)
app.include_router(agent_store_router)
app.include_router(agent_run_alias_router)
app.include_router(agent_ecosystem_router)
app.include_router(developers_router)

# Browse UI API
app.include_router(marketplace_browse_router)

# Product: /agents/installations, /dashboard
app.include_router(agents_installations_product_router)
app.include_router(dashboard_router)
app.include_router(installations_schedules_router)

# Developer economy
app.include_router(developers_economy_router)

# Tasks & workflows
app.include_router(workflow_router)
app.include_router(demo_router)
app.include_router(war_room_router)
app.include_router(legacy_scheduler_router)
app.include_router(task_scheduler_router)

# Platform
app.include_router(system_router)
app.include_router(api_keys_router)
app.include_router(event_router)
app.include_router(webhook_router)
app.include_router(projects_router)
app.include_router(teams_router)
app.include_router(plans_router)
app.include_router(usage_router)

# Agents v2, templates, packages
app.include_router(agents_v2_router)
app.include_router(templates_router)
app.include_router(packages_router)
app.include_router(simulation_router)
app.include_router(autonomous_router)

# Registry & instances
app.include_router(agents_registry_router)
app.include_router(agent_instances_router)


@app.get("/")
def root():
    return {"message": "Agent Cloud API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}
