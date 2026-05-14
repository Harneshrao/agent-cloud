"""
Container pooling for agent sandbox execution.

Pre-starts a configurable number of containers and reuses them for
run_agent() calls to reduce latency and overhead vs. starting a new
container per task.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Optional, Set

# Pool size and image from environment.
CONTAINER_POOL_SIZE = int(os.environ.get("CONTAINER_POOL_SIZE", "5"))
SANDBOX_IMAGE = os.environ.get("AGENT_SANDBOX_IMAGE", "agent-runtime:latest")

# Resource limits applied to each pool container.
CONTAINER_MEMORY = os.environ.get("AGENT_SANDBOX_MEMORY", "256m")
CONTAINER_CPUS = os.environ.get("AGENT_SANDBOX_CPUS", "0.5")


class ContainerPool:
    """
    Maintains idle and busy container lists, provides acquire/release,
    and restarts containers that have crashed.
    """

    def __init__(
        self,
        size: Optional[int] = None,
        image: Optional[str] = None,
        platform_root: Optional[Path] = None,
    ) -> None:
        self._size = size if size is not None else CONTAINER_POOL_SIZE
        self._image = image or SANDBOX_IMAGE
        if platform_root is None:
            platform_root = Path(__file__).resolve().parent.parent
        self._platform_root = Path(platform_root)
        self._idle: List[str] = []
        self._busy: Set[str] = set()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._initialized = False

    def _start_one(self) -> Optional[str]:
        """Start one container; return container id or None on failure."""
        cmd = [
            "docker",
            "run",
            "-d",
            "-v", f"{self._platform_root}:/app/platform:ro",
            "--network", "none",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "--memory", CONTAINER_MEMORY,
            "--cpus", CONTAINER_CPUS,
            self._image,
            "sleep", "infinity",
        ]
        try:
            out = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._platform_root),
            )
            if out.returncode != 0:
                return None
            return (out.stdout or "").strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None

    def _is_running(self, container_id: str) -> bool:
        """Return True if the container exists and is running."""
        try:
            out = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return out.returncode == 0 and (out.stdout or "").strip().lower() == "true"
        except Exception:
            return False

    def _remove(self, container_id: str) -> None:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass

    def initialize(self) -> None:
        """Start the configured number of containers and fill the idle list."""
        with self._lock:
            if self._initialized:
                return
            for _ in range(self._size):
                cid = self._start_one()
                if cid:
                    self._idle.append(cid)
            self._initialized = True

    def acquire_container(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Take a container from the idle list; block until one is available.

        Returns container id, or None if timeout is reached or pool could not
        provide a container. Caller must call release_container when done.
        """
        self.initialize()
        with self._condition:
            deadline = (time.monotonic() + timeout) if timeout is not None else None
            while True:
                if self._idle:
                    cid = self._idle.pop()
                    self._busy.add(cid)
                    return cid
                # Try to replace any crashed busy containers so we can grow idle again
                for cid in list(self._busy):
                    if not self._is_running(cid):
                        self._busy.discard(cid)
                        self._remove(cid)
                        new_cid = self._start_one()
                        if new_cid:
                            self._idle.append(new_cid)
                if self._idle:
                    continue
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._condition.wait(timeout=min(remaining, 5.0))
                else:
                    self._condition.wait(timeout=5.0)

    def release_container(self, container_id: str) -> None:
        """
        Return a container to the pool. If it has crashed, remove it and
        start a new one for the idle list.
        """
        with self._condition:
            self._busy.discard(container_id)
            if self._is_running(container_id):
                self._idle.append(container_id)
            else:
                self._remove(container_id)
                new_cid = self._start_one()
                if new_cid:
                    self._idle.append(new_cid)
            self._condition.notify()

    @property
    def idle_containers(self) -> List[str]:
        """Current list of idle container ids (snapshot)."""
        with self._lock:
            return list(self._idle)

    @property
    def busy_containers(self) -> List[str]:
        """Current list of busy container ids (snapshot)."""
        with self._lock:
            return list(self._busy)


# Default process-wide pool; lazily initialized on first use.
_default_pool: Optional[ContainerPool] = None
_default_pool_lock = threading.Lock()


def get_pool() -> ContainerPool:
    """Return the default container pool (lazily created)."""
    global _default_pool
    with _default_pool_lock:
        if _default_pool is None:
            _default_pool = ContainerPool()
        return _default_pool
