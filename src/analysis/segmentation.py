"""Product segmentation by rotation, margin and profitability using KMeans."""

import warnings

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


SEGMENT_LABELS = {
    0: "Estrella",       # high rotation + high margin
    1: "Vaca lechera",   # high rotation + low margin
    2: "Nicho",          # low rotation + high margin
    3: "Perro",          # low rotation + low margin
}

_N_CLUSTERS = 4
_RANDOM_STATE = 42


def segment_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cluster products into 4 segments using rotation and margin.
    Returns df with added columns: cluster_id, segmento.
    """
    from src.analysis.profitability import compute_metrics

    if len(df) < _N_CLUSTERS:
        raise ValueError(
            f"Se requieren al menos {_N_CLUSTERS} productos para segmentar, "
            f"pero se recibieron {len(df)}."
        )

    df = compute_metrics(df.copy())

    feature_cols = ["unidades_vendidas_mes", "margen_pct", "beneficio_mensual"]
    features = df[feature_cols].values

    zero_var = [col for col, std in zip(feature_cols, features.std(axis=0)) if std == 0]
    if zero_var:
        warnings.warn(
            f"varianza cero detectada en features: {zero_var}. "
            "El clustering con productos idénticos produce resultados indeterminados.",
            UserWarning,
            stacklevel=2,
        )

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    km = KMeans(n_clusters=_N_CLUSTERS, random_state=_RANDOM_STATE, n_init="auto")
    df["cluster_id"] = km.fit_predict(scaled)

    # Map cluster IDs to semantic labels by sorting cluster centres
    # (high rotation + high margin → Estrella; low + low → Perro)
    centres = km.cluster_centers_
    # Score each centre: mean of normalised rotation + margin + profit
    centre_scores = centres.mean(axis=1)
    rank_order = np.argsort(centre_scores)[::-1]  # highest first

    label_map = {int(cluster): list(SEGMENT_LABELS.values())[i] for i, cluster in enumerate(rank_order)}
    df["segmento"] = df["cluster_id"].map(label_map)

    return df


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate stats per segment. Expects df already segmented (has 'segmento' column)."""
    if "segmento" not in df.columns:
        df = segment_products(df)
    return (
        df.groupby("segmento")
        .agg(
            productos=("nombre", "count"),
            beneficio_mensual_total=("beneficio_mensual", "sum"),
            margen_pct_promedio=("margen_pct", "mean"),
            rotacion_promedio=("unidades_vendidas_mes", "mean"),
        )
        .round(2)
        .sort_values("beneficio_mensual_total", ascending=False)
    )
