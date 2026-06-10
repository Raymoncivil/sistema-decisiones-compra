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


class RespuestaAnalisis(BaseModel):
    total_productos: int
    recomendaciones: list[RecomendacionProducto]
    resumen_segmentos: list[ResumenSegmento]
