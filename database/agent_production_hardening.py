"""
Production hardening: sandboxing, trust metrics, fraud signals.

Tables:
  agent_execution_sandbox - sandbox_id, agent_id, container_id, cpu_limit, memory_limit, created_at
  agent_trust_metrics     - agent_name (or agent_id), success_rate, failure_rate, avg_runtime, trust_score, last_updated
  agent_fraud_signals     - signal_id, agent_id, signal_type, confidence, created_at
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db

# Default container limits when not set (cpus as float, memory_mb)
DEFAULT_CPU_LIMIT = 2.0
DEFAULT_MEMORY_LIMIT_MB = 512


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def get_sandbox_for_agent(agent_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT sandbox_id, agent_id, container_id, cpu_limit, memory_limit, created_at FROM agent_execution_sandbox WHERE agent_id = ?",
        (agent_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "sandbox_id": row["sandbox_id"],
        "agent_id": row["agent_id"],
        "container_id": row["container_id"] or "",
        "cpu_limit": float(row["cpu_limit"]) if row["cpu_limit"] is not None else DEFAULT_CPU_LIMIT,
        "memory_limit": int(row["memory_limit"]) if row["memory_limit"] is not None else DEFAULT_MEMORY_LIMIT_MB,
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
    }


def upsert_sandbox(
    agent_id: int,
    container_id: str = "",
    cpu_limit: float = DEFAULT_CPU_LIMIT,
    memory_limit: int = DEFAULT_MEMORY_LIMIT_MB,
) -> Dict[str, Any]:
    """Create or update sandbox config for an agent. Containers must run with these limits."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_execution_sandbox (agent_id, container_id, cpu_limit, memory_limit, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(agent_id) DO UPDATE SET
            container_id = excluded.container_id,
            cpu_limit = excluded.cpu_limit,
            memory_limit = excluded.memory_limit
        """,
        (agent_id, (container_id or "").strip(), max(0.1, min(8.0, float(cpu_limit))), max(128, min(4096, int(memory_limit))), now),
    )
    conn.commit()
    cur.execute("SELECT sandbox_id FROM agent_execution_sandbox WHERE agent_id = ?", (agent_id,))
    row = cur.fetchone()
    sandbox_id = row["sandbox_id"] if row else None
    return get_sandbox_for_agent(agent_id) or {}


def set_sandbox_container(agent_id: int, container_id: str) -> None:
    """Record the container id for a running sandbox (e.g. when worker starts the container)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_execution_sandbox SET container_id = ? WHERE agent_id = ?",
        (container_id.strip(), agent_id),
    )
    conn.commit()


# --- Trust metrics ---


def get_trust_metrics(agent_name: str) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_name, agent_id, runs_total, runs_success, runs_failed, success_rate, failure_rate, avg_runtime_ms, trust_score, last_updated FROM agent_trust_metrics WHERE agent_name = ?",
        (agent_name,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "agent_name": row["agent_name"],
        "agent_id": row.get("agent_id"),
        "runs_total": int(row["runs_total"] or 0),
        "runs_success": int(row["runs_success"] or 0),
        "runs_failed": int(row["runs_failed"] or 0),
        "success_rate": float(row["success_rate"]) if row["success_rate"] is not None else 1.0,
        "failure_rate": float(row["failure_rate"]) if row["failure_rate"] is not None else 0.0,
        "avg_runtime_ms": float(row["avg_runtime_ms"]) if row["avg_runtime_ms"] is not None else None,
        "trust_score": float(row["trust_score"]) if row["trust_score"] is not None else 1.0,
        "last_updated": row["last_updated"],
    }


