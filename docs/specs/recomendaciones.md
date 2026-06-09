# Spec: Motor de Recomendaciones de Compra

**Versión:** 1.0  
**Fecha:** 2026-06-08  
**Módulo:** `src/recommendations/engine.py`  
**Dependencia directa:** `src/analysis/profitability.py`  
**Spec relacionada:** [rentabilidad.md](rentabilidad.md)

---

## 1. Propósito

Traducir el `score_rentabilidad` de cada producto en una decisión accionable de compra, acompañada de un razonamiento legible y un nivel de confianza cuantificado.

Este módulo **no calcula métricas** — las delega a `profitability.py`. Su única responsabilidad es clasificar, razonar y recomendar.

---

## 2. Entradas

### `generate_recommendations(df)` — entrada principal

Recibe el DataFrame crudo de productos (mismo formato que entrega `loader.load_products`). El motor aplica internamente `compute_metrics` y `compute_composite_score` antes de clasificar.

| Columna requerida        | Tipo    | Restricciones         |
|--------------------------|---------|-----------------------|
| `nombre`                 | `str`   | Único por producto    |
| `precio_compra`          | `float` | > 0                   |
| `precio_venta`           | `float` | > `precio_compra`     |
| `unidades_vendidas_mes`  | `int`   | >= 0                  |
| `categoria`              | `str`   | Permite repetidos     |

---

## 3. Salidas

### 3.1 `generate_recommendations(df)` → `list[Recommendation]`

Lista de objetos `Recommendation`, ordenada alfabéticamente por `decision` (COMPRAR → NO_COMPRAR → USAR_ALTERNATIVA).

```python
@dataclass
class Recommendation:
    nombre:       str
    categoria:    str
    decision:     Literal["COMPRAR", "NO_COMPRAR", "USAR_ALTERNATIVA"]
    confianza:    float        # 0.0 – 1.0
    razonamiento: str
    alternativa:  str | None   # None si no hay alternativa disponible
```

### 3.2 `recommendations_to_df(recs)` → `pd.DataFrame`

Convierte la lista en un DataFrame con columnas:

| Columna        | Tipo    | Notas                                      |
|----------------|---------|--------------------------------------------|
| `nombre`       | `str`   |                                            |
| `categoria`    | `str`   |                                            |
| `decision`     | `str`   | COMPRAR / NO_COMPRAR / USAR_ALTERNATIVA    |
| `confianza`    | `float` | 0.0 – 1.0                                  |
| `alternativa`  | `str`   | Nombre del producto o `"-"` si no hay      |
| `razonamiento` | `str`   | Texto legible en español                   |

---

## 4. Lógica de decisión

### 4.1 Umbrales

Los umbrales operan sobre `score_rentabilidad` (0–1, calculado por `profitability.compute_composite_score`):

| Constante          | Valor | Rol                                     |
|--------------------|-------|-----------------------------------------|
| `SCORE_BUY`        | 0.45  | Límite inferior para COMPRAR            |
| `SCORE_ALTERNATIVE`| 0.25  | Límite inferior para USAR_ALTERNATIVA   |

### 4.2 Árbol de decisión

```
score >= 0.45
    → COMPRAR

0.25 <= score < 0.45
    → USAR_ALTERNATIVA (provisional)

score < 0.25
    → NO_COMPRAR (provisional)
```

**Ajuste post-umbral para NO_COMPRAR:**
Si el score cae por debajo de `SCORE_ALTERNATIVE` (decisión inicial `NO_COMPRAR`) pero existe otro producto en la misma categoría, la decisión se promueve a `USAR_ALTERNATIVA` y se registra el nombre del producto alternativo.

Tabla de decisión final completa:

| Score inicial  | ¿Hay alternativa en categoría? | Decisión final    |
|----------------|-------------------------------|-------------------|
| >= 0.45        | (irrelevante)                 | COMPRAR           |
| [0.25, 0.45)   | sí                            | USAR_ALTERNATIVA  |
| [0.25, 0.45)   | no                            | USAR_ALTERNATIVA  |
| < 0.25         | sí                            | USAR_ALTERNATIVA  |
| < 0.25         | no                            | NO_COMPRAR        |

> **Consecuencia:** `NO_COMPRAR` solo se emite cuando el score es bajo **y** no existe ningún otro producto en la misma categoría.

---

## 5. Cálculo de confianza

La confianza expresa qué tan lejos está el score del umbral más cercano. Rango resultante: **0.0 – 1.0**.

### COMPRAR

```
distancia = score − SCORE_BUY          # siempre >= 0
confianza = min(0.5 + distancia × 2.0, 1.0)
```

| score | confianza |
|-------|-----------|
| 0.45  | 0.50      |
| 0.70  | 1.00      |
| 1.00  | 1.00      |

La confianza mínima en COMPRAR es **0.50** (en el umbral exacto). Llega a 1.0 con score ≥ 0.75.

### NO_COMPRAR

```
distancia = SCORE_ALTERNATIVE − score  # siempre >= 0
confianza = min(0.5 + distancia × 3.0, 1.0)
```

| score | confianza |
|-------|-----------|
| 0.25  | 0.50      |
| 0.08  | 1.00      |
| 0.00  | 1.00      |

La confianza mínima en NO_COMPRAR es **0.50**. Llega a 1.0 con score ≤ 0.08.

### USAR_ALTERNATIVA

```
mid = (SCORE_BUY + SCORE_ALTERNATIVE) / 2   # = 0.35
confianza = max(0.40, 1.0 − |score − mid| × 4.0)
```

| score | confianza |
|-------|-----------|
| 0.35  | 1.00      |
| 0.25  | 0.60      |
| 0.45  | 0.60      |
| 0.10  | 0.40      |

