import pytest
import pandas as pd
from src.analysis.segmentation import segment_products, segment_summary


@pytest.fixture
def df_4():
    return pd.DataFrame({
        "nombre": ["A", "B", "C", "D"],
        "categoria": ["X", "X", "Y", "Y"],
        "precio_compra": [1.0, 2.0, 5.0, 3.0],
        "precio_venta": [2.0, 3.5, 9.0, 4.5],
        "unidades_vendidas_mes": [100, 50, 10, 80],
    })


# ---------------------------------------------------------------------------
# Gap tests
# ---------------------------------------------------------------------------

def test_gap3_fewer_than_4_products_clear_error():
    """Con < 4 productos KMeans falla, pero con el mensaje de sklearn, no el nuestro.
    Al corregir el gap, segment_products debe lanzar ValueError con mensaje en español
    antes de llegar a KMeans."""
    df = pd.DataFrame({
        "nombre": ["A", "B", "C"],
        "categoria": ["X", "X", "Y"],
        "precio_compra": [1.0, 2.0, 3.0],
        "precio_venta": [2.0, 3.0, 5.0],
        "unidades_vendidas_mes": [10, 20, 30],
    })
    with pytest.raises(ValueError, match="al menos 4 productos"):
        segment_products(df)


def test_gap4_identical_products_should_warn():
    """Cuando todos los productos tienen las mismas métricas, StandardScaler produce
    varianza cero. El módulo debería advertirlo. Actualmente no emite ninguna advertencia."""
    df = pd.DataFrame({
        "nombre": ["A", "B", "C", "D"],
        "categoria": ["X", "X", "Y", "Y"],
        "precio_compra": [1.0, 1.0, 1.0, 1.0],
        "precio_venta": [2.0, 2.0, 2.0, 2.0],
        "unidades_vendidas_mes": [10, 10, 10, 10],
    })
    with pytest.warns(UserWarning, match="varianza cero|identical|std"):
        segment_products(df)


def test_gap5_estrella_label_assigned_by_centroid_score_not_explicit_thresholds():
    """Gap documentado (segmentacion.md): la etiqueta Estrella se asigna al cluster
    con mayor score de centroide (media de features normalizadas), no por umbrales
    explícitos de margen y rotación.

    Con este dataset, AltaRotBajoMargen (10% de margen) recibe la etiqueta Estrella
    porque su beneficio mensual absoluto y rotación dominan el score de centroide,
    desplazando a BajaRotAltoMargen (400% de margen pero apenas 5 unidades/mes).
    Este es el comportamiento actual — puede sorprender al usuario de negocio.
    """
    df = pd.DataFrame({
        "nombre": ["AltaRotBajoMargen", "BajaRotAltoMargen", "Medio1", "Medio2"],
        "categoria": ["A", "B", "C", "D"],
        "precio_compra": [1.00, 5.00, 2.0, 3.0],
        "precio_venta": [1.10, 25.0, 3.5, 5.0],
        "unidades_vendidas_mes": [10000, 5, 100, 80],
    })
    result = segment_products(df)
    estrella = result[result["segmento"] == "Estrella"].iloc[0]
    # Alta rotación con margen bajo gana sobre alto margen con baja rotación,
    # porque beneficio_mensual (peso dominante) y unidades favorecen al primero.
    assert estrella["nombre"] == "AltaRotBajoMargen"
    assert estrella["margen_pct"] < 15  # el "Estrella" tiene margen porcentual bajo
