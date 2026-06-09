import pytest
import pandas as pd
from src.recommendations.engine import generate_recommendations, recommendations_to_df


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "nombre": ["Top", "Mid", "Low"],
            "categoria": ["A", "A", "B"],
            "precio_compra": [1.0, 2.0, 5.0],
            "precio_venta": [3.0, 3.5, 6.0],
            "unidades_vendidas_mes": [500, 50, 5],
        }
    )


def test_returns_one_rec_per_product(df):
    recs = generate_recommendations(df)
    assert len(recs) == len(df)


def test_all_decisions_are_valid(df):
    valid = {"COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA"}
    recs = generate_recommendations(df)
    assert all(r.decision in valid for r in recs)


def test_confidence_range(df):
    recs = generate_recommendations(df)
    assert all(0.0 <= r.confianza <= 1.0 for r in recs)


def test_reasoning_not_empty(df):
    recs = generate_recommendations(df)
    assert all(r.razonamiento for r in recs)


def test_to_dataframe_columns(df):
    recs = generate_recommendations(df)
    result = recommendations_to_df(recs)
    for col in ("nombre", "categoria", "decision", "confianza", "alternativa", "razonamiento"):
        assert col in result.columns
