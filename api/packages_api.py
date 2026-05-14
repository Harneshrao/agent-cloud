"""
Automation packages API: list, get, install into project, marketplace.

Endpoints:
  GET  /packages              - List all available packages
  GET  /packages/marketplace   - Marketplace view (most installed, recent, featured; for now list_packages)
  GET  /packages/{name}        - Get package metadata
  POST /packages/{name}/install - Install package into project (body: project_id)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth_api import get_current_user
from database.package_stats import get_all_package_stats
from database.projects import user_can_access_project
from engine.package_installer import install_package
from registry.package_registry import package_registry


router = APIRouter(prefix="/packages", tags=["packages"])


class InstallPackageRequest(BaseModel):
    """Request body for POST /packages/{name}/install."""

    project_id: int = Field(..., description="Project to install the package into")


# ---------- Marketplace before /{name} ----------


@router.get("/trending")
def packages_trending(limit: int = Query(20, ge=1, le=100)):
    """Return trending packages ranked by install count and recent installs."""
    try:
        stats = get_all_package_stats()
        packages = package_registry.list_packages()
        by_name = {p.get("name") or p.get("package_name"): p for p in packages if p.get("name") or p.get("package_name")}
        out = []
        for s in stats:
            name = s["package_name"]
            pkg = by_name.get(name)
            out.append({
                "package_name": name,
                "install_count": s["install_count"],
                "last_installed_at": s["last_installed_at"],
                **(pkg or {}),
            })
            if len(out) >= limit:
                break
        while len(out) < limit:
            added = False
            for p in packages:
                if len(out) >= limit:
                    break
                name = p.get("name") or p.get("package_name")
                if name and not any(x.get("package_name") == name for x in out):
                    out.append({
                        "package_name": name,
                        "install_count": 0,
                        "last_installed_at": None,
                        **p,
                    })
                    added = True
            if not added:
                break
        return {"packages": out[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace")
def packages_marketplace():
    """Marketplace view: for now returns all available packages (list_packages)."""
    packages = package_registry.list_packages()
    return {"packages": packages}


@router.get("")
def list_packages():
    """Return all available automation packages."""
    packages = package_registry.list_packages()
    return {"packages": packages}


@router.get("/{name}")
def get_package(name: str):
    """Return metadata for one package by name."""
    pkg = package_registry.get_package(name)
    if pkg is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return pkg


@router.post("/{name}/install")
def install_package_endpoint(
    name: str,
    body: InstallPackageRequest,
    user: dict = Depends(get_current_user),
):
    """
    Install an automation package into a project.
    Requires auth; validates user_can_access_project(project_id, user_id).
    """
    project_id = body.project_id
    if not user_can_access_project(project_id, user["id"]):
        raise HTTPException(status_code=403, detail="Access denied to this project")
    try:
        result = install_package(
            project_id=project_id,
            package_name=name,
            author_user_id=user["id"],
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
