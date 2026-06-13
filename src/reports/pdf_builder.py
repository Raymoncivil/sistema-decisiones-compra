"""PDF report generator for purchase decision analysis."""
from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .charts import build_segments_chart as _build_chart_png

log = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm

_DECISION_COLORS = {
    "COMPRAR": colors.HexColor("#27ae60"),
    "NO_COMPRAR": colors.HexColor("#c0392b"),
    "USAR_ALTERNATIVA": colors.HexColor("#e67e22"),
}


def generate_pdf(
    reporte: dict[str, Any],
    output_path: Path | str | None = None,
) -> bytes:
    """Generate a PDF from the orchestrator's report dict.

    Args:
        reporte: dict produced by ``Orchestrator.run().reporte``.
        output_path: if given, the PDF is also written to this path.

    Returns:
        Raw PDF bytes.
    """
    log.info("generando PDF...")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    styles = _build_styles()
    story: list = []

    _add_header(story, styles, reporte)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2c3e50")))
    story.append(Spacer(1, 0.5 * cm))

    _add_resumen_ejecutivo(story, styles, reporte)
    story.append(Spacer(1, 0.8 * cm))

    _add_recommendations_table(story, styles, reporte.get("recomendaciones", []))
    story.append(Spacer(1, 0.8 * cm))

    chart_img = _build_segments_chart(reporte.get("resumen_segmentos", []))
    if chart_img is not None:
        story.append(Paragraph("Análisis por Segmento KMeans", styles["section_title"]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(chart_img)

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        log.info("PDF guardado en %s (%d bytes)", out, len(pdf_bytes))

    log.info("PDF generado (%d bytes)", len(pdf_bytes))
    return pdf_bytes


# ── Styles ────────────────────────────────────────────────────────────────────

def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    dark = "#2c3e50"
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=20,
            textColor=colors.HexColor(dark),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#7f8c8d"),
        ),
        "section_title": ParagraphStyle(
            "section_title",
            parent=base["Heading2"],
            fontSize=12,
            textColor=colors.HexColor(dark),
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor(dark),
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#7f8c8d"),
            alignment=1,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value",
            parent=base["Normal"],
            fontSize=22,
            fontName="Helvetica-Bold",
            alignment=1,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor(dark),
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#7f8c8d"),
        ),
    }


# ── Header ────────────────────────────────────────────────────────────────────

def _add_header(story: list, styles: dict, reporte: dict) -> None:
    story.append(Paragraph("Sistema de Decisiones de Compra", styles["title"]))
    metricas = reporte.get("metricas_pipeline", {})
    archivo = metricas.get("archivo", "—")
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(
        Paragraph(f"Reporte generado el {fecha} &nbsp;·&nbsp; Archivo: {archivo}", styles["subtitle"])
    )


# ── Resumen ejecutivo ─────────────────────────────────────────────────────────

def _add_resumen_ejecutivo(story: list, styles: dict, reporte: dict) -> None:
    story.append(Paragraph("Resumen Ejecutivo", styles["section_title"]))

    total = reporte.get("total_productos", 0)
    conteo = reporte.get("conteo_decisiones", {})

    kpis = [
        ("Total productos", str(total), "#2c3e50"),
        ("Comprar", str(conteo.get("COMPRAR", 0)), "#27ae60"),
        ("Usar alternativa", str(conteo.get("USAR_ALTERNATIVA", 0)), "#e67e22"),
        ("No comprar", str(conteo.get("NO_COMPRAR", 0)), "#c0392b"),
    ]

    cell_w = (PAGE_W - 2 * MARGIN) / len(kpis)

    def kpi_cell(label: str, value: str, hex_color: str):
        label_p = Paragraph(label.upper(), styles["kpi_label"])
        value_p = Paragraph(
            f'<font color="{hex_color}"><b>{value}</b></font>',
            styles["kpi_value"],
        )
        return [label_p, value_p]

    cells = [[kpi_cell(l, v, c) for l, v, c in kpis]]
    col_widths = [cell_w] * len(kpis)

    tbl = Table(cells, colWidths=col_widths, rowHeights=[1.6 * cm])
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)

    metricas = reporte.get("metricas_pipeline", {})
    score_max = metricas.get("score_max", 0)
    score_min = metricas.get("score_min", 0)
    filas = metricas.get("filas_cargadas", 0)
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"Filas procesadas: {filas} &nbsp;·&nbsp; "
            f"Score máximo: {score_max:.2f} &nbsp;·&nbsp; Score mínimo: {score_min:.2f}",
            styles["small"],
        )
    )


# ── Recommendations table ─────────────────────────────────────────────────────

_TOP_N = 10


def _add_recommendations_table(story: list, styles: dict, recomendaciones: list[dict]) -> None:
    comprar = [r for r in recomendaciones if r["decision"] == "COMPRAR"]
    alternativa = [r for r in recomendaciones if r["decision"] == "USAR_ALTERNATIVA"]

    comprar.sort(key=lambda r: r.get("confianza", 0), reverse=True)
    alternativa.sort(key=lambda r: r.get("confianza", 0), reverse=True)

    if comprar:
        story.append(
            Paragraph(f"Top Recomendaciones — COMPRAR ({len(comprar)} productos)", styles["section_title"])
        )
        story.append(_build_rec_table(comprar[:_TOP_N], styles, "#27ae60"))
        story.append(Spacer(1, 0.5 * cm))

    if alternativa:
        story.append(
            Paragraph(
                f"Top Recomendaciones — USAR ALTERNATIVA ({len(alternativa)} productos)",
                styles["section_title"],
            )
        )
        story.append(_build_rec_table(alternativa[:_TOP_N], styles, "#e67e22"))


def _build_rec_table(rows: list[dict], styles: dict, accent_hex: str) -> Table:
    accent = colors.HexColor(accent_hex)
    header_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dee2e6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ])

    usable_w = PAGE_W - 2 * MARGIN
    col_widths = [
        usable_w * 0.20,  # nombre
        usable_w * 0.12,  # categoría
        usable_w * 0.08,  # confianza
        usable_w * 0.44,  # razonamiento
        usable_w * 0.16,  # alternativa
    ]

    headers = ["Producto", "Categoría", "Confianza", "Razonamiento", "Alternativa"]
    data = [headers]
    for r in rows:
        data.append([
            r.get("nombre", ""),
            r.get("categoria", ""),
            f"{r.get('confianza', 0):.0%}",
            r.get("razonamiento", ""),
            r.get("alternativa") or "—",
        ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(header_style)
    return tbl


# ── Segments chart ────────────────────────────────────────────────────────────

def _build_segments_chart(resumen_segmentos: list[dict]) -> Image | None:
    png = _build_chart_png(resumen_segmentos)
    if png is None:
        return None
    usable_w = PAGE_W - 2 * MARGIN
    return Image(io.BytesIO(png), width=usable_w, height=usable_w * 0.42)
