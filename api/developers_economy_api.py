"""
Developer Economy API: register, publish agents, versions, dashboard, payouts.

POST /developers/register     - Register as developer
POST /developers/agents       - Publish agent (metadata)
POST /developers/agents/{id}/versions - Add version
GET  /developers/dashboard    - Dashboard (installs, runs, revenue, top agents)
GET  /developers/my-agents      - List agents you published (auth)
GET  /developers/earnings     - Earnings list
GET  /developers/payouts      - Payouts list
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from api.auth_api import get_current_user
from api.deps import require_admin
from database.developer_economy import (
    register_developer,
    get_developer_profile_by_user_id,
    create_published_agent,
    list_published_agents_by_developer,
    get_published_agent,
    add_agent_version,
    get_latest_version,
    get_version,
    get_verification_status,
    set_verification_status,
    get_install_stats,
    get_developer_dashboard_economy,
    get_earnings_for_developer,
    get_payouts_for_developer,
    get_published_agent_by_name,
    update_version_code_location,
)
from agent_runtime.package_validation import validate_agent_zip
from agent_runtime.storage_paths import (
    get_agent_package_path,
    get_agent_package_dir,
    code_location_relative,
)
from database.agent_ratings import get_average_rating_for_agent
from database.agent_production_hardening import (
    get_sandbox_for_agent,
    upsert_sandbox,
    get_trust_metrics,
    get_fraud_signals,
)


router = APIRouter(prefix="/developers", tags=["developer-economy"])


class RegisterDeveloperRequest(BaseModel):
    display_name: str = Field(..., min_length=1, description="Display name")
    company_name: str = Field("", description="Company name")
    website: str = Field("", description="Website URL")
    bio: str = Field("", description="Short bio")


class PublishAgentRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, description="Unique agent name")
    description: str = Field("", description="Agent description")
    category: str = Field("", description="Category")
    price_per_run: float = Field(0.0, ge=0, description="Price per run")
    currency: str = Field("USD", description="Currency code")


class AddVersionRequest(BaseModel):
    version: str = Field(..., min_length=1, description="Semver e.g. 1.0.0")
    code_location: str = Field("", description="e.g. s3://bucket/agent/v1")
    changelog: str = Field("", description="Changelog for this version")


class PublishAgentWithPackageResponse(BaseModel):
    status: str
    agent_id: int
    version: str


def _require_developer(user: dict) -> dict:
    """Return developer profile for current user or raise 403."""
    profile = get_developer_profile_by_user_id(user["id"])
    if not profile:
        raise HTTPException(status_code=403, detail="Register as a developer first: POST /developers/register")
    return profile


@router.post("/register")
def post_register(data: RegisterDeveloperRequest, user: dict = Depends(get_current_user)):
    """Register the current user as a developer. Body: display_name, company_name (optional)."""
    try:
        profile = register_developer(
            user_id=user["id"],
            display_name=data.display_name,
            company_name=data.company_name,
            website=data.website,
            bio=data.bio,
        )
        return {"message": "Registered as developer", "developer": profile}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents")
def post_publish_agent(data: PublishAgentRequest, user: dict = Depends(get_current_user)):
    """Publish an agent (metadata). Agent starts in draft; submit for review to get approved."""
    dev = _require_developer(user)
    try:
        agent = create_published_agent(
            developer_id=dev["developer_id"],
            agent_name=data.agent_name,
            description=data.description,
            category=data.category,
            price_per_run=data.price_per_run,
            currency=data.currency,
        )
        return {"message": "Agent created (draft)", "agent": agent}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-agents")
def get_my_agents(user: dict = Depends(get_current_user)):
    """List agents published by the current developer (authenticated)."""
    dev = _require_developer(user)
    agents = list_published_agents_by_developer(dev["developer_id"])
    out = []
    for a in agents:
        ver = get_verification_status(a["agent_id"])
        stats = get_install_stats(a["agent_id"])
        out.append({
            **a,
            "verification_status": ver["status"] if ver else "draft",
            "installs_total": stats["installs_total"] if stats else 0,
            "runs_total": stats["runs_total"] if stats else 0,
            "revenue_total": stats["revenue_total"] if stats else 0,
        })
    return {"agents": out}


@router.post("/agents/{agent_id}/versions")
def post_agent_version(agent_id: int, data: AddVersionRequest, user: dict = Depends(get_current_user)):
    """Add a new version for an agent. Only latest stable is executed."""
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        version = add_agent_version(
            agent_id=agent_id,
            version=data.version,
            code_location=data.code_location,
            changelog=data.changelog,
        )
        return {"message": "Version added", "version": version}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/upload")
async def post_agent_upload(
    agent_id: int,
    user: dict = Depends(get_current_user),
    file: UploadFile = File(..., description="Zip archive of agent package (agent.yaml, agent.py, optional requirements.txt)"),
    version: str = Form(..., description="Version string e.g. 1.0.0"),
    changelog: str = Form("", description="Changelog for this version"),
):
    """
    Upload agent package zip. Validates agent.yaml and agent.py exist, stores at storage/agents/{agent_id}/{version}.zip,
    creates or updates agent_versions record with code_location.
    """
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    version = (version or "").strip()
    if not version:
        raise HTTPException(status_code=400, detail="version is required")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {e}")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        try:
            tmp.write(contents)
            tmp.flush()
            ok, errors = validate_agent_zip(tmp.name)
            if not ok:
                raise HTTPException(status_code=400, detail="; ".join(errors))
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    storage_path = get_agent_package_path(agent_id, version)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(storage_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save package: {e}")
    code_loc = code_location_relative(agent_id, version)
    existing = get_version(agent_id, version)
    if existing:
        update_version_code_location(agent_id, version, code_loc, changelog)
    else:
        add_agent_version(agent_id=agent_id, version=version, code_location=code_loc, changelog=(changelog or "").strip())
    return {"status": "uploaded", "version": version}


@router.post("/agents/publish", response_model=PublishAgentWithPackageResponse)
async def post_publish_agent_with_package(
    user: dict = Depends(get_current_user),
    file: UploadFile = File(..., description="Zip archive of agent package (agent.yaml, agent.py, optional requirements.txt)"),
    metadata: str = Form(..., description="JSON metadata: agent_name, description, category, price_per_run, currency"),
    version: str = Form(..., description="Version string e.g. 1.0.0"),
    changelog: str = Form("", description="Changelog for this version"),
):
    """
    One-step publish endpoint for developer CLI.
    Creates agent if missing, uploads package, creates version, and submits for review.
    """
    import json

    dev = _require_developer(user)
    try:
        meta = json.loads(metadata)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    agent_name = (meta.get("agent_name") or "").strip()
    if not agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required in metadata")
    description = meta.get("description") or ""
    category = meta.get("category") or ""
    price_per_run = float(meta.get("price_per_run") or 0)
    currency = (meta.get("currency") or "USD").strip() or "USD"

    # Ensure agent exists or create it
    existing = get_published_agent_by_name(agent_name)
    if existing and existing["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=400, detail="Agent name already taken by another developer")
    if existing:
        agent = existing
    else:
        try:
            agent = create_published_agent(
                developer_id=dev["developer_id"],
                agent_name=agent_name,
                description=description,
                category=category,
                price_per_run=price_per_run,
                currency=currency,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    agent_id = agent["agent_id"]

    # Reuse upload validation and storage logic
    version = (version or "").strip()
    if not version:
        raise HTTPException(status_code=400, detail="version is required")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {e}")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        try:
            tmp.write(contents)
            tmp.flush()
            ok, errors = validate_agent_zip(tmp.name)
            if not ok:
                raise HTTPException(status_code=400, detail="; ".join(errors))
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    storage_path = get_agent_package_path(agent_id, version)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(storage_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save package: {e}")
    code_loc = code_location_relative(agent_id, version)
    existing_version = get_version(agent_id, version)
    if existing_version:
        update_version_code_location(agent_id, version, code_loc, changelog)
    else:
        add_agent_version(agent_id=agent_id, version=version, code_location=code_loc, changelog=(changelog or "").strip())
    # Automatically submit for review
    set_verification_status(agent_id, "under_review")
    return PublishAgentWithPackageResponse(status="uploaded", agent_id=agent_id, version=version)


@router.get("/agents/{agent_id}/verification")
def get_agent_verification(agent_id: int, user: dict = Depends(get_current_user)):
    """Get verification status for an agent (draft | under_review | approved | rejected)."""
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    ver = get_verification_status(agent_id)
    return {"agent_id": agent_id, "verification": ver or {"status": "draft"}}


@router.post("/agents/{agent_id}/submit-review")
def post_submit_for_review(agent_id: int, user: dict = Depends(get_current_user)):
    """Submit agent for platform review (draft -> under_review)."""
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    set_verification_status(agent_id, "under_review")
    return {"message": "Submitted for review", "agent_id": agent_id}


@router.get("/dashboard")
def get_dashboard(user: dict = Depends(get_current_user)):
    """Developer dashboard: total installs, runs, revenue, revenue this month, top agents."""
    dev = _require_developer(user)
    data = get_developer_dashboard_economy(dev["developer_id"])
    return data


@router.get("/earnings")
def get_earnings(user: dict = Depends(get_current_user), limit: int = 100):
    """List earnings (developer share per run)."""
    dev = _require_developer(user)
    earnings = get_earnings_for_developer(dev["developer_id"], limit=limit)
    return {"earnings": earnings}


@router.get("/payouts")
def get_payouts(user: dict = Depends(get_current_user), limit: int = 50):
    """List payouts (pending | processing | paid)."""
    dev = _require_developer(user)
    payouts = get_payouts_for_developer(dev["developer_id"], limit=limit)
    return {"payouts": payouts}


@router.get("/profile")
def get_my_profile(user: dict = Depends(get_current_user)):
    """Get current developer profile."""
    profile = get_developer_profile_by_user_id(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Not registered as developer")
    return profile


class SetVerificationRequest(BaseModel):
    status: str = Field(..., description="approved | rejected")


@router.put("/agents/{agent_id}/verification")
def put_agent_verification(
    agent_id: int,
    data: SetVerificationRequest,
    user: dict = Depends(require_admin),
):
    """[Admin] Approve or reject an agent for marketplace listing."""
    if data.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")
    agent = get_published_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    set_verification_status(agent_id, data.status, reviewer_id=user["id"])
    return {"message": f"Agent {agent_id} {data.status}", "agent_id": agent_id}


# --- Sandbox (container limits) ---


class SandboxConfigRequest(BaseModel):
    cpu_limit: float = Field(2.0, ge=0.1, le=8.0, description="CPU limit (cores)")
    memory_limit: int = Field(512, ge=128, le=4096, description="Memory limit (MB)")


@router.get("/agents/{agent_id}/sandbox")
def get_agent_sandbox(agent_id: int, user: dict = Depends(get_current_user)):
    """Get sandbox config (container limits) for an agent."""
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    sandbox = get_sandbox_for_agent(agent_id)
    return sandbox or {"agent_id": agent_id, "cpu_limit": 2.0, "memory_limit": 512, "container_id": ""}


@router.put("/agents/{agent_id}/sandbox")
def put_agent_sandbox(agent_id: int, data: SandboxConfigRequest, user: dict = Depends(get_current_user)):
    """Set sandbox container limits for an agent. Agents run in isolated containers with these limits."""
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    sandbox = upsert_sandbox(agent_id, cpu_limit=data.cpu_limit, memory_limit=data.memory_limit)
    return {"message": "Sandbox config updated", "sandbox": sandbox}


# --- Trust metrics (read-only for developer) ---


@router.get("/agents/{agent_id}/trust")
def get_agent_trust(agent_id: int, user: dict = Depends(get_current_user)):
    """Get trust metrics (success_rate, failure_rate, avg_runtime, trust_score) for an agent."""
    dev = _require_developer(user)
    agent = get_published_agent(agent_id)
    if not agent or agent["developer_id"] != dev["developer_id"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    metrics = get_trust_metrics(agent["agent_name"])
    return metrics or {"agent_name": agent["agent_name"], "trust_score": 1.0, "success_rate": 1.0, "runs_total": 0}


# --- Fraud signals (admin only) ---


@router.get("/agents/{agent_id}/fraud-signals")
def get_agent_fraud_signals(agent_id: int, limit: int = 50, user: dict = Depends(require_admin)):
    """[Admin] List fraud signals for an agent (run_spike, install_spike, bot_activity, etc.)."""
    agent = get_published_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    signals = get_fraud_signals(agent_id, limit=limit)
    return {"agent_id": agent_id, "signals": signals}
