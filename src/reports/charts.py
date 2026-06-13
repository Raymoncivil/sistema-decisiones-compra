"""Shared chart builders for reports and dashboard."""
from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_SEGMENT_COLORS = {
    "Estrella": "#f1c40f",
    "Vaca lechera": "#3498db",
    "Nicho": "#9b59b6",
    "Perro": "#95a5a6",
}
_DEFAULT_COLOR = "#bdc3c7"


def build_segments_chart(resumen_segmentos: list[dict]) -> bytes | None:
    """Render the KMeans segment chart and return PNG bytes, or None if no data."""
    if not resumen_segmentos:
        return None

    segmentos = [s["segmento"] for s in resumen_segmentos]
    productos = [s["productos"] for s in resumen_segmentos]
    beneficios = [s["beneficio_mensual_total"] for s in resumen_segmentos]
    chart_colors = [_SEGMENT_COLORS.get(s, _DEFAULT_COLOR) for s in segmentos]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor("#ffffff")

    bars1 = ax1.bar(segmentos, productos, color=chart_colors, edgecolor="white", linewidth=0.8)
    ax1.set_title("Productos por Segmento", fontsize=11, fontweight="bold", color="#2c3e50", pad=10)
    ax1.set_ylabel("Nº productos", fontsize=9, color="#7f8c8d")
    ax1.tick_params(colors="#2c3e50", labelsize=9)
    ax1.set_facecolor("#f8f9fa")
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.spines[["left", "bottom"]].set_color("#dee2e6")
    for bar, val in zip(bars1, productos):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            str(val),
            ha="center", va="bottom",
            fontsize=9, fontweight="bold", color="#2c3e50",
        )

    bars2 = ax2.bar(segmentos, beneficios, color=chart_colors, edgecolor="white", linewidth=0.8)
    ax2.set_title("Beneficio Mensual por Segmento (€)", fontsize=11, fontweight="bold", color="#2c3e50", pad=10)
    ax2.set_ylabel("Beneficio (€)", fontsize=9, color="#7f8c8d")
    ax2.tick_params(colors="#2c3e50", labelsize=9)
    ax2.set_facecolor("#f8f9fa")
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.spines[["left", "bottom"]].set_color("#dee2e6")
    for bar, val in zip(bars2, beneficios):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(beneficios) * 0.01,
            f"{val:,.0f}",
            ha="center", va="bottom",
            fontsize=8, fontweight="bold", color="#2c3e50",
        )

    plt.tight_layout(pad=2.0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
