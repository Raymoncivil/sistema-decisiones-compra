# Sistema de Análisis de Compra/Venta — Contexto del Agente

## Descripción
Sistema de minería de datos y análisis inteligente para optimizar decisiones
de compra y venta de productos. El sistema analiza datos históricos, tendencias
y métricas de rentabilidad para recomendar qué comprar, qué evitar y
cuál es la mejor alternativa disponible.

## Objetivo principal
- Identificar productos con mayor beneficio/rentabilidad
- Detectar productos que NO conviene comprar (baja rotación, pérdida)
- Sugerir alternativas óptimas basadas en datos
- Aplicar minería de datos para encontrar patrones ocultos

## Stack tecnológico
- Lenguaje: Python
- Análisis de datos: Pandas, NumPy
- Machine Learning: Scikit-learn
- Visualización: Matplotlib, Seaborn
- Base de datos: SQLite (desarrollo) / PostgreSQL (producción)
- API: FastAPI

## Módulos del sistema
src/
  data/            → ingesta y limpieza de datos
  analysis/        → minería de datos y modelos
  recommendations/ → motor de decisiones
  api/             → endpoints para consultas
  reports/         → generación de reportes

## Reglas del agente
- Siempre validar datos antes de analizar (nulls, outliers)
- Los modelos deben ser explicables (no cajas negras)
- Toda recomendación debe incluir el motivo y el nivel de confianza
- Usar commits descriptivos por cada módulo completado

## Lo que NO debe hacer el agente
- No eliminar datos históricos originales
- No tomar decisiones sin mostrar el razonamiento
- No usar modelos sin validar con datos de prueba primero

## Tipos de análisis esperados
- Análisis de rentabilidad por producto
- Clasificación: comprar / no comprar / alternativa
- Segmentación de productos por comportamiento
- Predicción de demanda futura