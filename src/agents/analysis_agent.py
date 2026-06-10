from __future__ import annotations

import logging

import pandas as pd

from src.analysis.profitability import rank_products
from src.analysis.segmentation import segment_products, segment_summary
from .base import AgentResult, timed

AGENT_NAME = "AnalysisAgent"
log = logging.getLogger(AGENT_NAME)


class AnalysisAgent:
    """Calcula rentabilidad, ranking y segmentación KMeans."""

    @timed(AGENT_NAME)
    def run(self, df: pd.DataFrame) -> AgentResult:
        log.debug("input: %d productos", len(df))

        try:
            log.debug("calculando rentabilidad y ranking...")
            df_ranked = rank_products(df)
            score_max = round(float(df_ranked["score_rentabilidad"].max()), 4)
            score_min = round(float(df_ranked["score_rentabilidad"].min()), 4)
            log.debug("scores — max: %.4f  min: %.4f", score_max, score_min)

            log.debug("ejecutando segmentación KMeans (k=4)...")
            df_segmented = segment_products(df_ranked)
            segmentos = list(df_segmented["segmento"].unique())
            for seg in sorted(segmentos):
                n = (df_segmented["segmento"] == seg).sum()
                log.debug("  segmento %-15s : %d productos", seg, n)

            log.debug("calculando resumen por segmento...")
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
                "score_max": score_max,
                "score_min": score_min,
                "segmentos_encontrados": segmentos,
            },
        )
