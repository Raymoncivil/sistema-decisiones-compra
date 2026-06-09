# Spec: Módulo de Carga y Validación de Datos

**Versión:** 1.0  
**Fecha:** 2026-06-08  
**Módulo:** `src/data/loader.py`  
**Spec relacionada:** [rentabilidad.md](rentabilidad.md)

---

## 1. Propósito

Cargar el CSV de productos, validar que cumple las restricciones de negocio y devolver un DataFrame limpio listo para análisis. Es la única puerta de entrada de datos al sistema — ningún otro módulo lee ficheros directamente.

---

## 2. Interfaz pública

```python
from src.data.loader import load_products, REQUIRED_COLUMNS

df = load_products("src/data/productos.csv")
```

`REQUIRED_COLUMNS` es el único símbolo exportable además de `load_products`. Contiene el esquema esperado del CSV.

---

## 3. Entrada

Un archivo CSV con al menos las siguientes columnas (pueden existir columnas adicionales, que se ignoran):

| Columna                 | Tipo esperado | Restricciones de negocio              |
|-------------------------|---------------|---------------------------------------|
| `nombre`                | `str`         | Sin restricción de unicidad en loader |
| `precio_compra`         | `float`       | > 0 en todas las filas                |
| `precio_venta`          | `float`       | > 0 y > `precio_compra` en todas las filas |
| `unidades_vendidas_mes` | `int`         | >= 0 en todas las filas               |
| `categoria`             | `str`         | Sin restricción de valores            |

El archivo debe existir en la ruta indicada. El separador es coma (`,`). La codificación la gestiona `pd.read_csv` con sus defaults (UTF-8 con fallback).

---

## 4. Salida

`load_products(path)` → `pd.DataFrame` limpio con exactamente las columnas del CSV original (sin añadir ni eliminar columnas).

Transformaciones aplicadas por `_clean`:

| Columna                 | Transformación                       |
|-------------------------|--------------------------------------|
| `nombre`                | `.str.strip()` — elimina espacios al inicio y fin |
| `categoria`             | `.str.strip()` — elimina espacios al inicio y fin |
| `precio_compra`         | `.round(4)` — 4 decimales            |
| `precio_venta`          | `.round(4)` — 4 decimales            |
| `unidades_vendidas_mes` | Sin transformación                   |

El DataFrame original del CSV no se modifica (se trabaja sobre copia implícita de pandas).

---

## 5. Flujo de ejecución

```
load_products(path)
  │
  ├─ Path(path).exists() ?
  │     No  → FileNotFoundError
  │
  ├─ pd.read_csv(path)
  │
  ├─ _validate(df)
  │     ├─ columnas requeridas presentes ?
  │     │     No  → ValueError: "Columnas requeridas faltantes: [...]"
  │     ├─ nulos en columnas requeridas ?
  │     │     Sí  → ValueError: "Valores nulos detectados:\n..."
  │     ├─ precio_compra > 0 en todas las filas ?
  │     │     No  → ValueError: "precio_compra debe ser > 0 en todas las filas"
  │     ├─ precio_venta > 0 en todas las filas ?
  │     │     No  → ValueError: "precio_venta debe ser > 0 en todas las filas"
  │     ├─ unidades_vendidas_mes >= 0 en todas las filas ?
  │     │     No  → ValueError: "unidades_vendidas_mes no puede ser negativo"
  │     └─ precio_venta > precio_compra en todas las filas ?
  │           No  → ValueError: "Productos con margen <= 0: [nombres]"
  │
  └─ _clean(df)  →  DataFrame limpio
```

La validación es **fail-fast**: lanza en la primera regla que falla, no acumula todos los errores.

---

## 6. Errores y mensajes exactos

| Condición                                      | Excepción          | Mensaje                                                        |
|------------------------------------------------|--------------------|----------------------------------------------------------------|
| Archivo no encontrado                          | `FileNotFoundError`| `"No se encontró el archivo: {path}"`                         |
| Columnas requeridas ausentes                   | `ValueError`       | `"Columnas requeridas faltantes: {lista}"`                    |
| Nulos en columnas requeridas                   | `ValueError`       | `"Valores nulos detectados:\n{serie con conteos}"`            |
| `precio_compra` <= 0 en alguna fila            | `ValueError`       | `"precio_compra debe ser > 0 en todas las filas"`             |
| `precio_venta` <= 0 en alguna fila             | `ValueError`       | `"precio_venta debe ser > 0 en todas las filas"`              |
| `unidades_vendidas_mes` < 0 en alguna fila     | `ValueError`       | `"unidades_vendidas_mes no puede ser negativo"`               |
| `precio_venta` <= `precio_compra` en alguna fila | `ValueError`     | `"Productos con margen <= 0 (precio_venta <= precio_compra): {nombres}"` |

