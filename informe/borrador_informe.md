# Predicción de Over/Under 2.5 en tres ligas europeas

Borrador académico. Autor, asignatura, docente y fecha de entrega deben completarse por el estudiante.

## Introducción

Este proyecto analiza si las estadísticas recientes de los equipos ayudan a estimar la probabilidad de que un partido termine con más de 2,5 goles. Over=1 corresponde a tres o más goles y Under=0, a dos o menos. Se trabajó con Premier League, LaLiga y Bundesliga, usando Python para extracción, preparación y modelado y preparando un informe interactivo para Power BI Desktop.

El objetivo fue comparar modelos con una referencia sencilla mediante una evaluación cronológica. Se dio prioridad a ROC-AUC y log loss para evaluar las probabilidades, además de medir la exactitud de la clase con umbral 0,5.

## Fuente y alcance

La fuente fue el sitio público [Flashscore](https://www.flashscore.com/). Se extrajeron las temporadas completas 2023-24, 2024-25 y 2025-26: 380 partidos por temporada en Premier League y LaLiga y 306 en Bundesliga, para un total de 3.198. Las URLs, fechas y hashes de evidencia están en `data/raw/evidencia/inventario.json`. Los CSV raw conservan URLs por partido y metadatos de extracción.

Las páginas cargan contenido con JavaScript. Se utilizó Playwright con Edge, pausas, backoff, guardado incremental y un máximo de tres contextos. Las fichas de resultados proporcionaron tiros, tiros al arco, posesión y córners de ambos equipos. Los nueve grupos liga-temporada alcanzaron cobertura del 100% y no tuvieron nulos en fecha, jornada, equipos o marcador. Las tarjetas se excluyeron por falta de asociación tabular fiable. El scraper contempla detenerse ante restricciones sin eludirlas.

Se conservaron también 865 fixtures de 2026-27 sin visitar sus fichas. Para pronosticar se seleccionaron 70 partidos de las próximas tres jornadas por liga. El snapshot corresponde al 17 de octubre de 2026 y el último resultado permitido en el historial es del 24 de mayo de 2026. Los pronósticos representan ese corte y no incorporan resultados posteriores de 2026-27.

## Metodología

### Limpieza y objetivo

Se normalizaron equipos, fechas ISO y tipos numéricos, se revisaron duplicados e identificadores y se comprobó `total_goles = goles_local + goles_visitante`. La variable objetivo vale uno cuando el total alcanza tres goles. No se fabricaron observaciones ni se sustituyeron estadísticas ausentes por ceros.

### Ventanas móviles y prevención de fuga

Se construyeron 94 variables numéricas y se añadió liga como variable categórica. Incluyen promedios de goles a favor/en contra, proporción Over y estadísticas de juego en ventanas de 5 y 10 partidos, generales y en la sede correspondiente. También se usaron diferencias entre equipos, tamaños de ventana y días desde el último partido.

Cada feature utiliza únicamente fechas estrictamente anteriores. La implementación procesa todos los encuentros de un día como un bloque y actualiza después el historial. Así desplaza las ventanas y excluye también cualquier encuentro del mismo día. Se arrastró historial entre temporadas y se exigieron diez partidos generales y cinco en la sede. Se excluyeron 441 filas por historial insuficiente y quedaron 2.757 elegibles. Una auditoría independiente recalculó medias previas y verificó las fechas.

No se utilizaron como predictores el marcador o las estadísticas actuales, el objetivo, IDs, equipos, temporada, fecha ni `motivo_exclusion`. El preprocesamiento se ajustó dentro de cada fold. El historial de fixtures permaneció congelado al cierre de resultados permitidos de 2025-26, sin completarlo con otros fixtures.

### Entrenamiento y validación

Se entrenó con 1.749 filas de 2023-24 y 2024-25 y se reservó 2025-26 para la evaluación final con 1.008 partidos. Dentro del entrenamiento se usó TimeSeriesSplit con cuatro cortes sobre fechas únicas, sin dividir un día entre entrenamiento y validación.

Se compararon una línea base mayoritaria por liga, regresión logística, Random Forest y XGBoost. La base asigna probabilidades según la frecuencia Over de cada liga en el entrenamiento. Se aplicaron regularización fuerte, árboles poco profundos y semilla 42. Los hiperparámetros se eligieron por menor log loss medio interno. La selección entre modelos priorizó esa pérdida y dejó ROC-AUC como desempate. El umbral de clase se fijó en 0,5.

Random Forest obtuvo el menor log loss interno (0,6753), frente a 0,6848 de base, 0,6785 de logística y 0,6771 de XGBoost. Se eligió antes de consultar el test y no se reajustó con él para generar los pronósticos de fixtures.

## Resultados

### Evaluación global de 2025-26

| Modelo | Accuracy | Precisión Over | Recall Over | F1 | ROC-AUC | Log loss |
|---|---:|---:|---:|---:|---:|---:|
| Línea base | 56,15% | 0,5945 | 0,6890 | 0,6383 | 0,5252 | 0,6835 |
| Regresión logística | 57,64% | 0,5972 | 0,7544 | 0,6667 | 0,5675 | 0,6786 |
| Random Forest | 55,95% | 0,5801 | 0,7809 | 0,6657 | 0,5728 | 0,6764 |
| XGBoost | 55,65% | 0,5768 | 0,7898 | 0,6667 | 0,5739 | 0,6773 |

El modelo seleccionado aumentó ROC-AUC en 0,0476 y redujo log loss en 0,0072 frente a la base. La mejora fue modesta. La exactitud cayó 0,20 puntos porcentuales: 564 aciertos frente a 566 de la referencia. Logística obtuvo mayor exactitud en prueba y XGBoost un AUC ligeramente mayor, pero esos resultados no se usaron para reemplazar al modelo elegido dentro del entrenamiento.

La matriz de Random Forest fue TN=122, FP=320, FN=124 y TP=442. El recall alto de Over vino acompañado de numerosos Under clasificados como Over. Ninguna evaluación global o por liga superó 66%, umbral definido para activar una revisión adicional. En todos los casos se verificaron historiales, fechas, columnas y separación temporal.

### Diferencias por liga

| Liga | n prueba | Accuracy base | Accuracy RF | AUC base | AUC RF | Log loss base | Log loss RF |
|---|---:|---:|---:|---:|---:|---:|---:|
| Premier League | 360 | 55,56% | 53,06% | 0,5000 | 0,5063 | 0,6928 | 0,6916 |
| LaLiga | 352 | 50,00% | 56,53% | 0,5000 | 0,5947 | 0,6955 | 0,6793 |
| Bundesliga | 296 | 64,19% | 58,78% | 0,5000 | 0,5744 | 0,6580 | 0,6542 |

LaLiga mostró la mejora más clara en discriminación, pérdida y exactitud. En Premier League el AUC estuvo cerca de 0,5 y la reducción de pérdida fue mínima. En Bundesliga, la frecuencia alta de Over hizo competitiva a la base: Random Forest mejoró AUC y log loss, pero perdió exactitud. La base global tiene AUC 0,5252 porque asigna probabilidades distintas entre ligas; dentro de cada liga son constantes y su AUC es 0,5.

### Importancia y calibración

La importancia por permutación se calculó para los tres modelos aprendidos sobre la última validación interna (349 filas), ajustando cada estimador solo con fechas previas. Se hicieron ocho repeticiones y se midió el aumento de log loss. Entre las variables con mayor importancia media de Random Forest estuvieron la posesión reciente del local, sus goles y su frecuencia Over en diez encuentros. Las desviaciones fueron amplias y las ventanas están correlacionadas; el orden no demuestra causalidad ni estabilidad de los efectos.

Las curvas de calibración comparan probabilidades medias y proporciones Over observadas en grupos del test. Se usaron como diagnóstico, sin recalibrar con la prueba. Las gráficas muestran la capacidad limitada y la superposición entre probabilidades asignadas a resultados Over y Under.

### Fixtures e informe interactivo

De los 70 fixtures seleccionados, 51 recibieron probabilidad y clase de Random Forest. Los 19 sin historial suficiente conservaron “sin predicción”, con ambas salidas vacías. No se calcularon aciertos de fixtures porque sus resultados no forman parte de la evaluación.

Se prepararon hechos y dimensiones para Power BI, medidas DAX y una guía de cuatro páginas: resumen; comparación y matriz; liga y equipo; y próximos partidos con formato condicional. Las métricas corresponden solo a 2025-26. El .pbix será construido por el estudiante y sigue pendiente al cierre de este borrador.

## Limitaciones

La muestra de entrenamiento es pequeña para 95 predictores y hay correlación entre ventanas. La validación temporal y la regularización reducen el riesgo de sobreajuste, pero no lo eliminan. Una sola temporada de prueba no demuestra estabilidad a largo plazo ni significación estadística de las pequeñas diferencias observadas.

El fútbol presenta variabilidad importante. El modelo no incluye alineaciones, lesiones, sanciones, cambios de entrenador ni noticias de última hora. El rendimiento difiere entre ligas y la proporción Over puede cambiar entre temporadas.

Los equipos sin historial suficiente quedaron excluidos. Las métricas describen partidos elegibles, no todos los 1.066 encuentros de la temporada de prueba. Durante esa evaluación el historial se actualiza con resultados anteriores: no equivale a pronosticar toda la temporada antes de su inicio.

Los fixtures de 2026-27 utilizan historia congelada de 2025-26, con un desfase que limita su utilidad actual. La falta de resultados posteriores fue una restricción del alcance aprobado. Las páginas web también pueden cambiar, de modo que futuras capturas requieren repetir los controles.

## Conclusiones

Se construyó un flujo reproducible de extracción real, limpieza, features históricas, validación temporal y comparación de modelos. Random Forest fue seleccionado con el criterio fijado dentro del entrenamiento y mostró una mejora pequeña en ROC-AUC y log loss, sin mejorar la exactitud al umbral 0,5.

Los resultados por liga muestran que la evaluación global no describe por igual las tres competiciones. La referencia mayoritaria siguió siendo competitiva y la capacidad predictiva fue limitada. La preparación del informe interactivo permite explorar esas diferencias y reconocer fixtures sin información suficiente, conservando vacías sus probabilidades.

## Anexos del enunciado

| Requisito | Archivo o carpeta | Estado |
|---|---|---|
| Código de extracción real | src/scraper.py, pipeline.py, extraccion.py, fichas.py y config.py | Incluido |
| Limpieza y datos | src/limpieza.py; data/clean/datos_limpios.csv | Incluido |
| Features y controles | src/features.py, verificar.py; dataset_modelo.csv y auditoria_temporal.csv | Incluido |
| Modelado y métricas | src/modelo.py, estimadores.py, verificar_modelado.py; data/clean/metricas.csv y resultados_cv.csv | Incluido |
| Modelos entrenados | data/modelo/modelo.joblib | Incluido |
| Código y gráficas | src/graficas.py; graficas/ (ocho PNG) | Incluido |
| Predicciones | data/clean/predicciones_prueba.csv y predicciones_fixtures.csv | Incluido |
| Preparación Power BI | src/powerbi.py; powerbi/*.csv, guia_powerbi.md, medidas.dax y visual_calibracion.py | Incluido |
| Informe interactivo Power BI | powerbi/informe_over25.pbix | **Pendiente de construir y anexar por el estudiante** |

No se generaron ZIP ni versiones adicionales. El reporte de trazabilidad y reejecución está en `informe/reporte_final.md`.
