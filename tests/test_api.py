import io
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

VALID_CSV = (
    "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
    "ProductoA,10.0,15.0,100,Electronica\n"
    "ProductoB,20.0,25.0,50,Electronica\n"
    "ProductoC,5.0,8.0,200,Ropa\n"
    "ProductoD,30.0,40.0,10,Ropa\n"
    "ProductoE,8.0,12.0,80,Electronica\n"
)


def _csv_file(content: str, filename: str = "productos.csv"):
    return ("archivo", (filename, io.BytesIO(content.encode()), "text/csv"))


def _analizar_valido() -> dict:
    resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
    assert resp.status_code == 200
    return resp.json()


# ── POST /analizar ─────────────────────────────────────────────────────────────

class TestAnalizar:
    def test_respuesta_estructura_completa(self):
        data = _analizar_valido()
        assert "reporte_id" in data
        assert "total_productos" in data
        assert "conteo_decisiones" in data
        assert "recomendaciones" in data
        assert "resumen_segmentos" in data
        assert "metricas_pipeline" in data

    def test_reporte_id_es_uuid(self):
        import uuid
        data = _analizar_valido()
        uid = uuid.UUID(data["reporte_id"])  # raises if invalid
        assert str(uid) == data["reporte_id"]

    def test_metricas_pipeline_campos(self):
        m = _analizar_valido()["metricas_pipeline"]
        assert m["archivo"].endswith(".csv")
        assert m["filas_cargadas"] == 5
        assert 0.0 <= m["score_min"] <= m["score_max"] <= 1.0
        assert "DataAgent" in m["tiempos_ms"]
        assert "AnalysisAgent" in m["tiempos_ms"]
        assert "ReportAgent" in m["tiempos_ms"]

    def test_conteo_decisiones_suma_total(self):
        data = _analizar_valido()
        assert sum(data["conteo_decisiones"].values()) == data["total_productos"]

    def test_total_productos_correcto(self):
        assert _analizar_valido()["total_productos"] == 5

    def test_cada_recomendacion_tiene_campos_requeridos(self):
        for rec in _analizar_valido()["recomendaciones"]:
            for campo in ("nombre", "categoria", "decision", "confianza", "razonamiento", "alternativa"):
                assert campo in rec

    def test_decision_valores_validos(self):
        decisiones_validas = {"COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA"}
        for rec in _analizar_valido()["recomendaciones"]:
            assert rec["decision"] in decisiones_validas

    def test_confianza_en_rango(self):
        for rec in _analizar_valido()["recomendaciones"]:
            assert 0.0 <= rec["confianza"] <= 1.0

    def test_razonamiento_no_vacio(self):
        for rec in _analizar_valido()["recomendaciones"]:
            assert len(rec["razonamiento"]) > 0

    def test_segmentos_esperados(self):
        segmentos = {s["segmento"] for s in _analizar_valido()["resumen_segmentos"]}
        assert segmentos.issubset({"Estrella", "Vaca lechera", "Nicho", "Perro"})

    def test_archivo_no_csv_devuelve_400(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV, filename="datos.txt")])
        assert resp.status_code == 400

    def test_csv_con_columnas_faltantes_devuelve_422(self):
        resp = client.post("/analizar", files=[_csv_file("nombre,precio_compra\nProductoA,10.0\n")])
        assert resp.status_code == 422

    def test_csv_vacio_devuelve_422(self):
        csv_vacio = "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
        resp = client.post("/analizar", files=[_csv_file(csv_vacio)])
        assert resp.status_code == 422

    def test_menos_de_4_productos_devuelve_422(self):
        csv_pocos = (
            "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
            "A,10.0,15.0,100,Cat\nB,20.0,25.0,50,Cat\nC,5.0,8.0,200,Cat\n"
        )
        resp = client.post("/analizar", files=[_csv_file(csv_pocos)])
        assert resp.status_code == 422

    def test_separador_punto_y_coma_devuelve_422(self):
        csv_sc = "nombre;precio_compra;precio_venta;unidades_vendidas_mes;categoria\nA;10;15;100;Cat\n"
        resp = client.post("/analizar", files=[_csv_file(csv_sc)])
        assert resp.status_code == 422


# ── GET /reporte/{id} ─────────────────────────────────────────────────────────

class TestDescargarReporte:
    def test_descarga_pdf_valido(self):
        reporte_id = _analizar_valido()["reporte_id"]
        resp = client.get(f"/reporte/{reporte_id}")
        assert resp.status_code == 200

    def test_content_type_es_pdf(self):
        reporte_id = _analizar_valido()["reporte_id"]
        resp = client.get(f"/reporte/{reporte_id}")
        assert resp.headers["content-type"] == "application/pdf"

    def test_body_comienza_con_firma_pdf(self):
        reporte_id = _analizar_valido()["reporte_id"]
        resp = client.get(f"/reporte/{reporte_id}")
        assert resp.content[:4] == b"%PDF"

    def test_content_disposition_incluye_nombre(self):
        reporte_id = _analizar_valido()["reporte_id"]
        resp = client.get(f"/reporte/{reporte_id}")
        assert "reporte_" in resp.headers.get("content-disposition", "")

    def test_id_inexistente_devuelve_404(self):
        resp = client.get("/reporte/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_id_malformado_devuelve_404(self):
        resp = client.get("/reporte/no-existe")
        assert resp.status_code == 404
