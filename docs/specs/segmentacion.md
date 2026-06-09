# Spec: Módulo de Segmentación de Productos

**Versión:** 1.0  
**Fecha:** 2026-06-08  
**Módulo:** `src/analysis/segmentation.py`  
**Dependencia directa:** `src/analysis/profitability.compute_metrics`  
**Spec relacionada:** [rentabilidad.md](rentabilidad.md)

---

## 1. Propósito

Agrupar productos en cuatro segmentos de comportamiento comercial (Estrella, Vaca lechera, Nicho, Perro) usando KMeans sobre rotación, margen y beneficio mensual. Los segmentos permiten tomar decisiones estratégicas de cartera más allá del ranking individual de rentabilidad.

Este módulo **no recomienda comprar ni descartar** productos — eso es responsabilidad de `engine.py`. Su responsabilidad es clasificar por comportamiento.

---

## 2. Entradas

### `segment_products(df)` y `segment_summary(df)`

Ambas funciones reciben el DataFrame crudo de productos (mismo formato que entrega `loader.load_products`). Internamente llaman a `compute_metrics` — no requieren que las columnas de métricas ya existan.

| Columna requerida        | Tipo    | Restricciones        |
|--------------------------|---------|----------------------|
| `nombre`                 | `str`   |                      |
| `precio_compra`          | `float` | > 0                  |
| `precio_venta`           | `float` | > `precio_compra`    |
| `unidades_vendidas_mes`  | `int`   | >= 0                 |
| `categoria`              | `str`   |                      |

---

## 3. Salidas

### 3.1 `segment_products(df)` → `pd.DataFrame`

Devuelve el DataFrame con todas las columnas de `compute_metrics` más dos columnas adicionales:

| Columna nueva  | Tipo    | Valores posibles                                 |
|----------------|---------|--------------------------------------------------|
| `cluster_id`   | `int`   | 0, 1, 2, 3 — ID interno del cluster KMeans      |
| `segmento`     | `str`   | Estrella / Vaca lechera / Nicho / Perro          |

El DataFrame original no se modifica (se trabaja sobre `df.copy()`).

### 3.2 `segment_summary(df)` → `pd.DataFrame`

Tabla agregada por segmento, ordenada por `beneficio_mensual_total` descendente:

| Columna                      | Tipo    | Descripción                            |
|------------------------------|---------|----------------------------------------|
| `segmento`                   | `str`   | Índice del DataFrame resultante        |
| `productos`                  | `int`   | Cantidad de productos en el segmento   |
| `beneficio_mensual_total`    | `float` | Suma de `beneficio_mensual`, 2 dec.    |
| `margen_pct_promedio`        | `float` | Media de `margen_pct`, 2 dec.          |
| `rotacion_promedio`          | `float` | Media de `unidades_vendidas_mes`, 2 dec.|

---

## 4. Algoritmo de segmentación

### 4.1 Features usadas

| Feature                  | Fuente                  |
|--------------------------|-------------------------|
| `unidades_vendidas_mes`  | Columna original        |
| `margen_pct`             | `compute_metrics`       |
| `beneficio_mensual`      | `compute_metrics`       |

### 4.2 Preprocesamiento

Las tres features se escalan con `StandardScaler` (media 0, desviación estándar 1) antes de entrenar KMeans. El scaler se ajusta sobre el conjunto completo — no hay separación train/test.

### 4.3 KMeans

| Parámetro       | Valor  | Motivo                                    |
|-----------------|--------|-------------------------------------------|
| `n_clusters`    | 4      | Corresponde a los 4 segmentos de negocio  |
| `random_state`  | 42     | Reproducibilidad                          |
| `n_init`        | "auto" | Valor por defecto de sklearn >= 1.2       |

### 4.4 Asignación de etiquetas semánticas

Los IDs de cluster que devuelve KMeans (0–3) no tienen orden semántico garantizado — varían según los datos. El módulo los reordena así:

1. Calcular la media de las tres coordenadas del centroide en espacio normalizado para cada cluster.
2. Ordenar clusters de mayor a menor media (`np.argsort(centre_scores)[::-1]`).
3. Asignar etiquetas en ese orden:

| Posición por score de centroide | Etiqueta asignada |
|---------------------------------|-------------------|
| 1° (mayor score compuesto)      | Estrella          |
| 2°                              | Vaca lechera      |
| 3°                              | Nicho             |
| 4° (menor score compuesto)      | Perro             |

**Interpretación de negocio de las etiquetas:**

| Segmento      | Perfil esperado                        |
|---------------|----------------------------------------|
| Estrella      | Alta rotación + alto margen            |
| Vaca lechera  | Alta rotación + bajo margen            |
| Nicho         | Baja rotación + alto margen            |
| Perro         | Baja rotación + bajo margen            |

