import pandas as pd
import numpy as np
from pathlib import Path


REQUIRED_COLUMNS = {
    "nombre": str,
    "precio_compra": float,
    "precio_venta": float,
    "unidades_vendidas_mes": int,
    "categoria": str,
}


def load_products(path: str | Path) -> pd.DataFrame:
    """Load and validate the products CSV. Returns a clean DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    df = pd.read_csv(path)
    _validate(df)
    df = _clean(df)
    return df


def _validate(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Columnas requeridas faltantes: {missing}")

    nulls = df[list(REQUIRED_COLUMNS)].isnull().sum()
    if nulls.any():
        raise ValueError(f"Valores nulos detectados:\n{nulls[nulls > 0]}")

    if (df["precio_compra"] <= 0).any():
        raise ValueError("precio_compra debe ser > 0 en todas las filas")
    if (df["precio_venta"] <= 0).any():
        raise ValueError("precio_venta debe ser > 0 en todas las filas")
    if (df["unidades_vendidas_mes"] < 0).any():
        raise ValueError("unidades_vendidas_mes no puede ser negativo")

    negative_margin = df[df["precio_venta"] <= df["precio_compra"]]
    if not negative_margin.empty:
        names = negative_margin["nombre"].tolist()
        raise ValueError(f"Productos con margen <= 0 (precio_venta <= precio_compra): {names}")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["nombre"] = df["nombre"].str.strip()
    df["categoria"] = df["categoria"].str.strip()
    df["precio_compra"] = df["precio_compra"].round(4)
    df["precio_venta"] = df["precio_venta"].round(4)
    return df
