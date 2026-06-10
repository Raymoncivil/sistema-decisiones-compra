import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(".")))

from src.agents.orchestrator import Orchestrator

csv_path = Path("src/data/productos.csv")
print(f"=== Probando Orchestrator con: {csv_path} ===\n")

t_inicio = time.perf_counter()
orch = Orchestrator()
result = orch.run(csv_path)
t_total = round((time.perf_counter() - t_inicio) * 1000, 2)

# Tiempos por subagente
print("--- Tiempos por subagente ---")
for r in result.pipeline:
    estado = "OK" if r.success else "FAIL"
    print(f"  [{estado}] {r.agent:<20} {r.duration_ms:>8.2f} ms")
print(f"  {'TOTAL PIPELINE':<21} {result.duration_ms:>8.2f} ms")
print(f"  {'(wall-clock)':<21} {t_total:>8.2f} ms")
print()

if not result.success:
    print(f"ERROR: {result.error}")
    failed = result.failed_agent
    if failed:
        print(f"Agente que fallo: {failed.agent}")
    sys.exit(1)

# Metricas del pipeline
m = result.reporte.get("metricas_pipeline", {})
print("--- Metricas del pipeline ---")
print(f"  Archivo          : {m.get('archivo')}")
print(f"  Filas cargadas   : {m.get('filas_cargadas')}")
print(f"  Score max        : {m.get('score_max')}")
print(f"  Score min        : {m.get('score_min')}")
print(f"  Segmentos        : {m.get('segmentos_encontrados')}")

# Distribucion de decisiones
print()
recomendaciones = result.reporte.get("recomendaciones", [])
conteo = {}
for rec in recomendaciones:
    dec = rec.get("decision", "?")
    conteo[dec] = conteo.get(dec, 0) + 1
print("--- Distribucion de decisiones ---")
for dec, n in sorted(conteo.items()):
    print(f"  {dec:<25} {n:>4} productos")
print(f"  {'TOTAL':<25} {sum(conteo.values()):>4} productos")

# Top 5 COMPRAR
print()
print("--- Top 5 COMPRAR (mayor score) ---")
comprar = [r for r in recomendaciones if r.get("decision") == "COMPRAR"]
comprar_sorted = sorted(comprar, key=lambda x: x.get("score", 0), reverse=True)[:5]
for i, rec in enumerate(comprar_sorted, 1):
    print(f"  {i}. {rec.get('nombre','?'):<25}  score={rec.get('score',0):.4f}  conf={rec.get('confianza','?')}")

# Top 5 NO_COMPRAR
print()
print("--- Top 5 NO_COMPRAR (menor score) ---")
no_comprar = [r for r in recomendaciones if r.get("decision") == "NO_COMPRAR"]
no_sorted = sorted(no_comprar, key=lambda x: x.get("score", 0))[:5]
for i, rec in enumerate(no_sorted, 1):
    print(f"  {i}. {rec.get('nombre','?'):<25}  score={rec.get('score',0):.4f}  conf={rec.get('confianza','?')}")

print()
print("=== Pipeline completado con exito ===")
