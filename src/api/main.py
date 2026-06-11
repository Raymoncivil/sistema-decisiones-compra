import tempfile
import uuid
from pathlib import Path

from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from src.agents.orchestrator import Orchestrator
from src.reports import generate_pdf

from .models import MetricasPipeline, RecomendacionProducto, ResumenSegmento, RespuestaAnalisis

app = FastAPI(
    title="Sistema de Decisiones de Compra",
    description="Analiza productos desde un CSV y devuelve recomendaciones de compra.",
    version="2.0.0",
)

_orchestrator = Orchestrator()

_REPORTS_DIR = Path(tempfile.gettempdir()) / "sdcompra_reports"
_REPORTS_DIR.mkdir(exist_ok=True)

# Maps reporte_id -> PDF path; lives for the duration of the server process.
_reports: dict[str, Path] = {}


@app.post(
    "/analizar",
    response_model=RespuestaAnalisis,
    responses={200: {"content": {"application/pdf": {}}, "description": "JSON o PDF según ?formato"}},
)
async def analizar(
    archivo: UploadFile = File(..., description="CSV con columnas: nombre, precio_compra, precio_venta, unidades_vendidas_mes, categoria"),
    formato: Literal["pdf"] | None = Query(default=None, description="Si es 'pdf', devuelve el reporte en PDF en lugar de JSON."),
):
    if not archivo.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV.")

    contenido = await archivo.read()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(contenido)
        tmp_path = Path(tmp.name)

    try:
        resultado = _orchestrator.run(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if resultado.failed:
        raise HTTPException(status_code=_status_code(resultado), detail=resultado.error)

    reporte_id = str(uuid.uuid4())
    pdf_path = _REPORTS_DIR / f"{reporte_id}.pdf"
    generate_pdf(resultado.reporte, output_path=pdf_path)
    _reports[reporte_id] = pdf_path

    if formato == "pdf":
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"reporte_{reporte_id[:8]}.pdf",
        )

    r = resultado.reporte
    m = r["metricas_pipeline"]

    return RespuestaAnalisis(
        reporte_id=reporte_id,
        total_productos=r["total_productos"],
        conteo_decisiones=r["conteo_decisiones"],
        recomendaciones=[RecomendacionProducto(**rec) for rec in r["recomendaciones"]],
        resumen_segmentos=[ResumenSegmento(**seg) for seg in r["resumen_segmentos"]],
        metricas_pipeline=MetricasPipeline(
            archivo=m["archivo"],
            filas_cargadas=m["filas_cargadas"],
            score_max=m["score_max"],
            score_min=m["score_min"],
            segmentos_encontrados=m["segmentos_encontrados"],
            tiempos_ms=m["tiempos_ms"],
        ),
    )


@app.get("/reporte/{reporte_id}")
async def descargar_reporte(reporte_id: str):
    pdf_path = _reports.get(reporte_id)
    if pdf_path is None or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Reporte no encontrado.")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"reporte_{reporte_id[:8]}.pdf",
    )


def _status_code(resultado) -> int:
    agent = resultado.failed_agent
    if agent is None:
        return 500
    if agent.agent in ("DataAgent", "AnalysisAgent"):
        return 422
    return 500
