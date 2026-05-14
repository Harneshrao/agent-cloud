"""
Developer Economy: developer profiles, published agents, versions, reviews,
install stats, earnings, and payouts.

Tables:
  developer_profiles   - developer_id (PK), user_id, display_name, company_name, website, bio, verified, created_at
  published_agents     - agent_id (PK), developer_id, agent_name, description, category, price_per_run, currency, status, created_at
  agent_versions       - version_id (PK), agent_id, version, code_location, changelog, created_at
  agent_reviews        - review_id (PK), agent_id, reviewer_id, rating, comment, created_at (platform verification)
  agent_verification   - agent_id, status (draft|under_review|approved|rejected), reviewed_at, reviewer_id
  agent_install_stats  - agent_id, installs_total, runs_total, revenue_total, last_run_at
  developer_earnings  - earning_id (PK), developer_id, agent_id, run_id, amount, currency, created_at
  developer_payouts   - payout_id (PK), developer_id, amount, currency, status, created_at, paid_at
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db

# Revenue share: 80% developer, 20% platform
DEVELOPER_SHARE_RATIO = 0.80
PLATFORM_FEE_RATIO = 0.20


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def register_developer(user_id: int, display_name: str, company_name: str = "", website: str = "", bio: str = "") -> Dict[str, Any]:
    """Register user as developer. Creates developer_profile. Returns profile dict."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT developer_id FROM developer_profiles WHERE user_id = ?", (user_id,))
    if cur.fetchone():
        raise ValueError("User is already registered as a developer")
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO developer_profiles (user_id, display_name, company_name, website, bio, verified, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
        """,
        (user_id, (display_name or "").strip() or "Developer", (company_name or "").strip(), (website or "").strip(), (bio or "").strip(), now),
    )
    conn.commit()
    developer_id = int(cur.lastrowid)
    # Ensure balance account exists (reuse existing developer_accounts)
    try:
        from database.developer_accounts import get_or_create
        get_or_create(user_id)
    except Exception:
        pass
    return get_developer_profile_by_id(developer_id)


def get_developer_profile_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT developer_id, user_id, display_name, company_name, website, bio, verified, created_at FROM developer_profiles WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    return _row_to_profile(row) if row else None


def get_developer_profile_by_id(developer_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT developer_id, user_id, display_name, company_name, website, bio, verified, created_at FROM developer_profiles WHERE developer_id = ?",
        (developer_id,),
    )
    row = cur.fetchone()
    return _row_to_profile(row) if row else None


def _row_to_profile(row) -> Dict[str, Any]:
    return {
        "developer_id": row["developer_id"],
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "company_name": row["company_name"] or "",
        "website": row["website"] or "",
        "bio": row["bio"] or "",
        "verified": bool(row["verified"]),
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
    }


# --- Published agents (Step 2) ---


def create_published_agent(
    developer_id: int,
    agent_name: str,
    description: str = "",
    category: str = "",
    price_per_run: float = 0.0,
    currency: str = "USD",
) -> Dict[str, Any]:
    """Create a new published agent (status draft). agent_name must be unique."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    agent_name = (agent_name or "").strip().lower().replace(" ", "_")
    if not agent_name:
        raise ValueError("agent_name required")
    now = datetime.utcnow()
    try:
        cur.execute(
            """
            INSERT INTO published_agents (developer_id, agent_name, description, category, price_per_run, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)
            """,
            (developer_id, agent_name, (description or "").strip(), (category or "").strip(), max(0, float(price_per_run)), (currency or "USD").strip() or "USD", now),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        if "UNIQUE" in str(e) or "unique" in str(e).lower():
            raise ValueError(f"Agent name '{agent_name}' is already taken") from e
        raise
    agent_id = int(cur.lastrowid)
    # Create verification row (draft)
    cur.execute(
        """
        INSERT INTO agent_verification (agent_id, status) VALUES (?, 'draft')
        ON CONFLICT (agent_id) DO NOTHING
        """,
        (agent_id,),
    )
    conn.commit()
    # Create install_stats row
    cur.execute(
        """
        INSERT INTO agent_install_stats (agent_id, installs_total, runs_total, revenue_total)
        VALUES (?, 0, 0, 0)
        ON CONFLICT (agent_id) DO NOTHING
        """,
        (agent_id,),
    )
    conn.commit()
    # Create default sandbox (container limits) for production hardening
    try:
        from database.agent_production_hardening import upsert_sandbox
        upsert_sandbox(agent_id, container_id="", cpu_limit=2.0, memory_limit=512)
    except Exception:
        pass
    return get_published_agent(agent_id)


def get_published_agent(agent_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_id, developer_id, agent_name, description, category, price_per_run, currency, status, created_at FROM published_agents WHERE agent_id = ?",
        (agent_id,),
    )
    row = cur.fetchone()
    return _row_to_published_agent(row) if row else None


def get_published_agent_by_name(agent_name: str) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_id, developer_id, agent_name, description, category, price_per_run, currency, status, created_at FROM published_agents WHERE agent_name = ?",
        (agent_name.strip().lower(),),
    )
    row = cur.fetchone()
    return _row_to_published_agent(row) if row else None


def list_published_agents_by_developer(developer_id: int) -> List[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_id, developer_id, agent_name, description, category, price_per_run, currency, status, created_at FROM published_agents WHERE developer_id = ? ORDER BY created_at DESC",
        (developer_id,),
    )
    return [_row_to_published_agent(r) for r in cur.fetchall()]


def list_approved_agents_for_marketplace() -> List[Dict[str, Any]]:
    """Agents with verification status = approved (and published_agents.status = published)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT p.agent_id, p.developer_id, p.agent_name, p.description, p.category, p.price_per_run, p.currency, p.status, p.created_at
        FROM published_agents p
        JOIN agent_verification v ON v.agent_id = p.agent_id
        WHERE v.status = 'approved' AND p.status IN ('published', 'approved')
        ORDER BY p.created_at DESC
        """
    )
    return [_row_to_published_agent(r) for r in cur.fetchall()]