La confianza es **máxima en el punto medio** entre umbrales (0.35) y cae hacia los bordes. El mínimo absoluto es **0.40** (piso fijo).

---

## 6. Selección de alternativa

La función `_find_alternative(row, df)` busca un sustituto cuando la decisión es `NO_COMPRAR` o `USAR_ALTERNATIVA`.

**Algoritmo:**

1. Filtrar el DataFrame por `categoria == row["categoria"]` excluyendo el propio producto.
2. Si el subconjunto está vacío → devuelve `None` (sin alternativa).
3. Si no → devuelve el `nombre` del producto con el `score_rentabilidad` más alto en esa categoría.

**Reglas:**

- La alternativa siempre pertenece a la **misma categoría** que el producto evaluado.
- Si hay empate en score, `idxmax()` elige el primero que aparece en el DataFrame (determinístico pero dependiente del orden).
- Si la categoría tiene un solo producto, no hay alternativa posible → la decisión permanece `NO_COMPRAR`.

---

## 7. Razonamiento generado

El campo `razonamiento` es texto fijo en español construido a partir de las métricas del producto.

### COMPRAR
```
"Score {score:.2f} — beneficio mensual {beneficio:.2f} €, margen {margen:.1f}%, rotación {unidades} uds/mes."
```

### USAR_ALTERNATIVA
```
"Score medio ({score:.2f}): beneficio mensual {beneficio:.2f} €. Existe un producto en la misma categoría con mejor rentabilidad."
```

### NO_COMPRAR
```
"Score bajo ({score:.2f}): beneficio mensual {beneficio:.2f} €, rotación {unidades} uds/mes. No justifica el espacio de inventario."
```

---

## 8. Reglas de negocio

| # | Regla                                                                                                                         |
|---|-------------------------------------------------------------------------------------------------------------------------------|
| 1 | Los umbrales `SCORE_BUY` y `SCORE_ALTERNATIVE` son constantes en código. Cambiarlos requiere re-validar el comportamiento del motor con datos reales. |
| 2 | `SCORE_BUY` debe ser siempre mayor que `SCORE_ALTERNATIVE`. Si se invierten, el árbol de decisión colapsa.                  |
| 3 | La confianza **nunca supera 1.0** ni baja de 0.40 (USAR_ALTERNATIVA) o 0.50 (COMPRAR / NO_COMPRAR).                        |
| 4 | La alternativa sugerida puede tener cualquier score — incluyendo uno que también esté en zona `NO_COMPRAR`. El motor no filtra alternativas por umbral. |
| 5 | El orden de la lista devuelta es alfabético por decisión, no por score ni por confianza.                                     |
| 6 | El motor no modifica el DataFrame de entrada.                                                                                 |

---

## 9. Comportamiento en casos borde

| Caso                                          | Comportamiento                                                                 |
|-----------------------------------------------|--------------------------------------------------------------------------------|
| Todos los productos en la misma categoría     | El de mayor score recibe COMPRAR; los demás podrían recibir USAR_ALTERNATIVA apuntando al mejor |
| Un único producto en el sistema               | No hay alternativa posible; si score < 0.25 → NO_COMPRAR                      |
| Score exactamente igual al umbral (0.45 / 0.25) | Se aplica `>=`, por lo que 0.45 → COMPRAR y 0.25 → USAR_ALTERNATIVA         |
| Dos productos con el mismo score máximo en categoría | `idxmax()` selecciona el primero en índice del DataFrame                |
| `score_rentabilidad` = 1.0                    | COMPRAR con confianza = 1.0                                                    |
| `score_rentabilidad` = 0.0                    | NO_COMPRAR (si no hay alternativa) con confianza = min(0.5 + 0.25×3, 1.0) = 1.0 |

---

## 10. Interfaz pública

```python
from src.recommendations.engine import (
    generate_recommendations,   # list[Recommendation] — función principal
    recommendations_to_df,      # convierte la lista en DataFrame
    Recommendation,             # dataclass del resultado
    SCORE_BUY,                  # 0.45 — umbral comprar
    SCORE_ALTERNATIVE,          # 0.25 — umbral alternativa
)
```

---

## 11. Lo que este módulo NO hace

- No calcula scores ni métricas de rentabilidad (delegado a `profitability.py`).
- No persiste resultados ni escribe archivos.
- No valida los datos de entrada (delegado a `loader.py`).
- No busca alternativas fuera de la misma categoría.
- No considera precio, stock disponible ni datos externos para elegir la alternativa — solo usa el score.

---

## 12. Tests esperados

- [ ] Score >= 0.45 → decisión COMPRAR.
- [ ] Score en [0.25, 0.45) → decisión USAR_ALTERNATIVA.
- [ ] Score < 0.25 con alternativa en categoría → decisión USAR_ALTERNATIVA (no NO_COMPRAR).
- [ ] Score < 0.25 sin alternativa en categoría → decisión NO_COMPRAR.
- [ ] Confianza COMPRAR en umbral exacto (0.45) = 0.50.
- [ ] Confianza COMPRAR con score 0.70 = 1.00.
- [ ] Confianza NO_COMPRAR en umbral exacto (0.25) = 0.50.
- [ ] Confianza USAR_ALTERNATIVA máxima en score = 0.35.
- [ ] Confianza nunca supera 1.0 ni baja de 0.40.
- [ ] La alternativa sugerida pertenece siempre a la misma categoría.
- [ ] Con un solo producto en el sistema y score bajo → NO_COMPRAR, alternativa = None.
- [ ] El DataFrame original no se modifica.
- [ ] `recommendations_to_df` devuelve `"-"` (no `None`) cuando no hay alternativa.
