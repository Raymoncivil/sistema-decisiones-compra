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


class TestAnalizar:
    def test_respuesta_estructura_completa(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        assert resp.status_code == 200
        data = resp.json()
        assert "total_productos" in data
        assert "conteo_decisiones" in data
        assert "recomendaciones" in data
        assert "resumen_segmentos" in data
        assert "metricas_pipeline" in data

    def test_metricas_pipeline_campos(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        m = resp.json()["metricas_pipeline"]
        assert m["archivo"].endswith(".csv")
        assert m["filas_cargadas"] == 5
        assert 0.0 <= m["score_min"] <= m["score_max"] <= 1.0
        assert "DataAgent" in m["tiempos_ms"]
        assert "AnalysisAgent" in m["tiempos_ms"]
        assert "ReportAgent" in m["tiempos_ms"]

    def test_conteo_decisiones_suma_total(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        data = resp.json()
        assert sum(data["conteo_decisiones"].values()) == data["total_productos"]

    def test_total_productos_correcto(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        assert resp.json()["total_productos"] == 5

    def test_cada_recomendacion_tiene_campos_requeridos(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        for rec in resp.json()["recomendaciones"]:
            assert "nombre" in rec
            assert "categoria" in rec
            assert "decision" in rec
            assert "confianza" in rec
            assert "razonamiento" in rec
            assert "alternativa" in rec

    def test_decision_valores_validos(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        decisiones_validas = {"COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA"}
        for rec in resp.json()["recomendaciones"]:
            assert rec["decision"] in decisiones_validas

    def test_confianza_en_rango(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        for rec in resp.json()["recomendaciones"]:
            assert 0.0 <= rec["confianza"] <= 1.0

    def test_razonamiento_no_vacio(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        for rec in resp.json()["recomendaciones"]:
            assert len(rec["razonamiento"]) > 0

    def test_segmentos_esperados(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV)])
        segmentos = {s["segmento"] for s in resp.json()["resumen_segmentos"]}
        segmentos_validos = {"Estrella", "Vaca lechera", "Nicho", "Perro"}
        assert segmentos.issubset(segmentos_validos)

    def test_archivo_no_csv_devuelve_400(self):
        resp = client.post("/analizar", files=[_csv_file(VALID_CSV, filename="datos.txt")])
        assert resp.status_code == 400

    def test_csv_con_columnas_faltantes_devuelve_422(self):
        csv_malo = "nombre,precio_compra\nProductoA,10.0\n"
        resp = client.post("/analizar", files=[_csv_file(csv_malo)])
        assert resp.status_code == 422

    def test_csv_vacio_devuelve_422(self):
        csv_vacio = "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
        resp = client.post("/analizar", files=[_csv_file(csv_vacio)])
        assert resp.status_code == 422

    def test_menos_de_4_productos_devuelve_422(self):
        csv_pocos = (
            "nombre,precio_compra,precio_venta,unidades_vendidas_mes,categoria\n"
            "A,10.0,15.0,100,Cat\n"
            "B,20.0,25.0,50,Cat\n"
            "C,5.0,8.0,200,Cat\n"
        )
        resp = client.post("/analizar", files=[_csv_file(csv_pocos)])
        assert resp.status_code == 422

    def test_separador_punto_y_coma_devuelve_422(self):
        csv_semicolon = "nombre;precio_compra;precio_venta;unidades_vendidas_mes;categoria\nA;10;15;100;Cat\n"
        resp = client.post("/analizar", files=[_csv_file(csv_semicolon)])
        assert resp.status_code == 422
