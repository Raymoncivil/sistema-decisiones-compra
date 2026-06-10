import io
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile

from src.analysis.profitability import rank_products
from src.analysis.segmentation import segment_products, segment_summary
from src.data.loader import load_products
from src.recommendations.engine import generate_recommendations

from .models import RecomendacionProducto, ResumenSegmento, RespuestaAnalisis

app = FastAPI(
    title="Sistema de Decisiones de Compra",
    description="Analiza productos desde un CSV y devuelve recomendaciones de compra.",
    version="1.0.0",
)


@app.post("/analizar", response_model=RespuestaAnalisis)
async def analizar(archivo: UploadFile = File(..., description="CSV con columnas: nombre, precio_compra, precio_venta, unidades_vendidas_mes, categoria")):
    if not archivo.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV.")

    contenido = await archivo.read()

    # loader.load_products requiere un path en disco — escribimos a un temporal
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(contenido)
        tmp_path = Path(tmp.name)

    try:
        df = load_products(tmp_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    df_ranked = rank_products(df)

    try:
        df_segmentado = segment_products(df_ranked)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    recomendaciones = generate_recommendations(df_ranked)
    resumen = segment_summary(df_segmentado)

    return RespuestaAnalisis(
        total_productos=len(df),
        recomendaciones=[
            RecomendacionProducto(
                nombre=r.nombre,
                categoria=r.categoria,
                decision=r.decision,
                confianza=round(r.confianza, 4),
                razonamiento=r.razonamiento,
                alternativa=r.alternativa,
            )
            for r in recomendaciones
        ],
        resumen_segmentos=[
            ResumenSegmento(
                segmento=segmento,
                productos=int(row["productos"]),
                beneficio_mensual_total=round(row["beneficio_mensual_total"], 2),
                margen_pct_promedio=round(row["margen_pct_promedio"], 2),
                rotacion_promedio=round(row["rotacion_promedio"], 2),
            )
            for segmento, row in resumen.iterrows()
        ],
    )
