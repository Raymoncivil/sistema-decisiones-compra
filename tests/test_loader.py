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


# ---------------------------------------------------------------------------
# Gap tests
# ---------------------------------------------------------------------------

def test_gap6_string_price_raises_clear_value_error(tmp_path):
    """Cuando precio_compra contiene texto, pandas lo lee como object dtype.
    La comparación <= 0 lanza TypeError. Al corregir el gap, debe lanzar
    ValueError con mención explícita del campo."""
    csv = tmp_path / "string_price.csv"
    csv.write_text(
        "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
        "X,abc,2.0,10,Cat\n"
    )
    with pytest.raises(ValueError, match="precio_compra"):
        load_products(csv)


def test_gap7_empty_csv_raises_value_error(tmp_path):
    """Un CSV con solo cabecera supera _validate (sin filas no hay nada que viole
    restricciones) y devuelve un DataFrame vacío. Los módulos de análisis fallarán
    después con mensajes poco informativos. Al corregir el gap debe lanzar ValueError."""
    csv = tmp_path / "empty.csv"
    csv.write_text("nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n")
    with pytest.raises(ValueError, match="no contiene filas|vacío|empty"):
        load_products(csv)


def test_gap8_semicolon_separator_raises_clear_error(tmp_path):
    """pandas lee el CSV como una sola columna larga (ej. 'nombre;precio_compra;...').
    La validación entonces lanza ValueError sobre columnas faltantes, ocultando
    la causa real. Al corregir el gap, el mensaje debe mencionar el separador."""
    csv = tmp_path / "semicolon.csv"
    csv.write_text(
        "nombre;precio_compra;precio_venta;unidades_vendidas_mes;categoria\n"
        "X;1.0;2.0;10;Cat\n"
    )
    with pytest.raises(ValueError, match="separador|delimiter|sep"):
        load_products(csv)
