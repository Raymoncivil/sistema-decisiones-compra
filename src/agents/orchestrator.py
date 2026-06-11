from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .data_agent import DataAgent
from .analysis_agent import AnalysisAgent
from .report_agent import ReportAgent
from .base import AgentResult
from src.reports import generate_pdf

log = logging.getLogger("Orchestrator")


@dataclass
class OrquestadorResult:
    success: bool
    reporte: dict[str, Any] = field(default_factory=dict)
    pipeline: list[AgentResult] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0.0

    @property
    def failed(self) -> bool:
        return not self.success

    @property
    def failed_agent(self) -> AgentResult | None:
        return next((r for r in self.pipeline if r.failed), None)


class Orchestrator:
    """
    Orquestador del pipeline de análisis de compra.

    Distribuye el trabajo a 3 subagentes en secuencia:
      1. DataAgent      — carga y valida el CSV
      2. AnalysisAgent  — rentabilidad y segmentación
      3. ReportAgent    — recomendaciones y reporte final

    Si cualquier subagente falla, detiene el pipeline y devuelve
    el error con contexto de qué agente falló.
    """

    def __init__(self) -> None:
        self._data_agent = DataAgent()
        self._analysis_agent = AnalysisAgent()
        self._report_agent = ReportAgent()

    def run(
        self,
        csv_path: Path | str,
        pdf_output: Path | str | None = None,
    ) -> OrquestadorResult:
        t0 = time.perf_counter()
        pipeline: list[AgentResult] = []
        log.info("=== pipeline iniciado | archivo: %s ===", Path(csv_path).name)

        # ── Paso 1: carga y validación ──────────────────────────────────────
        log.info("[1/3] DataAgent")
        data_result = self._data_agent.run(csv_path)
        pipeline.append(data_result)
        if data_result.failed:
            log.error("pipeline abortado en DataAgent")
            return self._abort(pipeline, data_result.error, t0)

        # ── Paso 2: análisis y segmentación ──────────────────────────────────
        log.info("[2/3] AnalysisAgent")
        analysis_result = self._analysis_agent.run(data_result.data["df"])
        pipeline.append(analysis_result)
        if analysis_result.failed:
            log.error("pipeline abortado en AnalysisAgent")
            return self._abort(pipeline, analysis_result.error, t0)

        # ── Paso 3: recomendaciones y reporte ────────────────────────────────
        log.info("[3/3] ReportAgent")
        report_result = self._report_agent.run(
            df_ranked=analysis_result.data["df_ranked"],
            df_segmented=analysis_result.data["df_segmented"],
            segment_summary=analysis_result.data["segment_summary"],
        )
        pipeline.append(report_result)
        if report_result.failed:
            log.error("pipeline abortado en ReportAgent")
            return self._abort(pipeline, report_result.error, t0)

        reporte = {
            **report_result.data,
            "metricas_pipeline": {
                "archivo": data_result.data["archivo"],
                "filas_cargadas": data_result.data["filas"],
                "score_max": analysis_result.data["score_max"],
                "score_min": analysis_result.data["score_min"],
                "segmentos_encontrados": analysis_result.data["segmentos_encontrados"],
                "tiempos_ms": {r.agent: r.duration_ms for r in pipeline},
            },
        }

        if pdf_output is not None:
            generate_pdf(reporte, output_path=pdf_output)

        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        log.info("=== pipeline completado en %.2f ms ===", total_ms)
        return OrquestadorResult(
            success=True,
            reporte=reporte,
            pipeline=pipeline,
            duration_ms=total_ms,
        )

    @staticmethod
    def _abort(pipeline: list[AgentResult], error: str | None, t0: float) -> OrquestadorResult:
        return OrquestadorResult(
            success=False,
            pipeline=pipeline,
            error=error,
            duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