---

## 7. Reglas de negocio

| # | Regla |
|---|-------|
| 1 | El loader es la única función del sistema que lee ficheros. Ningún otro módulo debe llamar a `pd.read_csv` directamente. |
| 2 | Los datos originales nunca se modifican. Las transformaciones de limpieza producen un DataFrame nuevo. |
| 3 | Un CSV con columnas adicionales no esperadas es válido — se cargan y pasan al análisis sin error. |
| 4 | `precio_venta == precio_compra` (margen cero) es un error de datos, no una decisión de negocio. El loader lo rechaza. |
| 5 | `unidades_vendidas_mes = 0` es válido (producto sin rotación). No se rechaza en validación. |
| 6 | La validación no corrige datos — solo acepta o rechaza. Nunca rellenar nulos con defaults ni coercionar tipos silenciosamente. |

---

## 8. Comportamiento en casos borde

| Caso                                          | Comportamiento                                                                 |
|-----------------------------------------------|--------------------------------------------------------------------------------|
| CSV vacío (solo cabecera, sin filas)          | `_validate` pasa (no hay filas que violen restricciones). Devuelve DataFrame vacío. Los módulos de análisis fallarán después. |
| CSV con una sola fila                         | Válido si cumple restricciones. KMeans en segmentación fallará (necesita >= 4). |
| Columna `nombre` con duplicados               | Válido — el loader no exige unicidad de nombres.                               |
| `precio_compra` como string en el CSV         | `pd.read_csv` lo lee como `object`. La comparación `<= 0` lanzará `TypeError`, no `ValueError`. Gap no manejado. |
| Ruta con espacios                             | `Path(path)` lo maneja correctamente.                                          |
| Archivo CSV con separador `;`                 | Falla silenciosamente — `pd.read_csv` lo leerá como una sola columna. La validación detectará columnas faltantes. |

---

## 9. Lo que este módulo NO hace

- No normaliza ni transforma valores más allá del strip y round documentados.
- No infiere ni rellena valores nulos.
- No convierte tipos de columna explícitamente (confía en la inferencia de pandas).
- No valida unicidad de `nombre`.
- No filtra filas — acepta o rechaza el dataset completo.
- No escribe ficheros ni persiste resultados.

---

## 10. Gaps conocidos

| Gap | Impacto | Sugerencia |
|-----|---------|------------|
| Si `precio_compra` o `precio_venta` son strings en el CSV, la comparación `<= 0` lanza `TypeError` en lugar de un `ValueError` con mensaje claro | Error confuso para el usuario | Añadir coerción explícita con `pd.to_numeric(..., errors='coerce')` antes de validar, y tratar los NaN resultantes como error |
| CSV vacío pasa la validación y produce un DataFrame vacío que falla más tarde en el pipeline con errores poco informativos | Diagnóstico difícil | Añadir `if df.empty: raise ValueError("El CSV no contiene filas de datos")` |
| El separador del CSV está hardcodeado como coma (default de pandas) — no es configurable | CSVs con `;` fallan con mensaje sobre columnas faltantes, no sobre el separador | Documentarlo en el error o aceptar `sep` como parámetro opcional |

---

## 11. Tests esperados

- [ ] CSV válido con datos correctos → devuelve DataFrame sin errores.
- [ ] Archivo no encontrado → `FileNotFoundError` con la ruta en el mensaje.
- [ ] Columna requerida ausente → `ValueError` con el nombre de la columna.
- [ ] Fila con `precio_compra = 0` → `ValueError`.
- [ ] Fila con `precio_compra` negativo → `ValueError`.
- [ ] Fila con `precio_venta <= precio_compra` → `ValueError` con el nombre del producto.
- [ ] Fila con `unidades_vendidas_mes = -1` → `ValueError`.
- [ ] Fila con `unidades_vendidas_mes = 0` → válido, no lanza excepción.
- [ ] CSV con nulo en `precio_compra` → `ValueError` con conteo de nulos.
- [ ] CSV con columna extra no esperada → válido, la columna extra aparece en el DataFrame resultante.
- [ ] `nombre` y `categoria` con espacios al inicio/fin → devueltos sin espacios.
- [ ] `precio_compra` y `precio_venta` redondeados a 4 decimales en la salida.
- [ ] El CSV original no se modifica tras la llamada (inmutabilidad).
- [ ] CSV vacío (solo cabecera) → devuelve DataFrame vacío sin excepción.
