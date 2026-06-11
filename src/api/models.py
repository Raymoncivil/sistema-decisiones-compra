from pydantic import BaseModel


class RecomendacionProducto(BaseModel):
    nombre: str
    categoria: str
    decision: str
    confianza: float
    razonamiento: str
    alternativa: str | None


class ResumenSegmento(BaseModel):
    segmento: str
    productos: int
    beneficio_mensual_total: float
    margen_pct_promedio: float
    rotacion_promedio: float


class MetricasPipeline(BaseModel):
    archivo: str
    filas_cargadas: int
    score_max: float
    score_min: float
    segmentos_encontrados: list[str]
    tiempos_ms: dict[str, float]


class RespuestaAnalisis(BaseModel):
    reporte_id: str
    total_productos: int
    conteo_decisiones: dict[str, int]
    recomendaciones: list[RecomendacionProducto]
    resumen_segmentos: list[ResumenSegmento]
    metricas_pipeline: MetricasPipeline
