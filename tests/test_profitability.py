import pytest
import pandas as pd
from src.analysis.profitability import compute_metrics, compute_composite_score, top_n, bottom_n


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "nombre": ["A", "B", "C"],
            "categoria": ["X", "X", "Y"],
            "precio_compra": [1.0, 2.0, 5.0],
            "precio_venta": [2.0, 3.0, 9.0],
            "unidades_vendidas_mes": [100, 50, 10],
        }
    )


def test_compute_metrics_columns(sample_df):
    result = compute_metrics(sample_df)
    assert {"margen_unitario", "margen_pct", "beneficio_mensual", "roi_mensual"}.issubset(result.columns)


def test_margen_unitario(sample_df):
    result = compute_metrics(sample_df)
    assert result.loc[0, "margen_unitario"] == pytest.approx(1.0)
    assert result.loc[1, "margen_unitario"] == pytest.approx(1.0)
    assert result.loc[2, "margen_unitario"] == pytest.approx(4.0)


def test_beneficio_mensual(sample_df):
    result = compute_metrics(sample_df)
    assert result.loc[0, "beneficio_mensual"] == pytest.approx(100.0)
    assert result.loc[1, "beneficio_mensual"] == pytest.approx(50.0)
    assert result.loc[2, "beneficio_mensual"] == pytest.approx(40.0)


def test_composite_score_range(sample_df):
    result = compute_metrics(sample_df)
    result = compute_composite_score(result)
    assert (result["score_rentabilidad"] >= 0).all()
    assert (result["score_rentabilidad"] <= 1).all()


def test_top_n_returns_n_rows(sample_df):
    assert len(top_n(sample_df, 2)) == 2


def test_bottom_n_returns_n_rows(sample_df):
    assert len(bottom_n(sample_df, 2)) == 2


def test_top_n_sorted_descending(sample_df):
    result = top_n(sample_df, 3)
    scores = result["score_rentabilidad"].tolist()
    assert scores == sorted(scores, reverse=True)
