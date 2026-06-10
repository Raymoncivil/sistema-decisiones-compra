from __future__ import annotations

import logging

import pandas as pd

from src.recommendations.engine import generate_recommendations
from .base import AgentResult, timed

AGENT_NAME = "ReportAgent"
log = logging.getLogger(AGENT_NAME)


class ReportAgent:
    """Genera recomendaciones de compra y el reporte final estructurado."""

    @timed(AGENT_NAME)
    def run(self, df_ranked: pd.DataFrame, df_segmented: pd.DataFrame, segment_summary: pd.DataFrame) -> AgentResult:
        log.debug("generando recomendaciones para %d productos...", len(df_ranked))
        try:
            recomendaciones = generate_recommendations(df_ranked)
        except Exception as exc:
            return AgentResult(agent=AGENT_NAME, success=False, error=str(exc))

        conteo = {d: sum(1 for r in recomendaciones if r.decision == d)
                  for d in ("COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA")}

        for decision, n in conteo.items():
            log.debug("  %-20s : %d", decision, n)

        log.debug("serializando reporte final...")
        recs_json = [
            {
                "nombre": r.nombre,
                "categoria": r.categoria,
                "decision": r.decision,
                "score": r.score,
                "confianza": round(r.confianza, 4),
                "razonamiento": r.razonamiento,
                "alternativa": r.alternativa,
            }
            for r in recomendaciones
        ]

        resumen_json = [
            {
                "segmento": segmento,
                "productos": int(row["productos"]),
                "beneficio_mensual_total": round(row["beneficio_mensual_total"], 2),
                "margen_pct_promedio": round(row["margen_pct_promedio"], 2),
                "rotacion_promedio": round(row["rotacion_promedio"], 2),
            }
            for segmento, row in segment_summary.iterrows()
        ]

        return AgentResult(
            agent=AGENT_NAME,
            success=True,
            data={
                "recomendaciones": recs_json,
                "resumen_segmentos": resumen_json,
                "total_productos": len(recomendaciones),
                "conteo_decisiones": conteo,
            },
        )
