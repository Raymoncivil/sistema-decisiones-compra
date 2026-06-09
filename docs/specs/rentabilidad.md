# Spec: Módulo de Análisis de Rentabilidad

**Versión:** 1.0  
**Fecha:** 2026-06-08  
**Módulo:** `src/analysis/profitability.py`  
**Dependencia de entrada:** `src/data/loader.py`

---

## 1. Propósito

Calcular métricas de rentabilidad por producto y producir un score compuesto normalizado (0–1) que permita comparar y ordenar productos independientemente de su escala de precio o volumen.

Este módulo **no toma decisiones de compra** — eso es responsabilidad de `src/recommendations/engine.py`. Su única responsabilidad es calcular y ordenar.

---

## 2. Entradas

### DataFrame de productos

El módulo recibe un `pd.DataFrame` ya validado y limpiado por `loader.load_products()`.

| Columna                  | Tipo    | Restricciones                          |
|--------------------------|---------|----------------------------------------|
| `nombre`                 | `str`   | Sin espacios al inicio/fin             |
| `precio_compra`          | `float` | > 0                                    |
| `precio_venta`           | `float` | > 0 y > `precio_compra`               |
| `unidades_vendidas_mes`  | `int`   | >= 0                                   |
| `categoria`              | `str`   | Sin espacios al inicio/fin             |

**Precondición:** ninguna columna requerida puede contener nulos. El módulo asume que la validación ya ocurrió en el loader — no re-valida.

---

## 3. Salidas

### 3.1 `compute_metrics(df)` → `pd.DataFrame`

Devuelve el mismo DataFrame con cuatro columnas adicionales:

| Columna nueva       | Tipo    | Precisión | Fórmula                                                                 |
|---------------------|---------|-----------|-------------------------------------------------------------------------|
| `margen_unitario`   | `float` | 4 dec.    | `precio_venta − precio_compra`                                         |
| `margen_pct`        | `float` | 2 dec.    | `margen_unitario / precio_compra × 100`                                |
| `beneficio_mensual` | `float` | 2 dec.    | `margen_unitario × unidades_vendidas_mes`                              |
| `roi_mensual`       | `float` | 2 dec.    | `beneficio_mensual / (precio_compra × unidades_vendidas_mes) × 100`   |

El DataFrame original **no se modifica** (se trabaja sobre una copia).

### 3.2 `compute_composite_score(df)` → `pd.DataFrame`

Requiere que el DataFrame ya tenga las columnas de `compute_metrics`. Añade:

| Columna nueva         | Tipo    | Rango | Descripción                        |
|-----------------------|---------|-------|------------------------------------|
| `score_rentabilidad`  | `float` | 0–1   | Score compuesto ponderado, 4 dec.  |

**Cálculo del score:**

1. Normalizar las tres features al rango [0, 1] usando `MinMaxScaler` (fit sobre el conjunto completo).
2. Aplicar pesos fijos:

   | Feature                  | Peso |
   |--------------------------|------|
   | `beneficio_mensual`      | 50%  |
   | `margen_pct`             | 30%  |
   | `unidades_vendidas_mes`  | 20%  |

3. `score = dot(scaled_features, weights)`

**Propiedad importante:** el score es relativo al lote actual. Si se agrega o elimina un producto, todos los scores cambian porque el scaler se recalibra.

### 3.3 `rank_products(df)` → `pd.DataFrame`

Ejecuta `compute_metrics` + `compute_composite_score` y devuelve el DataFrame ordenado por `score_rentabilidad` descendente.

- El índice resultante se renombra `ranking` y empieza en 1.
- El producto con mayor score tiene `ranking = 1`.

### 3.4 `top_n(df, n=5)` → `pd.DataFrame`

Devuelve los `n` productos con mayor `score_rentabilidad`. Internamente llama a `rank_products`.

### 3.5 `bottom_n(df, n=3)` → `pd.DataFrame`

Devuelve los `n` productos con menor `score_rentabilidad`, ordenados de menor a mayor score. Internamente llama a `rank_products`.

---

## 4. Reglas de negocio

| # | Regla                                                                                                                                          |
|---|------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | `precio_venta` debe ser **estrictamente mayor** que `precio_compra`. Margen cero o negativo es un error de datos, no una decisión de negocio. |
| 2 | `unidades_vendidas_mes = 0` es válido (producto sin rotación). El `roi_mensual` resultará en `NaN` o `inf` si el denominador es cero — el módulo no lo maneja; se asume saneamiento externo. |
| 3 | El score **no es comparable entre ejecuciones distintas** (depende del lote). Solo es válido para rankear dentro del mismo DataFrame.           |
| 4 | Los pesos del score (50/30/20) son fijos en código. Cambiarlos requiere modificar `compute_composite_score` y re-validar el modelo.            |
| 5 | El módulo nunca modifica el DataFrame original — siempre opera sobre `df.copy()`.                                                              |

---

## 5. Comportamiento en casos borde

| Caso                              | Comportamiento esperado                                          |
|-----------------------------------|------------------------------------------------------------------|
| Un solo producto en el DataFrame  | Score = 1.0 (único punto, scaler lo normaliza al máximo)        |
| Todos los productos con el mismo score compuesto | MinMaxScaler produce `NaN` o 0 — resultado indefinido, requiere manejo futuro |
| `unidades_vendidas_mes = 0`       | `beneficio_mensual = 0`, `roi_mensual = NaN` o `inf`           |
| DataFrame vacío                   | Comportamiento indefinido — el loader debe prevenir este caso    |

---

## 6. Interfaz pública

```python
from src.analysis.profitability import (
    compute_metrics,          # agrega columnas de métricas
    compute_composite_score,  # agrega score_rentabilidad
    rank_products,            # métricas + score + orden descendente
    top_n,                    # n primeros del ranking
    bottom_n,                 # n últimos del ranking
)
```

Todas las funciones reciben y devuelven `pd.DataFrame`. Ninguna tiene efectos secundarios (no escribe archivos, no imprime, no modifica estado global).

---

## 7. Lo que este módulo NO hace

- No toma decisiones de compra (eso es `engine.py`).
- No persiste resultados (no escribe CSV ni base de datos).
- No genera gráficos ni reportes.
- No valida los datos de entrada (eso es `loader.py`).
- No predice demanda futura.

---

## 8. Dependencias

| Dependencia         | Uso                                      |
|---------------------|------------------------------------------|
| `pandas`            | Manipulación de DataFrame                |
| `numpy`             | Producto punto para el score compuesto   |
| `sklearn.preprocessing.MinMaxScaler` | Normalización de features  |

---

## 9. Tests esperados

Los tests de este módulo deben cubrir:

- [ ] `compute_metrics` produce los cuatro campos con los valores correctos para un caso conocido.
- [ ] `margen_pct` y `roi_mensual` tienen la precisión decimal especificada.
- [ ] `compute_composite_score` devuelve scores en [0, 1].
- [ ] Con un solo producto, el score es 1.0.
- [ ] `rank_products` devuelve el índice `ranking` empezando en 1, ordenado descendente.
- [ ] `top_n` devuelve exactamente `n` filas.
- [ ] `bottom_n` devuelve exactamente `n` filas, ordenadas de menor a mayor score.
- [ ] El DataFrame original no se modifica tras llamar a cualquier función.
