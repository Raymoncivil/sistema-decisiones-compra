import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.agents.orchestrator import Orchestrator

from .models import MetricasPipeline, RecomendacionProducto, ResumenSegmento, RespuestaAnalisis

app = FastAPI(
    title="Sistema de Decisiones de Compra",
    description="Analiza productos desde un CSV y devuelve recomendaciones de compra.",
    version="2.0.0",
)

_orchestrator = Orchestrator()


@app.post("/analizar", response_model=RespuestaAnalisis)
async def analizar(archivo: UploadFile = File(..., description="CSV con columnas: nombre, precio_compra, precio_venta, unidades_vendidas_mes, categoria")):
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
        status = _status_code(resultado)
        raise HTTPException(status_code=status, detail=resultado.error)

    r = resultado.reporte
    m = r["metricas_pipeline"]

    return RespuestaAnalisis(
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


def _status_code(resultado) -> int:
    """Mapea el agente fallido a un código HTTP semánticamente correcto."""
    agent = resultado.failed_agent
    if agent is None:
        return 500
    if agent.agent == "DataAgent":
        # FileNotFoundError no ocurre (usamos tmp), todo lo demás es validación
        return 422
    if agent.agent == "AnalysisAgent":
        return 422
    return 500
