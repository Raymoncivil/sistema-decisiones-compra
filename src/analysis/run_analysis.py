"""Entry point: run the full analysis pipeline and print results."""

from pathlib import Path

import pandas as pd

from src.data.loader import load_products
from src.analysis.profitability import rank_products, top_n, bottom_n
from src.analysis.segmentation import segment_products, segment_summary
from src.recommendations.engine import generate_recommendations, recommendations_to_df

DATA_PATH = Path(__file__).parent.parent / "data" / "productos.csv"

_SEP = "-" * 70


def _print_section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def run(data_path: Path = DATA_PATH) -> None:
    df = load_products(data_path)

    # ── 1. Full ranking ───────────────────────────────────────────────────
    _print_section("RANKING COMPLETO DE RENTABILIDAD")
    ranked = rank_products(df)
    display_cols = ["nombre", "categoria", "margen_unitario", "margen_pct",
                    "beneficio_mensual", "roi_mensual", "score_rentabilidad"]
    with pd.option_context("display.max_colwidth", 30, "display.float_format", "{:.2f}".format):
        print(ranked[display_cols].to_string())

    # ── 2. Top 5 ──────────────────────────────────────────────────────────
    _print_section("TOP 5 PRODUCTOS MÁS RENTABLES")
    top = top_n(df, 5)
    for i, row in top.iterrows():
        print(
            f"  {i}. {row['nombre']:<35} "
            f"beneficio {row['beneficio_mensual']:>7.2f} €/mes  "
            f"score {row['score_rentabilidad']:.3f}"
        )

    # ── 3. Bottom 3 ───────────────────────────────────────────────────────
    _print_section("3 PRODUCTOS MENOS RENTABLES")
    bottom = bottom_n(df, 3)
    for i, row in bottom.iterrows():
        print(
            f"  {i}. {row['nombre']:<35} "
            f"beneficio {row['beneficio_mensual']:>7.2f} €/mes  "
            f"score {row['score_rentabilidad']:.3f}"
        )

    # ── 4. Segmentation ───────────────────────────────────────────────────
    _print_section("SEGMENTACIÓN DE PRODUCTOS")
    seg_df = segment_products(df)
    seg_display = seg_df[["nombre", "categoria", "segmento", "beneficio_mensual", "margen_pct"]].copy()
    seg_display = seg_display.sort_values(["segmento", "beneficio_mensual"], ascending=[True, False])
    with pd.option_context("display.max_colwidth", 30, "display.float_format", "{:.2f}".format):
        print(seg_display.to_string(index=False))

    _print_section("RESUMEN POR SEGMENTO")
    with pd.option_context("display.float_format", "{:.2f}".format):
        print(segment_summary(df).to_string())

    # ── 5. Recommendations ────────────────────────────────────────────────
    _print_section("RECOMENDACIONES DE COMPRA")
    recs = generate_recommendations(df)
    recs_df = recommendations_to_df(recs)

    for decision in ("COMPRAR", "USAR_ALTERNATIVA", "NO_COMPRAR"):
        subset = recs_df[recs_df["decision"] == decision]
        if subset.empty:
            continue
        icon = {"COMPRAR": "+", "USAR_ALTERNATIVA": "~", "NO_COMPRAR": "x"}[decision]
        print(f"\n  [{icon}] {decision} ({len(subset)} productos)")
        for _, r in subset.iterrows():
            alt = f" -> alternativa: {r['alternativa']}" if r["alternativa"] != "-" else ""
            print(f"      · {r['nombre']:<35} confianza {r['confianza']:.0%}{alt}")
            print(f"        {r['razonamiento']}")


if __name__ == "__main__":
    run()
