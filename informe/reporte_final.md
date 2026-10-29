# Reporte del proyecto hasta Fase 7

Actualizado: 2026-10-18T12:14:13-05:00.

Fuente: [Flashscore](https://www.flashscore.com/). Se conservaron las URLs de cada partido en los CSV y las nueve URLs históricas y tres de fixtures en data/raw/evidencia/inventario.json. Over25=1 representa tres o más goles; Under=0, dos o menos.

Estado: Fases 6 y 7 completas. Preparación de Power BI entregada; el estudiante construirá el .pbix.

## Filas y cobertura por liga/temporada

La cobertura exige valores para ambos equipos. Si las fichas no terminaron, es provisional.

| Liga | Temporada | Filas/esperadas | IDs únicos | Nulos básicos % | Fichas | Tiros % | Al arco % | Posesión % | Córners % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Premier League | 2023-2024 | 380/380 | 380 | 0.0 | 380 | 100.0 | 100.0 | 100.0 | 100.0 |
| Premier League | 2024-2025 | 380/380 | 380 | 0.0 | 380 | 100.0 | 100.0 | 100.0 | 100.0 |
| Premier League | 2025-2026 | 380/380 | 380 | 0.0 | 380 | 100.0 | 100.0 | 100.0 | 100.0 |
| LaLiga | 2023-2024 | 380/380 | 380 | 0.0 | 380 | 100.0 | 100.0 | 100.0 | 100.0 |
| LaLiga | 2024-2025 | 380/380 | 380 | 0.0 | 380 | 100.0 | 100.0 | 100.0 | 100.0 |
| LaLiga | 2025-2026 | 380/380 | 380 | 0.0 | 380 | 100.0 | 100.0 | 100.0 | 100.0 |
| Bundesliga | 2023-2024 | 306/306 | 306 | 0.0 | 306 | 100.0 | 100.0 | 100.0 | 100.0 |
| Bundesliga | 2024-2025 | 306/306 | 306 | 0.0 | 306 | 100.0 | 100.0 | 100.0 | 100.0 |
| Bundesliga | 2025-2026 | 306/306 | 306 | 0.0 | 306 | 100.0 | 100.0 | 100.0 | 100.0 |

## Fixtures 2026-27

Todos quedan guardados y exentos del límite histórico; no se visitan sus fichas.

| Liga | Guardados |
|---|---:|
| Premier League | 315 |
| LaLiga | 296 |
| Bundesliga | 254 |

## Limpieza y características

Filas de modelado: 2757. Excluidas por historial: 441.
Variables numéricas: 94; variable categórica adicional: liga. Entrenamiento: 1749 filas de 2023-24/2024-25; prueba: 1008 de 2025-26.
Fixtures de las próximas tres jornadas por liga: 70; sin historial suficiente: 19.

Solo se usan fechas estrictamente anteriores; todos los partidos del mismo día se excluyen del historial. Se arrastra historial entre temporadas. Mínimo 10 partidos generales y 5 en la sede. Ventanas 5/10; medias estadísticas con al menos 80% de observaciones. Las Fases 4 y 5 se completaron; resultados más abajo.

Jornadas consecutivas preparadas: {"Bundesliga": [6, 7, 8], "LaLiga": [9, 10, 11], "Premier League": [7, 8, 9]}. Los aplazados de jornadas anteriores siguen en el maestro, fuera del horizonte de predicción.

Verificación independiente: OK: partición completa de 3198 resultados, variables numéricas finitas y medias previas de goles recalculadas para todas las filas; auditoría de fechas estrictamente anteriores..

El historial de fixtures está congelado al último resultado permitido (2025-26); no incluye resultados 2026-27. Los fixtures sin historial permanecen señalados.

Las proporciones Over históricas están en escala 0–1 y la posesión en 0–100. El dataset histórico incluye solo filas elegibles; las exclusiones por liga/temporada y el listado de variables están en metadatos_modelo.json y filas_sin_historial.csv.

## Línea base temporal

Clase mayoritaria elegida SOLO con 2023-24/2024-25 y evaluada en 2025-26. La mayoría del test es solo descriptiva, nunca se usa para decidir la clase.

| Liga | Población | Clase train | n test | Accuracy test |
|---|---|---:|---:|---:|
| Premier League | historico_completo | 1 | 380 | 55.00% |
| LaLiga | historico_completo | 0 | 380 | 50.00% |
| Bundesliga | historico_completo | 1 | 306 | 63.73% |
| Todas | historico_completo | 1 | 1066 | 55.72% |
| Premier League | dataset_modelo | 1 | 360 | 55.56% |
| LaLiga | dataset_modelo | 0 | 352 | 50.00% |
| Bundesliga | dataset_modelo | 1 | 296 | 64.19% |
| Todas | dataset_modelo | 1 | 1008 | 56.15% |

La referencia de Bundesliga supera 63% por su frecuencia de Over; es una línea base trivial. Los modelos posteriores deben compararse con esta referencia en las mismas filas de prueba.

## Incidencias y archivos

Fichas distintas con algún tiempo de espera: 105; completadas posteriormente: 105. Reducciones automáticas de ritmo registradas: 21; recuperaciones tras 20 fichas correctas: 21. No se activó la parada por CAPTCHA o restricción de acceso.

Fechas sin año se derivan de temporada verificada y mes, con marca de procedencia. Los playoffs de Bundesliga se excluyen: solo 306 partidos de liga regular. Las tarjetas quedan fuera por falta de asociación tabular fiable. No se rellenan estadísticas ausentes con ceros.

Se recuperó un bloqueo temporal de escritura de Windows (WinError 5) validando y consolidando el temporal en el CSV canónico. Se añadieron reintentos de reemplazo con backoff. No se consultó la copia de recuperación.

El ritmo es de hasta tres contextos, pausa 1–2,5 s por worker; ante aumento de errores, un worker y 5–8 s. CAPTCHA o restricción detienen la extracción sin intentar resolverlos. Las fichas fallidas se reintentan al final con backoff. Imágenes, fuentes, medios y dominios de anuncios/analítica se bloquean.

Se consolidaron los informes previos en este reporte y el código del piloto en config.py. Se eliminaron las muestras duplicadas, ZIP de avances, informes anteriores y DOM/capturas acumulados. Quedan datos canónicos, código, log único, estado de reanudación, metadatos y evidencia mínima. No se genera ZIP nuevo.

Archivos retirados: muestra_piloto.csv; validar_piloto.py y auditar_inventario.py; reporte_piloto.md, reporte_escalado.md, README_piloto.md y sus auditorías/controles redundantes; evidencia_piloto y DOM/capturas de ejecuciones anteriores; proyecto_over25_fase1_piloto.zip y proyecto_over25_avance_escalado.zip. Los doce certificados de inventario se consolidaron en data/raw/evidencia/inventario.json. Se conserva una sola muestra de DOM comprimida como evidencia mínima.

El resumen intermedio de limpieza se integró en metadatos_modelo.json y se retiró su archivo separado. Los temporales de escritura se consumen al reemplazar los CSV; se retiran las cachés de compilación del código al entregar.

La copia de seguridad única se creó una sola vez y no se leyó ni utilizó en el pipeline. Se eliminó al terminar las Fases 4 y 5 por autorización expresa del estudiante.

## Reejecución

Desde proyecto_over25, ejecutar:

```powershell
.\.venv\Scripts\python.exe -u src/scraper.py
```

Reutiliza los detalles completos y sobrescribe los mismos CSV canónicos. La copia de recuperación no forma parte de la ejecución. El log es informe/scraping.log; el estado operativo está en informe/estado_extraccion.json.

Salidas de revisión, si el scraping termina: data/clean/dataset_modelo.csv, dataset_fixtures_features.csv, datos_limpios.csv, fixtures_limpios.csv, linea_base.csv, auditoria_temporal.csv, filas_sin_historial.csv, calidad_datos.csv y metadatos_modelo.json. El dataset fue aprobado por el estudiante antes del entrenamiento. La Fase 5 fue aprobada por el estudiante antes de continuar a las Fases 6 y 7.

## Fases 4 y 5: evaluación temporal y predicciones

Entrenamiento: 1749 filas de 2023-24/2024-25. Prueba independiente: 1008 de 2025-26. Cuatro cortes TimeSeriesSplit sobre fechas únicas, sin dividir un día entre entrenamiento y validación. Preprocesamiento ajustado dentro de cada fold. Variables: las 94 numéricas aprobadas y liga; motivo_exclusion, IDs, equipos, temporada, fecha y resultado actual quedan fuera.

Modelo seleccionado: **Random Forest**, por menor log loss media en cuatro folds temporales; ROC-AUC desempata. Umbral fijo 0,5. La línea base aprende la frecuencia y clase mayoritaria por liga solo del entrenamiento; se evalúa sobre exactamente las mismas filas que los demás modelos. El conjunto de prueba nunca decide hiperparámetros, selección, umbral ni calibración.

| Modelo | Log loss CV | ROC-AUC CV |
|---|---:|---:|
| Línea base | 0.6848 | 0.5542 |
| Regresión logística | 0.6785 | 0.5865 |
| Random Forest | 0.6753 | 0.5860 |
| XGBoost | 0.6771 | 0.5820 |

Métricas de prueba (clase positiva = Over; TN/FP/FN/TP en metricas.csv). Menor log loss y mayor ROC-AUC son preferibles.

| Liga | Modelo | n | Accuracy | Precisión | Recall | F1 | ROC-AUC | Log loss |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Todas | Línea base | 1008 | 56.15% | 0.595 | 0.689 | 0.638 | 0.5252 | 0.6835 |
| Bundesliga | Línea base | 296 | 64.19% | 0.642 | 1.000 | 0.782 | 0.5000 | 0.6580 |
| LaLiga | Línea base | 352 | 50.00% | 0.000 | 0.000 | 0.000 | 0.5000 | 0.6955 |
| Premier League | Línea base | 360 | 55.56% | 0.556 | 1.000 | 0.714 | 0.5000 | 0.6928 |
| Todas | Regresión logística | 1008 | 57.64% | 0.597 | 0.754 | 0.667 | 0.5675 | 0.6786 |
| Bundesliga | Regresión logística | 296 | 62.16% | 0.650 | 0.889 | 0.751 | 0.5348 | 0.6571 |
| LaLiga | Regresión logística | 352 | 57.10% | 0.573 | 0.557 | 0.565 | 0.5850 | 0.6806 |
| Premier League | Regresión logística | 360 | 54.44% | 0.563 | 0.800 | 0.661 | 0.5096 | 0.6944 |
| Todas | Random Forest | 1008 | 55.95% | 0.580 | 0.781 | 0.666 | 0.5728 | 0.6764 |
| Bundesliga | Random Forest | 296 | 58.78% | 0.633 | 0.853 | 0.726 | 0.5744 | 0.6542 |
| LaLiga | Random Forest | 352 | 56.53% | 0.557 | 0.636 | 0.594 | 0.5947 | 0.6793 |
| Premier League | Random Forest | 360 | 53.06% | 0.551 | 0.840 | 0.665 | 0.5063 | 0.6916 |
| Todas | XGBoost | 1008 | 55.65% | 0.577 | 0.790 | 0.667 | 0.5739 | 0.6773 |
| Bundesliga | XGBoost | 296 | 59.12% | 0.629 | 0.884 | 0.735 | 0.5658 | 0.6576 |
| LaLiga | XGBoost | 352 | 53.69% | 0.533 | 0.591 | 0.561 | 0.5886 | 0.6810 |
| Premier League | XGBoost | 360 | 54.72% | 0.559 | 0.875 | 0.682 | 0.5155 | 0.6899 |

En prueba, el seleccionado cambia ROC-AUC en +0.0476 y log loss en -0.0072 frente a la referencia. Estos resultados son una evaluación, no una garantía de mejora futura.

Auditoría: verificación independiente de historiales previos, exclusión de resultados actuales y metadatos, fechas estrictas en los cuatro folds y en train/test, IDs disjuntos y lista blanca de predictores. Ninguna evaluación superó 66% de accuracy.

Importancia por permutación para los tres modelos aprendidos: ocho repeticiones sobre la última validación interna, con ajuste solo en fechas anteriores. Se mide aumento de log loss; valores negativos también se conservan. Las ventanas correlacionadas pueden repartir la importancia. La curva de calibración es diagnóstica del test y no se utiliza para recalibrar.

Verificación de entrega: OK: artefacto recargado; probabilidades y todas las métricas reproducidas; 70 fixtures, 19 vacíos; dataset aprobado intacto; ocho PNG.

Predicciones: 1.008 partidos de prueba por cada uno de los cuatro modelos (4.032 filas, no partidos nuevos). Fixtures: 70 filas canónicas; 51 con probabilidad y clase del modelo elegido y 19 como **sin predicción**, con ambas salidas vacías. Se mantienen sus motivos de exclusión. El modelo no se reajusta con la prueba; los historiales de fixtures sí incluyen los resultados permitidos hasta 2025-26. No se usan resultados 2026-27.

Gráficas: distribución de goles, Over por liga y por equipo, matrices de confusión, ROC, permutación, calibración y probabilidad frente al resultado. Distribuciones descriptivas usan los 3.198 resultados históricos; evaluación usa solo los 1.008 elegibles de prueba. Las proporciones por equipo muestran también su tamaño muestral.

Limitaciones: muestras pequeñas por liga, incertidumbre del fútbol, cambios de plantel y ausencia de alineaciones/lesiones. Las medias móviles se actualizan con resultados anteriores durante la prueba, como en una evaluación cronológica; no son un pronóstico de toda la temporada realizado en una sola fecha. Los futuros equipos sin historial suficiente quedan sin pronóstico.

Archivos canónicos nuevos: src/modelo.py, src/estimadores.py, src/graficas.py; data/modelo/modelo.joblib (cuatro estimadores y selector en un único contenedor); data/clean/metricas.csv, resultados_cv.csv, validacion_temporal.csv, importancia_variables.csv, predicciones_prueba.csv, predicciones_fixtures.csv y metadatos_modelado.json; ocho PNG en graficas. No se crearon ZIP ni versiones.

Reejecutar únicamente modelado y gráficas, desde proyecto_over25:

```powershell
python -m pip --python .venv/Scripts/python.exe install -r requirements.txt
.\.venv\Scripts\python.exe -u src/modelo.py
.\.venv\Scripts\python.exe -u src/graficas.py
.\.venv\Scripts\python.exe -u src/verificar_modelado.py
```

Los comandos sobrescriben sus archivos canónicos y no vuelven a extraer datos ni recrean la copia de seguridad. El artefacto joblib requiere las versiones de requirements.txt y que src esté en sys.path para cargar estimadores. Las Fases 6 y 7 se describen al final de este reporte.

## Fases 6 y 7

Exportación validada en powerbi: nombres de columnas sin tildes ni espacios, UTF-8 con BOM, delimitador coma, punto decimal y fechas ISO. Se conservaron todos los CSV originales aprobados.

| Tabla | Filas |
|---|---:|
| partidos_predicciones.csv | 4032 |
| metricas_modelos.csv | 16 |
| proximos_partidos.csv | 70 |
| equipos_resumen.csv | 174 |
| importancia_variables.csv | 285 |
| dim_liga.csv | 4 |
| dim_modelo.csv | 4 |
| dim_temporada.csv | 4 |
| dim_equipo.csv | 80 |
| dim_partido.csv | 1078 |
| puente_partido_equipo.csv | 2156 |

Prueba: 2025-26; 1.008 partidos únicos y cuatro modelos. Los totales de métricas son filas independientes de los desgloses y no deben sumarse con ellos. Snapshot de fixtures: 2026-10-17; último resultado permitido para features: 2026-05-24. Los pronósticos son de ese corte, no se han actualizado con resultados posteriores.

Guía, relaciones, tipos, diseño y comprobaciones: powerbi/guia_powerbi.md. Medidas listas para crear individualmente: powerbi/medidas.dax. Visual opcional: powerbi/visual_calibracion.py, con configuración explícita del intérprete. Se comprobó su ejecución con los datos exportados fuera de Desktop; las relaciones, DAX y el visual quedan pendientes de verificación en el .pbix que construirá el estudiante.

Documentación: README.md renovado y borrador académico en informe/borrador_informe.md, con metodología, resultados por liga, limitaciones y anexos. No se entrega ni se afirma haber generado un .pbix. Anexo pendiente: powerbi/informe_over25.pbix, a guardar por el estudiante. No se generaron ZIP, versiones ni nuevas copias de seguridad.

Reejecución de exportaciones: `.\.venv\Scripts\python.exe -u src/powerbi.py`. Sobrescribe las mismas once tablas y actualiza este reporte. No vuelve a extraer ni ajustar modelos. Trabajo detenido al terminar la Fase 7.

Verificación adicional de Fases 6/7: filtros de 80 equipos comprobados como local o visitante; ausencia de duplicación al seleccionar dos equipos; visual Python ejecutado con datos completos, vacíos y campos faltantes; hash del dataset aprobado intacto. DAX y relaciones pendientes de ejecutar en Desktop.

## Diseño visual del informe Power BI

Se revisó el PBIX aportado por el estudiante: PROYECTO OVER 2,5.pbix, en la raíz del proyecto. Contiene cuatro páginas de 1920×1080 y visuales nativos modernos. Se entregan powerbi/diseno/tema_over25.json (validado contra Microsoft JSON Schema 2.157), banners superior 1280×90 y lateral 200×630 en PNG y SVG, maqueta_resumen.png y guia_diseno.md con posiciones para 1280×720. El visual Python canónico se adaptó a la misma paleta. No se guardaron cambios en el PBIX: la herramienta de control devolvió una interrupción por Escape. Aplicación del tema y reubicación pendientes en Desktop. No se modificaron datos ni modelos; hash del dataset comprobado. No se generaron ZIP ni versiones.