> **Advertencia:** la asignación semántica se basa en el score medio del centroide, no en umbrales explícitos de margen o rotación. Con datasets pequeños o atípicos, un cluster etiquetado "Estrella" podría no tener realmente alta rotación Y alto margen — podría reflejar solo uno de los dos atributos. Las etiquetas son aproximaciones, no garantías.

---

## 5. Reglas de negocio

| # | Regla                                                                                                                           |
|---|---------------------------------------------------------------------------------------------------------------------------------|
| 1 | El número de clusters es fijo en 4. Cambiarlo implica redefinir `SEGMENT_LABELS` y revalidar la asignación semántica.         |
| 2 | Los segmentos son **relativos al lote actual**. Añadir o quitar productos puede reasignar productos a segmentos distintos.     |
| 3 | `random_state=42` garantiza reproducibilidad para el mismo dataset. Datasets distintos pueden producir asignaciones distintas. |
| 4 | El módulo no distingue por `categoria` — todos los productos compiten en el mismo espacio de clustering.                       |
| 5 | `cluster_id` es un detalle de implementación interno. Solo `segmento` debe usarse en capas superiores.                        |
| 6 | El módulo no modifica el DataFrame de entrada.                                                                                  |

---

## 6. Comportamiento en casos borde

| Caso                                        | Comportamiento                                                                                  |
|---------------------------------------------|-------------------------------------------------------------------------------------------------|
| Menos de 4 productos                        | KMeans falla (`n_samples < n_clusters`) — el módulo no maneja este error                       |
| Exactamente 4 productos                     | Cada producto queda en su propio cluster; la asignación semántica es válida pero poco significativa |
| Todos los productos con los mismos valores  | StandardScaler produce NaN (división por cero en std=0) — resultado indefinido                 |
| Un producto con `unidades_vendidas_mes = 0` | Feature válida, contribuye al centroide con valor 0                                             |
| Empate en score de centroide                | `np.argsort` es estable — el orden de desempate depende del índice original del array          |

---

## 7. Interfaz pública

```python
from src.analysis.segmentation import (
    segment_products,   # DataFrame con cluster_id y segmento por producto
    segment_summary,    # DataFrame agregado por segmento
    SEGMENT_LABELS,     # dict {0: "Estrella", 1: "Vaca lechera", ...}
)
```

`SEGMENT_LABELS` define el orden canónico de las etiquetas. Si se modifica, la asignación semántica cambia.

---

## 8. Lo que este módulo NO hace

- No recomienda comprar ni descartar productos (delegado a `engine.py`).
- No persiste el modelo KMeans entrenado (se re-entrena en cada llamada).
- No valida que los datos de entrada sean correctos (delegado a `loader.py`).
- No separa el espacio de clustering por categoría.
- No elige automáticamente el número óptimo de clusters (k=4 es fijo).
- No expone los centroides ni el scaler para uso externo.

---

## 9. Gaps conocidos

| Gap | Impacto | Sugerencia |
|-----|---------|------------|
| Falla con < 4 productos sin mensaje de error claro | Error de sklearn poco legible para el usuario | Validar `len(df) >= n_clusters` al inicio de `segment_products` |
| Todos los productos con std=0 en alguna feature produce NaN en StandardScaler | Resultado silenciosamente incorrecto | Detectar features con varianza cero antes de escalar |
| Etiquetas semánticas no garantizadas para datasets pequeños o atípicos | Un "Estrella" puede no serlo realmente | Documentar limitación en el reporte o añadir validación post-clustering |
| Modelo no persiste — se re-entrena en cada llamada | Ineficiencia y resultados distintos si los datos cambian | Considerar serialización del modelo para producción |

---

## 10. Tests esperados

- [ ] Con dataset válido de >= 4 productos, devuelve exactamente 4 segmentos distintos.
- [ ] Cada producto recibe exactamente uno de: Estrella, Vaca lechera, Nicho, Perro.
- [ ] El DataFrame original no se modifica tras llamar a `segment_products`.
- [ ] `segment_summary` devuelve exactamente 4 filas (una por segmento presente).
- [ ] `segment_summary` está ordenado por `beneficio_mensual_total` descendente.
- [ ] Llamadas consecutivas con el mismo DataFrame producen el mismo resultado (reproducibilidad).
- [ ] Con < 4 productos, el módulo lanza una excepción (test de fallo esperado).
- [ ] Las columnas `cluster_id` y `segmento` están presentes en la salida de `segment_products`.
- [ ] `segment_summary` incluye exactamente las columnas: `productos`, `beneficio_mensual_total`, `margen_pct_promedio`, `rotacion_promedio`.
