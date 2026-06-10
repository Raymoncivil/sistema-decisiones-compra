from __future__ import annotations

import pandas as pd

from src.analysis.profitability import rank_products
from src.analysis.segmentation import segment_products, segment_summary
from .base import AgentResult, timed

AGENT_NAME = "AnalysisAgent"


class AnalysisAgent:
    """Calcula rentabilidad, ranking y segmentación KMeans."""

    @timed(AGENT_NAME)
    def run(self, df: pd.DataFrame) -> AgentResult:
        try:
            df_ranked = rank_products(df)
            df_segmented = segment_products(df_ranked)
            resumen = segment_summary(df_segmented)
        except ValueError as exc:
            return AgentResult(agent=AGENT_NAME, success=False, error=str(exc))

        return AgentResult(
            agent=AGENT_NAME,
            success=True,
            data={
                "df_ranked": df_ranked,
                "df_segmented": df_segmented,
                "segment_summary": resumen,
                "score_max": round(float(df_ranked["score_rentabilidad"].max()), 4),
                "score_min": round(float(df_ranked["score_rentabilidad"].min()), 4),
                "segmentos_encontrados": list(df_segmented["segmento"].unique()),
            },
        )
