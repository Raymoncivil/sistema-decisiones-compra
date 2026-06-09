# Skill: Análisis de Rentabilidad Completo

Ejecuta el pipeline de análisis de rentabilidad del proyecto, interpreta los resultados y los presenta en un formato estructurado y accionable.

---

## Cuándo usar esta skill

Cuando el usuario pida:
- "analiza la rentabilidad"
- "qué productos debo comprar"
- "ejecuta el análisis"
- "muéstrame el ranking de productos"
- "corre el pipeline completo"
- o cualquier variante que implique ejecutar el sistema sobre `src/data/productos.csv`

---

## Paso 1 — Verificar el entorno

Antes de ejecutar, confirmar que el entorno está listo:

```powershell
# Verificar que el venv existe y tiene las dependencias
.venv\Scripts\python.exe -c "import pandas, sklearn, numpy; print('OK')"
```

Si falla: ver sección **Errores comunes → E1**.

Verificar que el archivo de datos existe:

```powershell
Test-Path src\data\productos.csv
```

Si devuelve `False`: ver **Errores comunes → E2**.

---

## Paso 2 — Leer el archivo de datos antes de ejecutar

Siempre leer `src/data/productos.csv` antes de correr el análisis para:
- Conocer cuántos productos hay
- Detectar problemas evidentes (columnas faltantes, valores negativos)
- Contextualizar los resultados al presentarlos

Columnas esperadas: `nombre`, `precio_compra`, `precio_venta`, `unidades_vendidas_mes`, `categoria`

Si faltan columnas o hay valores negativos en precios: ver **Errores comunes → E3**.

---

## Paso 3 — Archivos clave a leer para tener contexto completo

Leer estos archivos si el usuario pregunta sobre cómo funciona el análisis o si hay resultados inesperados:

| Archivo | Propósito |
|---|---|
| `src/analysis/profitability.py` | Fórmulas de métricas y pesos del score |
| `src/recommendations/engine.py` | Umbrales de decisión (0.45 / 0.25) y lógica de confianza |
| `src/analysis/segmentation.py` | Configuración de KMeans (k=4, random_state=42) |
| `docs/specs/rentabilidad.md` | Spec formal del módulo de métricas |
| `docs/specs/recomendaciones.md` | Spec formal del motor de decisiones |
| `docs/specs/segmentacion.md` | Spec formal del módulo de segmentación |

---

## Paso 4 — Ejecutar el análisis

```powershell
.venv\Scripts\python.exe -m src.analysis.run_analysis
```

Si el entorno está activado:

```powershell
python -m src.analysis.run_analysis
```

El comando imprime cinco secciones en orden:
1. Ranking completo de rentabilidad
2. Top 5 productos más rentables
3. 3 productos menos rentables
4. Segmentación de productos (por producto)
5. Resumen por segmento

---

## Paso 5 — Formato para presentar resultados

Nunca copiar la salida cruda del terminal directamente. Reorganizar en este formato:

### Sección 1: Resumen ejecutivo

Una tabla con los productos que reciben cada decisión:

```
## Recomendaciones de compra

| Decisión          | Productos | Confianza media |
|-------------------|-----------|-----------------|
| COMPRAR           | N         | X.XX            |
| USAR_ALTERNATIVA  | N         | X.XX            |
| NO_COMPRAR        | N         | X.XX            |
```

### Sección 2: COMPRAR — detalle

Listar solo los campos accionables: nombre, categoría, beneficio mensual, margen %, score, confianza.

```
### Comprar (N productos)

| Producto | Categoría | Beneficio/mes | Margen % | Score | Confianza |
|----------|-----------|---------------|----------|-------|-----------|
| ...      | ...       | X.XX €        | X.X%     | 0.XXX | XX%       |
```

### Sección 3: USAR_ALTERNATIVA — detalle

Incluir la columna `Alternativa sugerida`:

```
### Usar alternativa (N productos)

| Producto | Categoría | Score | Alternativa sugerida | Confianza |
|----------|-----------|-------|----------------------|-----------|
```

### Sección 4: NO_COMPRAR — detalle

```
### No comprar (N productos)

| Producto | Categoría | Score | Confianza | Motivo resumen |
|----------|-----------|-------|-----------|----------------|
```

