"""Tests for dashboard.api_client using respx to mock HTTP."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import respx
import httpx

from dashboard.api_client import APIClient, APIError

# ── fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_RESPONSE = {
    "reporte_id": "abc123",
    "total_productos": 3,
    "conteo_decisiones": {"COMPRAR": 2, "NO_COMPRAR": 1, "USAR_ALTERNATIVA": 0},
    "recomendaciones": [
        {
            "nombre": "ProdA",
            "categoria": "Elec",
            "decision": "COMPRAR",
            "confianza": 0.9,
            "razonamiento": "alto margen",
            "alternativa": None,
        }
    ],
    "resumen_segmentos": [
        {
            "segmento": "Estrella",
            "productos": 2,
            "beneficio_mensual_total": 800.0,
            "margen_pct_promedio": 35.0,
            "rotacion_promedio": 70.0,
        }
    ],
    "metricas_pipeline": {
        "archivo": "test.csv",
        "filas_cargadas": 3,
        "score_max": 0.9,
        "score_min": 0.3,
        "segmentos_encontrados": ["Estrella"],
        "tiempos_ms": {"DataAgent": 5.0},
    },
}

FAKE_PDF = b"%PDF-fake"

CSV_CONTENT = (
    "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
    "ProdA,10.0,15.0,100,Elec\n"
)


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    p = tmp_path / "test.csv"
    p.write_text(CSV_CONTENT, encoding="utf-8")
    return p


# ── analyze (from file path) ──────────────────────────────────────────────────

class TestAnalyze:
    @respx.mock
    def test_devuelve_dict_con_reporte_id(self, csv_file):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
        )
        with APIClient() as client:
            result = client.analyze(csv_file)
        assert result["reporte_id"] == "abc123"

    @respx.mock
    def test_total_productos_correcto(self, csv_file):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
        )
        with APIClient() as client:
            result = client.analyze(csv_file)
        assert result["total_productos"] == 3

    @respx.mock
    def test_error_400_lanza_api_error(self, csv_file):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(400, json={"detail": "El archivo debe ser un CSV."})
        )
        with APIClient() as client:
            with pytest.raises(APIError) as exc_info:
                client.analyze(csv_file)
        assert exc_info.value.status_code == 400

    @respx.mock
    def test_error_422_lanza_api_error(self, csv_file):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(422, json={"detail": "columnas inválidas"})
        )
        with APIClient() as client:
            with pytest.raises(APIError) as exc_info:
                client.analyze(csv_file)
        assert exc_info.value.status_code == 422

    @respx.mock
    def test_error_500_lanza_api_error(self, csv_file):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(500, json={"detail": "internal"})
        )
        with APIClient() as client:
            with pytest.raises(APIError) as exc_info:
                client.analyze(csv_file)
        assert exc_info.value.status_code == 500


# ── analyze_bytes ─────────────────────────────────────────────────────────────

class TestAnalyzeBytes:
    @respx.mock
    def test_acepta_bytes_y_devuelve_dict(self):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
        )
        with APIClient() as client:
            result = client.analyze_bytes(CSV_CONTENT.encode(), filename="datos.csv")
        assert "reporte_id" in result

    @respx.mock
    def test_conteo_decisiones_en_respuesta(self):
        respx.post("http://localhost:8000/analizar").mock(
            return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
        )
        with APIClient() as client:
            result = client.analyze_bytes(CSV_CONTENT.encode())
        assert result["conteo_decisiones"]["COMPRAR"] == 2


# ── download_pdf ──────────────────────────────────────────────────────────────

class TestDownloadPdf:
    @respx.mock
    def test_devuelve_bytes_pdf(self):
        respx.get("http://localhost:8000/reporte/abc123").mock(
            return_value=httpx.Response(200, content=FAKE_PDF, headers={"content-type": "application/pdf"})
        )
        with APIClient() as client:
            pdf = client.download_pdf("abc123")
        assert pdf == FAKE_PDF

    @respx.mock
    def test_comienza_con_firma_pdf(self):
        respx.get("http://localhost:8000/reporte/abc123").mock(
            return_value=httpx.Response(200, content=FAKE_PDF, headers={"content-type": "application/pdf"})
        )
        with APIClient() as client:
            pdf = client.download_pdf("abc123")
        assert pdf.startswith(b"%PDF")

    @respx.mock
    def test_404_lanza_api_error(self):
        respx.get("http://localhost:8000/reporte/no-existe").mock(
            return_value=httpx.Response(404, json={"detail": "Reporte no encontrado."})
        )
        with APIClient() as client:
            with pytest.raises(APIError) as exc_info:
                client.download_pdf("no-existe")
        assert exc_info.value.status_code == 404


# ── APIError ──────────────────────────────────────────────────────────────────

class TestAPIError:
    def test_mensaje_contiene_status_code(self):
        err = APIError(404, "not found")
        assert "404" in str(err)

    def test_atributos_accesibles(self):
        err = APIError(422, "bad data")
        assert err.status_code == 422
        assert err.detail == "bad data"


# ── base_url personalizable ───────────────────────────────────────────────────

class TestBaseUrl:
    @respx.mock
    def test_base_url_personalizado(self, csv_file):
        respx.post("http://mi-api:9000/analizar").mock(
            return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
        )
        with APIClient(base_url="http://mi-api:9000") as client:
            result = client.analyze(csv_file)
        assert result["reporte_id"] == "abc123"
