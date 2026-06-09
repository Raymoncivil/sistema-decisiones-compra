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


# ---------------------------------------------------------------------------
# Gap tests
# ---------------------------------------------------------------------------

def test_gap2_alternative_may_point_to_low_score_product():
    """Gap documentado (recomendaciones.md): la alternativa sugerida no se filtra
    por umbral — puede apuntar a otro producto que también tiene score bajo."""
    df = pd.DataFrame({
        "nombre": ["Lider1", "Lider2", "Flojo", "FlojoPeor"],
        "categoria": ["A", "A", "B", "B"],
        "precio_compra": [1.0, 1.0, 5.0, 5.0],
        "precio_venta": [10.0, 9.0, 5.5, 5.3],
        "unidades_vendidas_mes": [1000, 900, 1, 1],
    })
    recs_df = recommendations_to_df(generate_recommendations(df))

    for nombre in ("Flojo", "FlojoPeor"):
        row = recs_df[recs_df["nombre"] == nombre].iloc[0]
        assert row["decision"] == "USAR_ALTERNATIVA"
        # La alternativa sugerida es el otro producto de categoría B,
        # que también tiene score muy bajo (debería ser NO_COMPRAR por su propio mérito).
        assert row["alternativa"] in ("Flojo", "FlojoPeor")
        assert row["alternativa"] != nombre
