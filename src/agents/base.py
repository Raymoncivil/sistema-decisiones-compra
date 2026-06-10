from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    agent: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0

    @property
    def failed(self) -> bool:
        return not self.success


class AgentError(Exception):
    """Raised when an agent cannot complete its work."""


def timed(agent_name: str):
    """Decorator that wraps a run() method, fills AgentResult timing, and emits start/end logs."""
    def decorator(fn):
        def wrapper(*args, **kwargs) -> AgentResult:
            log = logging.getLogger(agent_name)
            log.info("iniciando")
            t0 = time.perf_counter()
            result: AgentResult = fn(*args, **kwargs)
            result.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if result.success:
                log.info("completado en %.2f ms", result.duration_ms)
            else:
                log.error("FALLO en %.2f ms — %s", result.duration_ms, result.error)
            return result
        return wrapper
    return decorator
