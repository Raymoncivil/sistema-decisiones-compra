"""Profitability analysis: computes per-product metrics and composite scores."""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add profitability columns to the product DataFrame."""
    df = df.copy()

    df["margen_unitario"] = (df["precio_venta"] - df["precio_compra"]).round(4)
    df["margen_pct"] = (df["margen_unitario"] / df["precio_compra"] * 100).round(2)
    df["beneficio_mensual"] = (df["margen_unitario"] * df["unidades_vendidas_mes"]).round(2)

    # ROI: monthly benefit relative to the capital invested per unit
    df["roi_mensual"] = (df["beneficio_mensual"] / (df["precio_compra"] * df["unidades_vendidas_mes"]) * 100).round(2)

    return df


def compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 0–1 composite profitability score combining:
      - beneficio_mensual  (50%) — absolute contribution to margin
      - margen_pct         (30%) — efficiency of each unit sold
      - unidades_vendidas_mes (20%) — rotation / demand signal
    """
    df = df.copy()
    scaler = MinMaxScaler()

    features = ["beneficio_mensual", "margen_pct", "unidades_vendidas_mes"]
    weights = [0.50, 0.30, 0.20]

    scaled = scaler.fit_transform(df[features])
    df["score_rentabilidad"] = np.dot(scaled, weights).round(4)

    return df


def rank_products(df: pd.DataFrame) -> pd.DataFrame:
    """Return products sorted by composite score descending, with rank column."""
    df = compute_metrics(df)
    df = compute_composite_score(df)
    df = df.sort_values("score_rentabilidad", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "ranking"
    return df


def top_n(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    ranked = rank_products(df)
    return ranked.head(n)


def bottom_n(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    ranked = rank_products(df)
    return ranked.tail(n).sort_values("score_rentabilidad")
