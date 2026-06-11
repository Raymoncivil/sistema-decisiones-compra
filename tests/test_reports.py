import tempfile
from pathlib import Path

import pytest

from src.reports import generate_pdf
from src.agents.orchestrator import Orchestrator

# ── fixtures ──────────────────────────────────────────────────────────────────

VALID_CSV = (
    "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
    "ProductoA,10.0,15.0,100,Electronica\n"
    "ProductoB,20.0,25.0,50,Electronica\n"
    "ProductoC,5.0,8.0,200,Ropa\n"
    "ProductoD,30.0,40.0,10,Ropa\n"
    "ProductoE,8.0,12.0,80,Electronica\n"
)

SAMPLE_REPORTE = {
    "total_productos": 5,
    "conteo_decisiones": {"COMPRAR": 2, "NO_COMPRAR": 1, "USAR_ALTERNATIVA": 2},
    "recomendaciones": [
        {
            "nombre": "ProductoA",
            "categoria": "Electronica",
            "decision": "COMPRAR",
            "score": 0.9,
            "confianza": 0.85,
            "razonamiento": "Alto margen y alta rotación.",
            "alternativa": None,
        },
        {
            "nombre": "ProductoB",
            "categoria": "Electronica",
            "decision": "USAR_ALTERNATIVA",
            "score": 0.5,
            "confianza": 0.60,
            "razonamiento": "Margen bajo respecto a sustitutos.",
            "alternativa": "ProductoX",
        },
        {
            "nombre": "ProductoC",
            "categoria": "Ropa",
            "decision": "NO_COMPRAR",
            "score": 0.2,
            "confianza": 0.75,
            "razonamiento": "Baja rotación y margen negativo.",
            "alternativa": None,
        },
        {
            "nombre": "ProductoD",
            "categoria": "Ropa",
            "decision": "COMPRAR",
            "score": 0.8,
            "confianza": 0.70,
            "razonamiento": "Buena rentabilidad histórica.",
            "alternativa": None,
        },
        {
            "nombre": "ProductoE",
            "categoria": "Electronica",
            "decision": "USAR_ALTERNATIVA",
            "score": 0.45,
            "confianza": 0.55,
            "razonamiento": "Existe sustituto más rentable.",
            "alternativa": "ProductoY",
        },
    ],
    "resumen_segmentos": [
        {
            "segmento": "Estrella",
            "productos": 2,
            "beneficio_mensual_total": 1200.0,
            "margen_pct_promedio": 40.0,
            "rotacion_promedio": 90.0,
        },
        {
            "segmento": "Vaca lechera",
            "productos": 1,
            "beneficio_mensual_total": 600.0,
            "margen_pct_promedio": 25.0,
            "rotacion_promedio": 50.0,
        },
        {
            "segmento": "Nicho",
            "productos": 1,
            "beneficio_mensual_total": 300.0,
            "margen_pct_promedio": 33.0,
            "rotacion_promedio": 80.0,
        },
        {
            "segmento": "Perro",
            "productos": 1,
            "beneficio_mensual_total": 60.0,
            "margen_pct_promedio": 10.0,
            "rotacion_promedio": 10.0,
        },
    ],
    "metricas_pipeline": {
        "archivo": "test.csv",
        "filas_cargadas": 5,
        "score_max": 0.9,
        "score_min": 0.2,
        "segmentos_encontrados": ["Estrella", "Vaca lechera", "Nicho", "Perro"],
        "tiempos_ms": {"DataAgent": 10.0, "AnalysisAgent": 50.0, "ReportAgent": 5.0},
    },
}


@pytest.fixture
def csv_valido() -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8")
    tmp.write(VALID_CSV)
    tmp.flush()
    tmp.close()  # Windows requires explicit close before unlink
    path = Path(tmp.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def reporte_real(csv_valido) -> dict:
    result = Orchestrator().run(csv_valido)
    assert result.success, f"pipeline falló: {result.error}"
    return result.reporte


# ── generate_pdf: interfaz básica ─────────────────────────────────────────────

class TestGeneratePdfBasic:
    def test_devuelve_bytes(self):
        pdf = generate_pdf(SAMPLE_REPORTE)
        assert isinstance(pdf, bytes)

    def test_bytes_no_vacios(self):
        pdf = generate_pdf(SAMPLE_REPORTE)
        assert len(pdf) > 0

    def test_comienza_con_firma_pdf(self):
        pdf = generate_pdf(SAMPLE_REPORTE)
        assert pdf[:4] == b"%PDF"

    def test_escribe_archivo_cuando_se_pasa_ruta(self, tmp_path):
        out = tmp_path / "reporte.pdf"
        generate_pdf(SAMPLE_REPORTE, output_path=out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_bytes_coinciden_con_archivo_escrito(self, tmp_path):
        out = tmp_path / "reporte.pdf"
        pdf_bytes = generate_pdf(SAMPLE_REPORTE, output_path=out)
        assert out.read_bytes() == pdf_bytes

    def test_crea_directorio_padre_si_no_existe(self, tmp_path):
        out = tmp_path / "subdir" / "nuevo" / "reporte.pdf"
        generate_pdf(SAMPLE_REPORTE, output_path=out)
        assert out.exists()

    def test_sin_ruta_no_crea_archivos(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        generate_pdf(SAMPLE_REPORTE)
        assert list(tmp_path.glob("*.pdf")) == []


# ── generate_pdf: contenido robusto ──────────────────────────────────────────

class TestGeneratePdfContenido:
    def test_sin_recomendaciones_no_falla(self):
        reporte = {**SAMPLE_REPORTE, "recomendaciones": []}
        pdf = generate_pdf(reporte)
        assert pdf[:4] == b"%PDF"

    def test_sin_segmentos_no_falla(self):
        reporte = {**SAMPLE_REPORTE, "resumen_segmentos": []}
        pdf = generate_pdf(reporte)
        assert pdf[:4] == b"%PDF"

    def test_sin_metricas_no_falla(self):
        reporte = {**SAMPLE_REPORTE, "metricas_pipeline": {}}
        pdf = generate_pdf(reporte)
        assert pdf[:4] == b"%PDF"

    def test_solo_comprar_no_falla(self):
        recs = [r for r in SAMPLE_REPORTE["recomendaciones"] if r["decision"] == "COMPRAR"]
        reporte = {**SAMPLE_REPORTE, "recomendaciones": recs}
        pdf = generate_pdf(reporte)
        assert pdf[:4] == b"%PDF"

    def test_solo_alternativa_no_falla(self):
        recs = [r for r in SAMPLE_REPORTE["recomendaciones"] if r["decision"] == "USAR_ALTERNATIVA"]
        reporte = {**SAMPLE_REPORTE, "recomendaciones": recs}
        pdf = generate_pdf(reporte)
        assert pdf[:4] == b"%PDF"

    def test_reporte_real_del_orquestador(self, reporte_real):
        pdf = generate_pdf(reporte_real)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000


# ── integración con Orchestrator ──────────────────────────────────────────────

class TestOrchestratorPdfIntegration:
    def test_orquestador_genera_pdf_con_pdf_output(self, csv_valido, tmp_path):
        out = tmp_path / "informe.pdf"
        result = Orchestrator().run(csv_valido, pdf_output=out)
        assert result.success
        assert out.exists()
        assert out.read_bytes()[:4] == b"%PDF"

    def test_orquestador_sin_pdf_output_no_crea_archivo(self, csv_valido, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = Orchestrator().run(csv_valido)
        assert result.success
        assert list(tmp_path.glob("*.pdf")) == []