def _row_to_published_agent(row) -> Dict[str, Any]:
    return {
        "agent_id": row["agent_id"],
        "developer_id": row["developer_id"],
        "agent_name": row["agent_name"],
        "description": row["description"] or "",
        "category": row["category"] or "",
        "price_per_run": float(row["price_per_run"]) if row["price_per_run"] is not None else 0.0,
        "currency": row["currency"] or "USD",
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
    }


# --- Agent versions (Step 3) ---


def add_agent_version(agent_id: int, version: str, code_location: str = "", changelog: str = "") -> Dict[str, Any]:
    """Add a new version for an agent. Only latest stable is used at runtime."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_versions (agent_id, version, code_location, changelog, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (agent_id, (version or "1.0.0").strip(), (code_location or "").strip(), (changelog or "").strip(), now),
    )
    conn.commit()
    version_id = int(cur.lastrowid)
    return {
        "version_id": version_id,
        "agent_id": agent_id,
        "version": (version or "1.0.0").strip(),
        "code_location": (code_location or "").strip(),
        "changelog": (changelog or "").strip(),
        "created_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
    }


def get_latest_version(agent_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT version_id, agent_id, version, code_location, changelog, created_at FROM agent_versions WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
        (agent_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "version_id": row["version_id"],
        "agent_id": row["agent_id"],
        "version": row["version"],
        "code_location": row["code_location"] or "",
        "changelog": row["changelog"] or "",
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
    }


def get_version(agent_id: int, version: str) -> Optional[Dict[str, Any]]:
    """Return a specific version row by agent_id and version string."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT version_id, agent_id, version, code_location, changelog, created_at FROM agent_versions WHERE agent_id = ? AND version = ?",
        (agent_id, version.strip()),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "version_id": row["version_id"],
        "agent_id": row["agent_id"],
        "version": row["version"],
        "code_location": row["code_location"] or "",
        "changelog": row["changelog"] or "",
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
    }


