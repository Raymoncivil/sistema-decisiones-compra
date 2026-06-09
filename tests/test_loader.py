import pytest
import pandas as pd
from pathlib import Path
from src.data.loader import load_products


DATA_PATH = Path(__file__).parent.parent / "src" / "data" / "productos.csv"


def test_load_returns_dataframe():
    df = load_products(DATA_PATH)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_required_columns_present():
    df = load_products(DATA_PATH)
    for col in ("nombre", "precio_compra", "precio_venta", "unidades_vendidas_mes", "categoria"):
        assert col in df.columns


def test_no_nulls():
    df = load_products(DATA_PATH)
    assert not df.isnull().any().any()


def test_positive_prices():
    df = load_products(DATA_PATH)
    assert (df["precio_compra"] > 0).all()
    assert (df["precio_venta"] > 0).all()


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_products("no_existe.csv")


def test_invalid_data_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\nX,-1.0,2.0,10,Cat\n")
    with pytest.raises(ValueError):
        load_products(bad_csv)
