from __future__ import annotations

import logging
from pathlib import Path

from src.data.loader import load_products
from .base import AgentResult, timed

AGENT_NAME = "DataAgent"
log = logging.getLogger(AGENT_NAME)


class DataAgent:
    """Carga y valida el CSV de productos. Devuelve un DataFrame limpio."""

    @timed(AGENT_NAME)
    def run(self, csv_path: Path | str) -> AgentResult:
        csv_path = Path(csv_path)
        log.debug("leyendo archivo: %s", csv_path.resolve())

        try:
            df = load_products(csv_path)
        except (FileNotFoundError, ValueError) as exc:
            return AgentResult(agent=AGENT_NAME, success=False, error=str(exc))

        log.debug(
            "cargadas %d filas, %d columnas: %s",
            len(df), len(df.columns), list(df.columns),
        )
        nulls = df.isnull().sum().sum()
        log.debug("valores nulos detectados: %d", nulls)

        return AgentResult(
            agent=AGENT_NAME,
            success=True,
            data={
                "df": df,
                "filas": len(df),
                "columnas": list(df.columns),
                "archivo": csv_path.name,
            },
        )
