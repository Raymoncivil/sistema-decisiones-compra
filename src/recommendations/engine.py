"""Decision engine: buy / do not buy / use alternative — with reasoning and confidence."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from src.analysis.profitability import compute_metrics, compute_composite_score


Decision = Literal["COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA"]

# Thresholds (tunable)
SCORE_BUY = 0.45        # score >= this → buy
SCORE_ALTERNATIVE = 0.25  # score in [this, BUY) → look for alternative
                          # score < this → do not buy


@dataclass
class Recommendation:
    nombre: str
    categoria: str
    decision: Decision
    confianza: float          # 0.0 – 1.0
    razonamiento: str
    alternativa: str | None = None


def _build_reasoning(row: pd.Series, decision: Decision) -> str:
    if decision == "COMPRAR":
        return (
            f"Score {row.score_rentabilidad:.2f} — "
            f"beneficio mensual {row.beneficio_mensual:.2f} €, "
            f"margen {row.margen_pct:.1f}%, "
            f"rotación {int(row.unidades_vendidas_mes)} uds/mes."
        )
    if decision == "USAR_ALTERNATIVA":
        return (
            f"Score medio ({row.score_rentabilidad:.2f}): "
            f"beneficio mensual {row.beneficio_mensual:.2f} €. "
            f"Existe un producto en la misma categoría con mejor rentabilidad."
        )
    return (
        f"Score bajo ({row.score_rentabilidad:.2f}): "
        f"beneficio mensual {row.beneficio_mensual:.2f} €, "
        f"rotación {int(row.unidades_vendidas_mes)} uds/mes. "
        "No justifica el espacio de inventario."
    )


def _confidence(score: float, decision: Decision) -> float:
    """Map score distance from nearest threshold to a 0–1 confidence value."""
    if decision == "COMPRAR":
        distance = score - SCORE_BUY
        return round(min(0.5 + distance * 2.0, 1.0), 2)
    if decision == "NO_COMPRAR":
        distance = SCORE_ALTERNATIVE - score
        return round(min(0.5 + distance * 3.0, 1.0), 2)
    # USAR_ALTERNATIVA: confidence proportional to how close to the boundary
    mid = (SCORE_BUY + SCORE_ALTERNATIVE) / 2
    return round(max(0.40, 1.0 - abs(score - mid) * 4.0), 2)


def _find_alternative(row: pd.Series, df: pd.DataFrame) -> str | None:
    same_cat = df[
        (df["categoria"] == row["categoria"]) & (df["nombre"] != row["nombre"])
    ]
    if same_cat.empty:
        return None
    best = same_cat.loc[same_cat["score_rentabilidad"].idxmax()]
    return best["nombre"]


def generate_recommendations(df: pd.DataFrame) -> list[Recommendation]:
    df = compute_metrics(df)
    df = compute_composite_score(df)

    recommendations: list[Recommendation] = []

    for _, row in df.iterrows():
        score = row["score_rentabilidad"]

        if score >= SCORE_BUY:
            decision: Decision = "COMPRAR"
        elif score >= SCORE_ALTERNATIVE:
            decision = "USAR_ALTERNATIVA"
        else:
            decision = "NO_COMPRAR"

        alternativa = None
        if decision in ("NO_COMPRAR", "USAR_ALTERNATIVA"):
            alternativa = _find_alternative(row, df)
            if alternativa and decision == "NO_COMPRAR":
                decision = "USAR_ALTERNATIVA"

        recommendations.append(
            Recommendation(
                nombre=row["nombre"],
                categoria=row["categoria"],
                decision=decision,
                confianza=_confidence(score, decision),
                razonamiento=_build_reasoning(row, decision),
                alternativa=alternativa,
            )
        )

    return sorted(recommendations, key=lambda r: r.decision)


def recommendations_to_df(recs: list[Recommendation]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "nombre": r.nombre,
                "categoria": r.categoria,
                "decision": r.decision,
                "confianza": r.confianza,
                "alternativa": r.alternativa or "-",
                "razonamiento": r.razonamiento,
            }
            for r in recs
        ]
    )