### Sección 5: Segmentos

```
### Segmentación de cartera

| Segmento     | Productos | Beneficio total/mes | Margen prom. | Rotación prom. |
|--------------|-----------|---------------------|--------------|----------------|
| Estrella     | N         | X.XX €              | X.X%         | XXX uds        |
| Vaca lechera | N         | X.XX €              | X.X%         | XXX uds        |
| Nicho        | N         | X.XX €              | X.X%         | XXX uds        |
| Perro        | N         | X.XX €              | X.X%         | XXX uds        |
```

### Sección 6: Observaciones destacadas

Señalar siempre:
- El producto con mayor score (y por cuánto supera al segundo)
- El segmento con mayor beneficio total
- Cualquier producto con confianza < 60% (zona de incertidumbre — el score está cerca de un umbral)
- Productos en USAR_ALTERNATIVA cuya alternativa sugerida también tiene score bajo (gap conocido de la spec)

---

## Errores comunes y cómo resolverlos

### E1 — ModuleNotFoundError al importar pandas / sklearn / numpy

```
ModuleNotFoundError: No module named 'pandas'
```

**Causa:** el venv no está activado o las dependencias no están instaladas.

**Solución:**
```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

Si el venv no existe:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### E2 — FileNotFoundError en productos.csv

```
FileNotFoundError: No se encontró el archivo: src\data\productos.csv
```

**Causa:** el archivo de datos no existe o está en otra ruta.

**Solución:** confirmar con el usuario dónde está el CSV y, si es necesario, pasarlo como argumento:

```python
from pathlib import Path
from src.analysis.run_analysis import run
run(data_path=Path("ruta/al/archivo.csv"))
```

---

### E3 — ValueError al validar columnas o valores

```
ValueError: Columnas requeridas faltantes: ['precio_compra']
ValueError: precio_compra debe ser > 0 en todas las filas
ValueError: Productos con margen <= 0: ['Producto X']
```

**Causa:** el CSV no cumple las restricciones del loader (`src/data/loader.py`).

**Diagnóstico:**
```python
import pandas as pd
df = pd.read_csv("src/data/productos.csv")
print(df.dtypes)
print(df.describe())
print(df[df["precio_venta"] <= df["precio_compra"]])
```

**Solución:** corregir el CSV — nunca modificar la validación del loader para saltarla.

---

### E4 — ValueError de KMeans: n_samples < n_clusters

```
ValueError: n_samples=3 should be >= n_clusters=4
```

**Causa:** el CSV tiene menos de 4 productos. KMeans requiere al menos tantas muestras como clusters (k=4).

**Solución:** añadir al menos 4 productos al CSV. No reducir k sin actualizar la spec y los tests.

---

### E5 — Resultados con NaN en roi_mensual

**Causa:** algún producto tiene `unidades_vendidas_mes = 0`. El ROI requiere dividir por `precio_compra × unidades`, que resulta en 0.

**Consecuencia:** `roi_mensual = NaN` o `inf`. El score compuesto no se ve afectado (no usa `roi_mensual`), pero el razonamiento del motor puede mostrar "rotación 0 uds/mes".

**Acción:** informar al usuario que el producto existe pero no tiene ventas registradas. No es un error — es un dato válido que indica stock sin movimiento.

---

### E6 — Resultados distintos al volver a ejecutar

**Causa:** el CSV cambió entre ejecuciones. Todos los scores son relativos al lote actual (MinMaxScaler y KMeans se recalibran en cada ejecución).

**Acción:** no comparar scores entre ejecuciones con datasets distintos. Comparar solo decisiones finales (COMPRAR / NO_COMPRAR / USAR_ALTERNATIVA).

---

## Restricciones importantes

- **Nunca modificar** `src/data/productos.csv` directamente — es dato histórico fuente.
- **Nunca reducir** los umbrales de decisión (0.45 / 0.25) sin actualizar `docs/specs/recomendaciones.md` y los tests.
- **Nunca cambiar** `random_state` de KMeans sin notificar al usuario que los segmentos cambiarán.
- Los scores **no son comparables** entre ejecuciones con datasets distintos.
- Las specs en `docs/specs/` son la fuente de verdad del comportamiento esperado — si el código y la spec difieren, es un bug.