def _ensure_trust_row(agent_name: str, agent_id: Optional[int] = None) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_trust_metrics (agent_name, agent_id, runs_total, runs_success, runs_failed, success_rate, failure_rate, trust_score, last_updated)
        VALUES (?, ?, 0, 0, 0, 1.0, 0.0, 1.0, ?)
        ON CONFLICT(agent_name) DO NOTHING
        """,
        (agent_name, agent_id, now),
    )
    conn.commit()


def record_run_success(agent_name: str, execution_time_ms: int, agent_id: Optional[int] = None) -> None:
    """Update trust metrics after a successful run."""
    _ensure_schema()
    _ensure_trust_row(agent_name, agent_id)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT runs_total, runs_success, avg_runtime_ms FROM agent_trust_metrics WHERE agent_name = ?",
        (agent_name,),
    )
    row = cur.fetchone()
    total = int(row["runs_total"] or 0) + 1 if row else 1
    success = int(row["runs_success"] or 0) + 1 if row else 1
    failed = total - success
    old_avg = float(row["avg_runtime_ms"]) if row and row["avg_runtime_ms"] is not None else None
    new_avg = execution_time_ms if old_avg is None else (old_avg * (total - 1) + execution_time_ms) / total
    success_rate = success / total
    failure_rate = failed / total
    trust_score = round(success_rate, 4)
    now = datetime.utcnow()
    cur.execute(
        """
        UPDATE agent_trust_metrics
        SET runs_total = ?, runs_success = ?, runs_failed = ?,
            success_rate = ?, failure_rate = ?, avg_runtime_ms = ?, trust_score = ?, last_updated = ?
        WHERE agent_name = ?
        """,
        (total, success, failed, success_rate, failure_rate, round(new_avg, 2), trust_score, now, agent_name),
    )
    conn.commit()


def record_run_failure(agent_name: str, agent_id: Optional[int] = None) -> None:
    """Update trust metrics after a failed run."""
    _ensure_schema()
    _ensure_trust_row(agent_name, agent_id)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT runs_total, runs_success, runs_failed FROM agent_trust_metrics WHERE agent_name = ?",
        (agent_name,),
    )
    row = cur.fetchone()
    total = int(row["runs_total"] or 0) + 1 if row else 1
    success = int(row["runs_success"] or 0) if row else 0
    failed = int(row["runs_failed"] or 0) + 1 if row else 1
    success_rate = success / total
    failure_rate = failed / total
    trust_score = round(success_rate, 4)
    now = datetime.utcnow()
    cur.execute(
        """
        UPDATE agent_trust_metrics
        SET runs_total = ?, runs_success = ?, runs_failed = ?,
            success_rate = ?, failure_rate = ?, trust_score = ?, last_updated = ?
        WHERE agent_name = ?
        """,
        (total, success, failed, success_rate, failure_rate, trust_score, now, agent_name),
    )
    conn.commit()


def get_trust_for_ranking(agent_name: str) -> float:
    """Return success_rate (0..1) for use in rank_score. Returns 0.5 if no data."""
    m = get_trust_metrics(agent_name)
    if not m or m.get("runs_total", 0) == 0:
        return 0.5
    return float(m.get("success_rate") or 0.5)


# --- Fraud signals ---


def record_fraud_signal(agent_id: int, signal_type: str, confidence: float, metadata: str = "") -> int:
    """Record a fraud signal (run_spike, install_spike, bot_activity, etc.). Returns signal_id."""
    _ensure_schema()
    if confidence < 0 or confidence > 1:
        confidence = max(0, min(1, confidence))
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO agent_fraud_signals (agent_id, signal_type, confidence, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
        (agent_id, signal_type.strip(), round(confidence, 4), (metadata or "").strip()[:2000], now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_fraud_signals(agent_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT signal_id, agent_id, signal_type, confidence, metadata, created_at FROM agent_fraud_signals WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
        (agent_id, limit),
    )
    out = []
    for r in cur.fetchall():
        out.append({
            "signal_id": r["signal_id"],
            "agent_id": r["agent_id"],
            "signal_type": r["signal_type"],
            "confidence": float(r["confidence"]),
            "metadata": r["metadata"] or "",
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        })
    return out


def has_recent_high_confidence_fraud(agent_id: int, signal_type: str, min_confidence: float = 0.8) -> bool:
    """True if there is a recent fraud signal of given type above confidence threshold."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT 1 FROM agent_fraud_signals
        WHERE agent_id = ? AND signal_type = ? AND confidence >= ?
        AND created_at >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
        LIMIT 1
        """,
        (agent_id, signal_type, min_confidence),
    )
    return cur.fetchone() is not None


# --- Fraud detection: spike detection (call after run or install) ---

RUN_SPIKE_THRESHOLD = 100   # runs in last hour
INSTALL_SPIKE_THRESHOLD = 30  # installs in last hour


def _runs_last_hour(agent_name: str) -> int:
    """Count runs for agent in the last hour (from agent_runs or usage)."""
    try:
        cur = db.get_connection().cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM agent_runs
            WHERE agent_name = ? AND created_at >= NOW() AT TIME ZONE 'UTC' - INTERVAL '1 hour'
            """,
            (agent_name,),
        )
        row = cur.fetchone()
        return int(row["n"]) if row and row["n"] is not None else 0
    except Exception:
        return 0


def check_run_spike_and_record(agent_id: int, agent_name: str) -> Optional[int]:
    """If runs in last hour exceed threshold, record run_spike fraud signal. Returns signal_id or None."""
    n = _runs_last_hour(agent_name)
    if n < RUN_SPIKE_THRESHOLD:
        return None
    confidence = min(0.99, 0.5 + (n - RUN_SPIKE_THRESHOLD) / 500.0)
    return record_fraud_signal(agent_id, "run_spike", confidence, metadata=f"runs_last_hour={n}")


def check_install_spike_and_record(agent_id: int, install_count_recent: int) -> Optional[int]:
    """If install count (e.g. last hour) exceeds threshold, record install_spike. Returns signal_id or None."""
    if install_count_recent < INSTALL_SPIKE_THRESHOLD:
        return None
    confidence = min(0.99, 0.5 + (install_count_recent - INSTALL_SPIKE_THRESHOLD) / 100.0)
    return record_fraud_signal(agent_id, "install_spike", confidence, metadata=f"installs_recent={install_count_recent}")