def update_version_code_location(agent_id: int, version: str, code_location: str, changelog: str = "") -> bool:
    """Update code_location (and optionally changelog) for an existing version. Returns True if updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_versions SET code_location = ?, changelog = ? WHERE agent_id = ? AND version = ?",
        (code_location.strip(), (changelog or "").strip(), agent_id, version.strip()),
    )
    conn.commit()
    return cur.rowcount > 0


# --- Agent verification (Step 4) ---


def get_verification_status(agent_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_id, status, reviewed_at, reviewer_id FROM agent_verification WHERE agent_id = ?",
        (agent_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "agent_id": row["agent_id"],
        "status": row["status"],
        "reviewed_at": row["reviewed_at"],
        "reviewer_id": row.get("reviewer_id"),
    }


def set_verification_status(agent_id: int, status: str, reviewer_id: Optional[int] = None) -> None:
    """status: draft | under_review | approved | rejected"""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    reviewed_at = now if status in ("approved", "rejected") else None
    cur.execute(
        """
        INSERT INTO agent_verification (agent_id, status, reviewed_at, reviewer_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(agent_id) DO UPDATE SET status = excluded.status, reviewed_at = excluded.reviewed_at, reviewer_id = excluded.reviewer_id
        """,
        (agent_id, status, reviewed_at, reviewer_id),
    )
    conn.commit()
    if status == "approved":
        cur.execute("UPDATE published_agents SET status = 'published' WHERE agent_id = ?", (agent_id,))
        conn.commit()


def add_agent_review(agent_id: int, reviewer_id: int, rating: int, comment: str = "") -> Dict[str, Any]:
    """Platform reviewer adds a review (internal verification feedback)."""
    _ensure_schema()
    if not (1 <= rating <= 5):
        raise ValueError("rating must be 1-5")
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO agent_reviews (agent_id, reviewer_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
        (agent_id, reviewer_id, rating, (comment or "").strip(), now),
    )
    conn.commit()
    return {"review_id": int(cur.lastrowid), "agent_id": agent_id, "rating": rating, "comment": comment, "created_at": now.isoformat()}


# --- Install stats (Step 5) ---


def get_install_stats(agent_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_id, installs_total, runs_total, revenue_total, last_run_at FROM agent_install_stats WHERE agent_id = ?",
        (agent_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "agent_id": row["agent_id"],
        "installs_total": int(row["installs_total"] or 0),
        "runs_total": int(row["runs_total"] or 0),
        "revenue_total": float(row["revenue_total"] or 0),
        "last_run_at": row["last_run_at"],
    }


def record_install_for_agent(agent_id: int) -> None:
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_install_stats SET installs_total = installs_total + 1 WHERE agent_id = ?",
        (agent_id,),
    )
    if cur.rowcount == 0:
        cur.execute(
            "INSERT INTO agent_install_stats (agent_id, installs_total, runs_total, revenue_total) VALUES (?, 1, 0, 0)",
            (agent_id,),
        )
    conn.commit()


def record_run_and_revenue(agent_id: int, revenue_this_run: float) -> None:
    """Increment runs_total, revenue_total, set last_run_at."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        UPDATE agent_install_stats
        SET runs_total = runs_total + 1, revenue_total = revenue_total + ?, last_run_at = ?
        WHERE agent_id = ?
        """,
        (revenue_this_run, now, agent_id),
    )
    if cur.rowcount == 0:
        cur.execute(
            "INSERT INTO agent_install_stats (agent_id, installs_total, runs_total, revenue_total, last_run_at) VALUES (?, 0, 1, ?, ?)",
            (agent_id, revenue_this_run, now),
        )
    conn.commit()


# --- Developer earnings (Step 6) ---


def record_earning(developer_id: int, agent_id: int, run_id: Optional[int], amount: float, currency: str = "USD") -> int:
    """Record developer share (80%) for a run. Also credits developer balance."""
    _ensure_schema()
    if amount <= 0:
        return 0
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO developer_earnings (developer_id, agent_id, run_id, amount, currency, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (developer_id, agent_id, run_id, amount, currency, now),
    )
    earning_id = int(cur.lastrowid)
    conn.commit()
    # Credit developer balance (developer_accounts uses user_id; we have developer_id)
    cur.execute("SELECT user_id FROM developer_profiles WHERE developer_id = ?", (developer_id,))
    row = cur.fetchone()
    if row:
        try:
            from database.developer_accounts import add_balance
            add_balance(int(row["user_id"]), amount)
        except Exception:
            pass
    return earning_id


def get_earnings_for_developer(developer_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT e.earning_id, e.developer_id, e.agent_id, e.run_id, e.amount, e.currency, e.created_at, p.agent_name
        FROM developer_earnings e
        JOIN published_agents p ON p.agent_id = e.agent_id
        WHERE e.developer_id = ?
        ORDER BY e.created_at DESC
        LIMIT ?
        """,
        (developer_id, limit),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "earning_id": r["earning_id"],
            "agent_id": r["agent_id"],
            "agent_name": r["agent_name"],
            "run_id": r["run_id"],
            "amount": float(r["amount"]),
            "currency": r["currency"],
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        })
    return out


