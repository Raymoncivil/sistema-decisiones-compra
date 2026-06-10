from __future__ import annotations

from pathlib import Path

from src.data.loader import load_products
from .base import AgentResult, timed

AGENT_NAME = "DataAgent"


class DataAgent:
    """Carga y valida el CSV de productos. Devuelve un DataFrame limpio."""

    @timed(AGENT_NAME)
    def run(self, csv_path: Path | str) -> AgentResult:
        csv_path = Path(csv_path)
        try:
            df = load_products(csv_path)
        except (FileNotFoundError, ValueError) as exc:
            return AgentResult(agent=AGENT_NAME, success=False, error=str(exc))

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
