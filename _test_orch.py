import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(".")))

# ── Configuracion de logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d  %(levelname)-5s  [%(name)-15s]  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
for lib in ("sklearn", "matplotlib", "PIL", "urllib3"):
    logging.getLogger(lib).setLevel(logging.WARNING)

from src.agents.orchestrator import Orchestrator  # noqa: E402

SEP = "-" * 72
csv_path = Path("src/data/productos.csv")

t_inicio = time.perf_counter()
orch = Orchestrator()
result = orch.run(csv_path)
t_total = round((time.perf_counter() - t_inicio) * 1000, 2)

print()
print(SEP)

# Tiempos por subagente
print("  TIEMPOS POR SUBAGENTE")
print(SEP)
for r in result.pipeline:
    estado = "OK  " if r.success else "FAIL"
    bar_len = int(r.duration_ms / max(result.duration_ms, 1) * 30)
    bar = "#" * bar_len
    print(f"  [{estado}] {r.agent:<18} {r.duration_ms:>8.2f} ms  {bar}")
print(f"  {'':-<22}")
print(f"  {'TOTAL PIPELINE':<22} {result.duration_ms:>8.2f} ms")
print(f"  {'(wall-clock)':<22} {t_total:>8.2f} ms")

if not result.success:
    print()
    print(f"  ERROR: {result.error}")
    failed = result.failed_agent
    if failed:
        print(f"  Agente que fallo: {failed.agent}")
    sys.exit(1)

# Metricas del pipeline
m = result.reporte.get("metricas_pipeline", {})
print()
print(SEP)
print("  METRICAS DEL PIPELINE")
print(SEP)
print(f"  Archivo          : {m.get('archivo')}")
print(f"  Filas cargadas   : {m.get('filas_cargadas')}")
print(f"  Score max        : {m.get('score_max')}")
print(f"  Score min        : {m.get('score_min')}")
print(f"  Segmentos        : {', '.join(m.get('segmentos_encontrados', []))}")

# Distribucion de decisiones
recomendaciones = result.reporte.get("recomendaciones", [])
conteo = {}
for rec in recomendaciones:
    dec = rec.get("decision", "?")
    conteo[dec] = conteo.get(dec, 0) + 1

print()
print(SEP)
print("  DISTRIBUCION DE DECISIONES")
print(SEP)
for dec, n in sorted(conteo.items()):
    bar = "*" * n
    print(f"  {dec:<22} {n:>3} productos  {bar}")
print(f"  {'TOTAL':<22} {sum(conteo.values()):>3} productos")

# Top COMPRAR
print()
print(SEP)
print("  TOP COMPRAR  (mayor score)")
print(SEP)
comprar = [r for r in recomendaciones if r.get("decision") == "COMPRAR"]
comprar_sorted = sorted(comprar, key=lambda x: x.get("score", 0), reverse=True)[:5]
for i, rec in enumerate(comprar_sorted, 1):
    print(
        f"  {i}. {rec.get('nombre','?'):<26} "
        f"score={rec.get('score',0):.4f}  conf={rec.get('confianza','?')}"
    )

# Top NO_COMPRAR
no_comprar = [r for r in recomendaciones if r.get("decision") == "NO_COMPRAR"]
if no_comprar:
    print()
    print(SEP)
    print("  TOP NO_COMPRAR  (menor score)")
    print(SEP)
    no_sorted = sorted(no_comprar, key=lambda x: x.get("score", 0))[:5]
    for i, rec in enumerate(no_sorted, 1):
        print(
            f"  {i}. {rec.get('nombre','?'):<26} "
            f"score={rec.get('score',0):.4f}  conf={rec.get('confianza','?')}"
        )

print()
print(SEP)
print("  Pipeline completado con exito")
print(SEP)