# --- Payouts (Step 7) ---


def create_payout(developer_id: int, amount: float, currency: str = "USD") -> int:
    """Create a pending payout. Caller should deduct from balance elsewhere."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO developer_payouts (developer_id, amount, currency, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (developer_id, amount, currency, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_payout_status(payout_id: int, status: str, paid_at: Optional[datetime] = None) -> None:
    """status: pending | processing | paid"""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE developer_payouts SET status = ?, paid_at = ? WHERE payout_id = ?",
        (status, paid_at or datetime.utcnow() if status == "paid" else None, payout_id),
    )
    conn.commit()


def get_payouts_for_developer(developer_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT payout_id, developer_id, amount, currency, status, created_at, paid_at FROM developer_payouts WHERE developer_id = ? ORDER BY created_at DESC LIMIT ?",
        (developer_id, limit),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "payout_id": r["payout_id"],
            "amount": float(r["amount"]),
            "currency": r["currency"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            "paid_at": r["paid_at"].isoformat() if r.get("paid_at") and hasattr(r["paid_at"], "isoformat") else (str(r["paid_at"]) if r.get("paid_at") else None),
        })
    return out


# --- Developer dashboard (Step 8) ---


def get_developer_dashboard_economy(developer_id: int) -> Dict[str, Any]:
    """Total installs, runs, revenue, revenue this month, top agents."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    # Resolve user_id for balance
    cur.execute("SELECT user_id FROM developer_profiles WHERE developer_id = ?", (developer_id,))
    row = cur.fetchone()
    user_id = row["user_id"] if row else None
    balance = 0.0
    if user_id:
        try:
            from database.developer_accounts import get_balance
            balance = get_balance(user_id)
        except Exception:
            pass

    cur.execute(
        """
        SELECT
            COALESCE(SUM(s.installs_total), 0) AS total_installs,
            COALESCE(SUM(s.runs_total), 0) AS total_runs,
            COALESCE(SUM(s.revenue_total), 0) AS total_revenue
        FROM published_agents p
        JOIN agent_install_stats s ON s.agent_id = p.agent_id
        WHERE p.developer_id = ?
        """,
        (developer_id,),
    )
    row = cur.fetchone()
    total_installs = int(row["total_installs"] or 0) if row else 0
    total_runs = int(row["total_runs"] or 0) if row else 0
    total_revenue = float(row["total_revenue"] or 0) if row else 0.0

    # Revenue this month
    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS revenue_month
        FROM developer_earnings
        WHERE developer_id = ? AND date(created_at) >= date('now', 'start of month')
        """,
        (developer_id,),
    )
    row = cur.fetchone()
    revenue_this_month = float(row["revenue_month"] or 0) if row else 0.0

    # Top agents by revenue
    cur.execute(
        """
        SELECT p.agent_id, p.agent_name, s.installs_total, s.runs_total, s.revenue_total
        FROM published_agents p
        JOIN agent_install_stats s ON s.agent_id = p.agent_id
        WHERE p.developer_id = ?
        ORDER BY s.revenue_total DESC
        LIMIT 10
        """,
        (developer_id,),
    )
    top_agents = []
    for r in cur.fetchall():
        top_agents.append({
            "agent_id": r["agent_id"],
            "agent_name": r["agent_name"],
            "installs_total": int(r["installs_total"] or 0),
            "runs_total": int(r["runs_total"] or 0),
            "revenue_total": float(r["revenue_total"] or 0),
        })

    return {
        "total_installs": total_installs,
        "total_runs": total_runs,
        "total_revenue": round(total_revenue, 2),
        "revenue_this_month": round(revenue_this_month, 2),
        "balance": round(balance, 2),
        "top_agents": top_agents,
    }
