import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.agents.data_agent import DataAgent
from src.agents.analysis_agent import AnalysisAgent
from src.agents.report_agent import ReportAgent
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


def _csv_file(content: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8")
    tmp.write(content)
    tmp.flush()
    return Path(tmp.name)


@pytest.fixture
def csv_valido() -> Path:
    path = _csv_file(VALID_CSV)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def df_limpio(csv_valido) -> pd.DataFrame:
    result = DataAgent().run(csv_valido)
    return result.data["df"]


@pytest.fixture
def analysis_data(df_limpio):
    return AnalysisAgent().run(df_limpio)


# ── DataAgent ─────────────────────────────────────────────────────────────────

class TestDataAgent:
    def test_exito_con_csv_valido(self, csv_valido):
        result = DataAgent().run(csv_valido)
        assert result.success
        assert result.error is None

    def test_devuelve_dataframe(self, csv_valido):
        result = DataAgent().run(csv_valido)
        assert isinstance(result.data["df"], pd.DataFrame)
        assert len(result.data["df"]) == 5

    def test_metadata_correcta(self, csv_valido):
        result = DataAgent().run(csv_valido)
        assert result.data["filas"] == 5
        assert "nombre" in result.data["columnas"]

    def test_falla_con_archivo_inexistente(self):
        result = DataAgent().run(Path("no_existe.csv"))
        assert result.failed
        assert result.error is not None

    def test_falla_con_csv_sin_columnas(self):
        path = _csv_file("nombre,precio_compra\nA,10\n")
        try:
            result = DataAgent().run(path)
            assert result.failed
        finally:
            path.unlink(missing_ok=True)

    def test_mide_duracion(self, csv_valido):
        result = DataAgent().run(csv_valido)
        assert result.duration_ms > 0


# ── AnalysisAgent ─────────────────────────────────────────────────────────────

class TestAnalysisAgent:
    def test_exito_con_df_valido(self, df_limpio):
        result = AnalysisAgent().run(df_limpio)
        assert result.success
        assert result.error is None

    def test_devuelve_df_ranked(self, df_limpio):
        result = AnalysisAgent().run(df_limpio)
        assert "score_rentabilidad" in result.data["df_ranked"].columns

    def test_devuelve_df_segmentado(self, df_limpio):
        result = AnalysisAgent().run(df_limpio)
        assert "segmento" in result.data["df_segmented"].columns

    def test_score_rango_valido(self, df_limpio):
        result = AnalysisAgent().run(df_limpio)
        assert 0.0 <= result.data["score_min"] <= result.data["score_max"] <= 1.0

    def test_falla_con_menos_de_4_productos(self):
        df_poco = pd.DataFrame({
            "nombre": ["A", "B", "C"],
            "precio_compra": [10.0, 20.0, 5.0],
            "precio_venta": [15.0, 25.0, 8.0],
            "unidades_vendidas_mes": [100, 50, 200],
            "categoria": ["Cat", "Cat", "Cat"],
        })
        result = AnalysisAgent().run(df_poco)
        assert result.failed

    def test_mide_duracion(self, df_limpio):
        result = AnalysisAgent().run(df_limpio)
        assert result.duration_ms > 0


# ── ReportAgent ───────────────────────────────────────────────────────────────

class TestReportAgent:
    def test_exito_con_datos_validos(self, analysis_data):
        result = ReportAgent().run(
            df_ranked=analysis_data.data["df_ranked"],
            df_segmented=analysis_data.data["df_segmented"],
            segment_summary=analysis_data.data["segment_summary"],
        )
        assert result.success

    def test_recomendaciones_tienen_campos_requeridos(self, analysis_data):
        result = ReportAgent().run(
            df_ranked=analysis_data.data["df_ranked"],
            df_segmented=analysis_data.data["df_segmented"],
            segment_summary=analysis_data.data["segment_summary"],
        )
        for rec in result.data["recomendaciones"]:
            for campo in ("nombre", "categoria", "decision", "confianza", "razonamiento"):
                assert campo in rec

    def test_decisiones_validas(self, analysis_data):
        result = ReportAgent().run(
            df_ranked=analysis_data.data["df_ranked"],
            df_segmented=analysis_data.data["df_segmented"],
            segment_summary=analysis_data.data["segment_summary"],
        )
        validas = {"COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA"}
        for rec in result.data["recomendaciones"]:
            assert rec["decision"] in validas

    def test_conteo_suma_total(self, analysis_data):
        result = ReportAgent().run(
            df_ranked=analysis_data.data["df_ranked"],
            df_segmented=analysis_data.data["df_segmented"],
            segment_summary=analysis_data.data["segment_summary"],
        )
        conteo = result.data["conteo_decisiones"]
        assert sum(conteo.values()) == result.data["total_productos"]


# ── Orchestrator ──────────────────────────────────────────────────────────────

class TestOrchestrator:
    def test_pipeline_completo_exitoso(self, csv_valido):
        result = Orchestrator().run(csv_valido)
        assert result.success
        assert result.error is None

    def test_reporte_contiene_campos_esperados(self, csv_valido):
        result = Orchestrator().run(csv_valido)
        assert "recomendaciones" in result.reporte
        assert "resumen_segmentos" in result.reporte
        assert "metricas_pipeline" in result.reporte

    def test_pipeline_registra_3_agentes(self, csv_valido):
        result = Orchestrator().run(csv_valido)
        assert len(result.pipeline) == 3

    def test_tiempos_registrados_por_agente(self, csv_valido):
        result = Orchestrator().run(csv_valido)
        tiempos = result.reporte["metricas_pipeline"]["tiempos_ms"]
        assert "DataAgent" in tiempos
        assert "AnalysisAgent" in tiempos
        assert "ReportAgent" in tiempos

    def test_falla_en_data_agent_aborta_pipeline(self):
        result = Orchestrator().run(Path("inexistente.csv"))
        assert result.failed
        assert len(result.pipeline) == 1  # solo DataAgent corrió
        assert result.pipeline[0].agent == "DataAgent"

    def test_error_propagado_correctamente(self):
        result = Orchestrator().run(Path("inexistente.csv"))
        assert result.error is not None
        assert len(result.error) > 0

    def test_duracion_total_registrada(self, csv_valido):
        result = Orchestrator().run(csv_valido)
        assert result.duration_ms > 0
