# Predicción de Over/Under 2.5 goles con Python y Power BI

Pipeline de ciencia de datos de principio a fin: datos de partidos de Premier League, LaLiga y Bundesliga, ingeniería de variables sin fuga de información, comparación de modelos con validación temporal y preparación de un informe en Power BI.

**Over** = tres o más goles en el partido. **Under** = dos o menos.

## Propósito

Comprobar si las estadísticas de los partidos anteriores de cada equipo (tiros, tiros al arco, posesión y córners en ventanas de 5 y 10 partidos) aportan señal para anticipar si un partido tendrá más de 2,5 goles, frente a una línea base por liga, y cerrar el ciclo hasta un informe en Power BI.

## Motivación

El mercado de goles totales es un caso limpio para practicar evaluación honesta de modelos: la etiqueta es binaria, el resultado se conoce pronto y es fácil engañarse con una validación mal hecha. Quise construir el flujo completo cuidando lo que más se descuida: usar solo información anterior a cada partido, separar entrenamiento y prueba por tiempo y medir calibración y pérdida logarítmica, no solo el porcentaje de aciertos.

## Datos

- 3.198 partidos de tres temporadas (2023-24, 2024-25 y 2025-26) con cobertura completa de tiros, tiros al arco, posesión y córners.
- 2.757 partidos elegibles tras excluir 441 con historial insuficiente. Entrenamiento: 1.749 partidos de las dos primeras temporadas. Prueba: 1.008 partidos de 2025-26.
- 94 variables numéricas y la liga como variable categórica.
- **Los datos no se publican en este repositorio.** Provienen de Flashscore, y su redistribución no está permitida, así que la carpeta `data/` se excluye. El código muestra cómo se procesaron, pero quien quiera reproducirlo debe obtener los datos por su cuenta y respetar los términos del sitio.

## Método

- Variables construidas solo con partidos estrictamente anteriores (sin fuga), con mínimo de 10 partidos de historial general y 5 en la sede.
- Cuatro cortes temporales internos para elegir modelos por pérdida logarítmica, con regularización y semilla 42.
- Modelos comparados: línea base por liga, regresión logística, Random Forest y XGBoost.
- Verificación independiente que recalcula medias, fechas y métricas.

## Resultados

| Modelo | AUC (prueba) | Pérdida logarítmica | Exactitud |
|---|---:|---:|---:|
| Línea base por liga | 0,5252 | 0,6835 | 56,15 % |
| Random Forest (elegido) | 0,5728 | 0,6764 | 55,95 % |

La mejora es **modesta**: el modelo ordena algo mejor los partidos y mejora la probabilidad estimada, pero no acierta más que la línea base con un umbral fijo de 0,5. Es un resultado honesto para un problema donde el azar pesa mucho.

Los resultados completos por liga y modelo están en `resultados/metricas_modelos.csv`, la importancia de variables en `resultados/importancia_variables.csv` y las figuras en `graficas/`.

## Estructura

```text
src/          Código modular comentado en español (extracción, limpieza, variables, modelo, gráficas, verificación)
graficas/     Ocho figuras: calibración, ROC, matrices de confusión, importancia de variables, Over por liga y equipo
informe/      Reporte consolidado y borrador académico
powerbi/      Guía del informe, medidas DAX, visual en Python y diseño
resultados/   Métricas por modelo e importancia de variables
```

## Informe en Power BI

El informe tiene 4 páginas (guía en `powerbi/guia_powerbi.md`, medidas en `powerbi/medidas.dax` y tema en `powerbi/diseno/`). El archivo `.pbix` no se publica porque incluye los datos de origen.

## Entorno

Python 3.14, con las versiones fijadas en `requirements.txt` (NumPy, pandas, scikit-learn, XGBoost, matplotlib, seaborn, joblib y Playwright para la extracción).

## Límites

- La mejora sobre la línea base es pequeña y no garantiza utilidad práctica.
- Solo tres ligas y tres temporadas.
- Los partidos de la temporada 2026-27 se usaron solo como fixtures, sin resultados.

## Autor

Mauricio Serrano · Ingeniería Industrial, Universidad del Magdalena · [Portafolio](https://madsh26.github.io) · [LinkedIn](https://www.linkedin.com/in/mauricio-david-serrano-hernandez/)
