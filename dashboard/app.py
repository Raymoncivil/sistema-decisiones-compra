"""Streamlit dashboard for Sistema de Decisiones de Compra."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.api_client import APIClient, APIError
from src.reports.charts import build_segments_chart

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Decisiones de Compra",
    page_icon="📦",
    layout="wide",
)

st.title("Sistema de Decisiones de Compra")
st.caption("Sube un CSV para analizar productos y obtener recomendaciones.")

# ── Sección 1: carga de archivo ───────────────────────────────────────────────

uploaded = st.file_uploader("Archivo CSV de productos", type=["csv"])

if uploaded is None:
    st.info("Sube un archivo CSV para comenzar.")
    st.stop()

if st.button("Analizar", type="primary"):
    with st.spinner("Analizando…"):
        try:
            with APIClient(base_url=API_URL) as api:
                data = api.analyze_bytes(uploaded.getvalue(), filename=uploaded.name)
            st.session_state["data"] = data
            st.session_state["pdf_id"] = data.get("reporte_id")
        except APIError as exc:
            st.error(f"Error del servidor: {exc.detail}")
            st.stop()

data: dict | None = st.session_state.get("data")
if data is None:
    st.stop()

# ── Sección 2: KPIs ───────────────────────────────────────────────────────────

st.divider()
st.subheader("Resumen ejecutivo")

conteo = data.get("conteo_decisiones", {})
total = data.get("total_productos", 0)
metricas = data.get("metricas_pipeline", {})

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total productos", total)
col2.metric("COMPRAR", conteo.get("COMPRAR", 0), delta=None)
col3.metric("USAR ALTERNATIVA", conteo.get("USAR_ALTERNATIVA", 0))
col4.metric("NO COMPRAR", conteo.get("NO_COMPRAR", 0))
col5.metric("Filas procesadas", metricas.get("filas_cargadas", "—"))

# ── Sección 3: tabla de recomendaciones ───────────────────────────────────────

st.divider()
st.subheader("Recomendaciones")

recs = data.get("recomendaciones", [])
if recs:
    df = pd.DataFrame(recs)
    df["confianza"] = (df["confianza"] * 100).round(1).astype(str) + " %"
    df = df.rename(columns={
        "nombre": "Producto",
        "categoria": "Categoría",
        "decision": "Decisión",
        "confianza": "Confianza",
        "razonamiento": "Razonamiento",
        "alternativa": "Alternativa",
    })
    df["Alternativa"] = df["Alternativa"].fillna("—")

    decision_filter = st.multiselect(
        "Filtrar por decisión",
        options=["COMPRAR", "USAR_ALTERNATIVA", "NO_COMPRAR"],
        default=["COMPRAR", "USAR_ALTERNATIVA", "NO_COMPRAR"],
    )
    filtered = df[df["Decisión"].isin(decision_filter)]

    _COLORS = {
        "COMPRAR": "background-color: #d5f5e3",
        "USAR_ALTERNATIVA": "background-color: #fdebd0",
        "NO_COMPRAR": "background-color: #fadbd8",
    }

    def _row_color(row):
        color = _COLORS.get(row["Decisión"], "")
        return [color] * len(row)

    st.dataframe(
        filtered.style.apply(_row_color, axis=1),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.warning("No hay recomendaciones disponibles.")

# ── Sección 4: gráfico de segmentos ──────────────────────────────────────────

st.divider()
st.subheader("Análisis por Segmento KMeans")

segmentos = data.get("resumen_segmentos", [])
png = build_segments_chart(segmentos)
if png:
    st.image(png, use_container_width=True)
else:
    st.info("No hay datos de segmentos para mostrar.")

# ── Descarga de PDF ───────────────────────────────────────────────────────────

st.divider()
pdf_id: str | None = st.session_state.get("pdf_id")
if pdf_id:
    if st.button("Descargar reporte PDF"):
        with st.spinner("Descargando PDF…"):
            try:
                with APIClient(base_url=API_URL) as api:
                    pdf_bytes = api.download_pdf(pdf_id)
                st.download_button(
                    label="Guardar PDF",
                    data=pdf_bytes,
                    file_name=f"reporte_{pdf_id[:8]}.pdf",
                    mime="application/pdf",
                )
            except APIError as exc:
                st.error(f"No se pudo descargar el PDF: {exc.detail}")
