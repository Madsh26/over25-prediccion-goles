# Guía de Power BI Desktop

El estudiante construirá y guardará `powerbi/informe_over25.pbix`. Esta entrega prepara datos, medidas y diseño; el archivo .pbix todavía está pendiente.

## 1. Alcance y fechas que deben verse en el informe

- Evaluación: temporada **2025-26**, 1.008 partidos elegibles. Entrenamiento: 2023-24 y 2024-25, 1.749 filas. Los modelos se seleccionaron usando cuatro validaciones temporales dentro del entrenamiento.
- Pronósticos: snapshot de fixtures del **2026-10-17**; las features usan resultados hasta **2026-05-24**. Son pronósticos de ese corte. Abrir o actualizar Power BI no incorpora resultados posteriores ni vuelve a entrenar.
- Próximas tres jornadas: Premier League 7–9 (25 partidos), LaLiga 9–11 (25) y Bundesliga 6–8 (20). Hay 70 filas: 51 con predicción de Random Forest y 19 sin historial suficiente. Las 19 conservan probabilidades y clases vacías.
- Umbral de clase: probabilidad Over ≥0,5. Over significa tres o más goles. El modelo elegido por CV es Random Forest, aunque otro modelo tenga una métrica de prueba superior.

## 2. Importación y tipos

1. Abra Power BI Desktop y cree un informe vacío. Vaya a **Inicio > Obtener datos > Texto/CSV**. Seleccione cada uno de los once CSV de esta carpeta.
2. Origen del archivo: **65001: Unicode (UTF-8)**. Delimitador: **coma**. Pulse **Transformar datos**. La marca BOM facilita reconocer UTF-8. Consulte [Csv.Document de Microsoft](https://learn.microsoft.com/en-us/powerquery-m/csv-document).
3. Use la primera fila como encabezados. Si el paso automático `Tipo cambiado` interpretó mal los decimales, elimínelo antes de convertirlos. Los archivos usan punto decimal: clic derecho en la columna > **Cambiar tipo > Usar configuración regional > Número decimal > Inglés (Estados Unidos)**. Para fechas ISO use tipo **Fecha**, no texto. [Tipos y configuración regional](https://learn.microsoft.com/en-us/power-query/data-types).
4. Respete esta asignación:

| Columnas | Tipo |
|---|---|
| `id_partido`, `id_prediccion`, equipos, modelo, liga, temporada, uso, variable, estados y motivos | Texto |
| Otros `id_*`, jornada, clases 0/1, resultado, acierto, indicadores, partidos, goles acumulados, TN/FP/FN/TP | Número entero |
| Probabilidades, proporciones, promedios, exactitud, precisión, sensibilidad, F1, ROC-AUC, pérdidas, diferencias e importancia | Número decimal |
| Todas las columnas `fecha*` | Fecha |

5. Los campos numéricos vacíos de `proximos_partidos` deben convertirse a **null**, sin reemplazarlos por cero. Conserve `estado_prediccion` y `clase_predicha_texto` para mostrar “sin predicción”.
6. Renombre las consultas exactamente como los archivos, sin `.csv`. Pulse **Cerrar y aplicar**. En Modelado configure IDs y clases como **No resumir**. Las proporciones están en escala 0–1: formato porcentaje, sin multiplicar nuevamente por 100. Use cuatro decimales para ROC-AUC y log loss.

## 3. Tablas y grano

| Tabla | Filas | Representa |
|---|---:|---|
| partidos_predicciones | 4.032 | Un partido de prueba × un modelo; 1.008 partidos × 4 |
| metricas_modelos | 16 | Un modelo × ámbito (total o una liga); solo prueba 2025-26 |
| proximos_partidos | 70 | Un fixture; solo el modelo elegido por CV |
| equipos_resumen | 174 | Un equipo × liga × temporada histórica |
| importancia_variables | 285 | Una variable × modelo aprendido; último fold interno, 349 filas |
| dim_liga | 4 | Tres ligas y la clave 0 para el total precomputado |
| dim_modelo | 4 | Línea base=0, logística=1, Random Forest=2, XGBoost=3 |
| dim_temporada | 4 | Entrenamiento, prueba y fixtures |
| dim_equipo | 80 | Equipo identificado dentro de su liga |
| dim_partido | 1.078 | Un partido de prueba o fixture |
| puente_partido_equipo | 2.156 | Dos participantes por partido |

`equipos_resumen` cuenta participaciones equipo-partido. Al sumar todos los equipos se obtienen 6.396 participaciones para los 3.198 partidos. Las tasas se calculan como suma de numeradores / suma de partidos, no como promedio simple de porcentajes. Las columnas de goles son desde la perspectiva del equipo.

## 4. Relaciones

En **Vista Modelo > Administrar relaciones**, quite las relaciones automáticas y cree solamente estas. Todas activas, cardinalidad 1:* y filtro **Único**, excepto la indicada con **Ambas**:

| Lado 1 | Lado * | Clave | Dirección |
|---|---|---|---|
| dim_liga | dim_partido | id_liga | Único |
| dim_liga | metricas_modelos | id_liga | Único |
| dim_liga | equipos_resumen | id_liga | Único |
| dim_temporada | dim_partido | id_temporada | Único |
| dim_temporada | metricas_modelos | id_temporada | Único |
| dim_temporada | equipos_resumen | id_temporada | Único |
| dim_modelo | partidos_predicciones | id_modelo | Único |
| dim_modelo | metricas_modelos | id_modelo | Único |
| dim_modelo | proximos_partidos | id_modelo | Único |
| dim_modelo | importancia_variables | id_modelo | Único |
| dim_partido | partidos_predicciones | id_partido | Único |
| dim_partido | proximos_partidos | id_partido | Único |
| dim_equipo | puente_partido_equipo | id_equipo | Único |
| dim_equipo | equipos_resumen | id_equipo | Único |
| dim_partido | puente_partido_equipo | id_partido | **Ambas** |

El puente permite que un equipo filtre partidos donde fue local **o** visitante. Mantenga solo esa relación bidireccional. No relacione `dim_equipo` con `dim_liga`, ni sus IDs locales/visitantes directamente con los hechos: crearían rutas adicionales. Las claves de liga, temporada y equipo en los hechos se conservan para trazabilidad; no cree todas las relaciones sugeridas automáticamente.

Use segmentadores de las dimensiones, no de los hechos. Para liga filtre el **visual del segmentador** con `id_liga > 0`; la clave 0 (“Todas”) solo identifica las métricas globales. Para mostrar las tres ligas juntas, quite la selección o seleccione las tres ligas reales. No seleccione la fila 0 como si fuera otra competición.

## 5. Medidas DAX y comportamiento de filtros

Abra `medidas.dax`. En **Modelado > Nueva medida**, pegue cada definición por separado, por ejemplo dentro de `partidos_predicciones`. El archivo contiene varias medidas, no es un único script ejecutable. Si su configuración usa `;` como separador DAX, cambie las comas de argumentos por `;`.

- Las medidas de evaluación requieren un modelo en contexto. Active selección única y deje **Random Forest** como valor inicial. Las filas de una tabla comparativa con `dim_modelo[modelo]` también proporcionan ese contexto; sus totales quedan vacíos deliberadamente.
- Exactitud, log loss, aciertos, fallos, proporción Over y matriz se recalculan sobre los partidos filtrados. Las referencias usan las **mismas filas** del modelo base. La diferencia de exactitud se expresa en puntos porcentuales; en `Mejora log loss base`, un valor positivo es favorable.
- ROC-AUC no se puede sumar ni promediar entre ligas. La tarjeta usa la fila precomputada global o la de una sola liga. Con dos ligas, equipo, jornada o detalle de partido devuelve vacío. Para ese subconjunto puede usar el visual Python; no presente el AUC global como si fuera del equipo.
- No arrastre `metricas_modelos[roc_auc]` o su exactitud a una tarjeta usando “Suma” o “Promedio”. Tampoco sume las cuatro filas de ámbito de cada modelo: el total ya contiene sus ligas.
- Importancia: aumento de log loss al permutar, sobre validación interna. No cambia por equipo o liga. En ese visual desactive la interacción de esos segmentadores y titule “Importancia global en validación interna”. La línea base no tiene importancias.

## 6. Diseño de las cuatro páginas

### Página 1. Resumen

Filtro de página: `dim_temporada[temporada] = 2025-26`. Segmentadores: liga y modelo (selección única, Random Forest inicial). No añada equipo aquí.

Fila superior: tarjetas `[ROC AUC]`, `[Log loss]`, `[Exactitud]` y `[Partidos evaluados]`. Segunda fila: `[ROC AUC linea base]`, `[Log loss linea base]`, `[Exactitud linea base]` y las diferencias. Gráfico de aciertos/fallos con las dos medidas. Añada una nota: “Test 2025-26. Modelo elegido por validación temporal interna. Mejora modesta en probabilidades; sin mejora en exactitud para el modelo elegido”.

Al iniciar debe ver: Random Forest, n=1.008, accuracy 55,95%, AUC 0,5728, log loss 0,6764. Base: 56,15%, 0,5252 y 0,6835.

### Página 2. Comparación y matriz

Filtro de página 2025-26. Tabla con `dim_modelo[modelo]` y las medidas de exactitud, precisión, sensibilidad, F1, ROC-AUC, log loss y diferencia contra base. Quite la interacción del segmentador de modelo con esta tabla para que muestre los cuatro. Un gráfico de barras de log loss facilita compararlos (menor es mejor).

Matriz: filas `partidos_predicciones[clase_real_texto]`, columnas `clase_predicha_texto`, valores `[Partidos evaluados]`. Mantenga el segmentador de modelo activo para la matriz. Etiquete filas “Resultado real” y columnas “Predicción”; Under=0, Over=1. Puede desactivar totales marginales. Incluya `[TN]`, `[FP]`, `[FN]`, `[TP]` como tarjetas si prefiere una matriz rotulada.

Añada el visual Python de calibración descrito abajo. La comparación por liga se hace con el segmentador de liga; con dos ligas el AUC precomputado queda vacío.

### Página 3. Liga y equipo

Segmentadores: `dim_liga[liga]`, `dim_temporada[temporada]`, `dim_equipo[equipo_liga]` y modelo (para las métricas de predicción). Mantenga liga sin la clave 0. Puede filtrar las opciones del segmentador de equipo con `[Participaciones historicas] > 0`.

Panel histórico: barras por equipo de `[Porcentaje Over historico]`, tabla con participaciones, goles a favor/contra/totales promedio. Usa los 3.198 resultados y permite elegir las tres temporadas históricas.

Panel de prueba: tarjetas `[Exactitud]`, `[Aciertos]`, `[Fallos]`, `[Log loss]` y `[Probabilidad media]`, tabla de partidos con fecha, local, visitante, probabilidad y clase. Solo contiene 2025-26; las otras temporadas históricas dejan este panel vacío. Con un equipo, el puente incluye sus encuentros en ambas sedes. Mantenga AUC precomputado fuera de este panel; use Python si necesita AUC/calibración de un subconjunto.

La importancia global puede mostrarse como barras de `variable` y `aumento_log_loss`, Top 12, sin suma de ámbitos; no cambia con liga/temporada/equipo. Indique que procede de validación interna de entrenamiento.

### Página 4. Próximos partidos

Filtro de página 2026-27. Modelo fijo Random Forest. No sincronice el segmentador de modelo de las otras páginas con esta página; un filtro de logística dejaría estos fixtures sin filas. El segmentador de temporada de la página 3 tampoco debe sincronizarse aquí ni a las páginas 1/2.

Tarjetas: `[Fixtures visibles]`=70, `[Fixtures con prediccion]`=51 y `[Fixtures sin prediccion]`=19. Tabla con fecha, jornada, local, visitante, `estado_prediccion`, probabilidad, `clase_predicha_texto` y motivo de exclusión. Ordene por fecha y liga.

Probabilidad: formato porcentaje y fondo por reglas o por `[Color probabilidad proximos]`: gris sin probabilidad; azul <50%; ámbar 50–<60%; verde ≥60%. Son bandas de lectura, no categorías validadas de confianza. Conserve visibles las 19 filas; no filtre `probabilidad_over25` por “no vacío”.

Texto visible: “Fixtures capturados al 2026-10-17. Historia hasta 2026-05-24. Pronósticos de corte; no son actualizaciones en vivo”.

## 7. Visual Python opcional

Los CSV y visuales nativos no requieren Python dentro de Power BI. El visual opcional sí necesita configurar la ruta: **Archivo > Opciones y configuración > Opciones > Scripts de Python**. Seleccione el directorio que contiene el ejecutable `.venv/Scripts/python.exe` del proyecto; si no se detecta, use la opción de ruta personalizada. Las dependencias ya constan en `requirements.txt` (pandas, matplotlib y scikit-learn). [Configuración oficial del intérprete](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-python-scripts).

Inserte un visual Python, habilítelo y añada: `partidos_predicciones[id_prediccion]`, `dim_modelo[modelo]`, `partidos_predicciones[resultado_over25]` y `partidos_predicciones[probabilidad_over25]`. Use **No resumir**. Pegue `visual_calibracion.py`. El ID único evita que la agrupación automática suprima observaciones idénticas, comportamiento descrito en la [guía oficial de visuales Python](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-python-visuals).

El script usa solo el DataFrame `dataset` filtrado por Power BI. No vuelve a entrenar ni lee rutas de datos. Se probó con las exportaciones en Python fuera de Desktop; configure y compruebe el visual en su instalación de Power BI. El gráfico generado es una imagen que responde a filtros del informe; no use su apariencia como prueba de recalibración del modelo.

## 8. Comprobación y guardado del .pbix

1. Con las tres ligas, modelo Random Forest y test 2025-26: 1.008 filas evaluadas; aciertos=564, fallos=444; TN=122, FP=320, FN=124, TP=442.
2. Cambie a LaLiga: 352 partidos, exactitud 56,53%, AUC 0,5947, log loss 0,6793. Base: exactitud 50%, AUC 0,5, log loss 0,6955.
3. Seleccione un equipo: la tabla debe incluirlo como local y visitante y cambiar exactitud/log loss; AUC precomputado vacío. Con dos equipos, un partido entre ellos debe seguir contando una vez por modelo.
4. Pruebe dos ligas: AUC precomputado vacío y log loss calculado sobre sus partidos, sin promediar las pérdidas de liga con igual peso.
5. Página 4 sin filtros de liga/equipo: 70 fixtures, 51 predichos, 19 sin predicción. Cambie de página y compruebe que el modelo/temporada de otras páginas no eliminan estos registros.
6. Compruebe tildes en valores, nulls, tipos, relaciones y texto de corte. Guarde **Archivo > Guardar como > powerbi/informe_over25.pbix** y anéxelo a la entrega universitaria con el código, CSV, métricas y PNG. No hay .pbix generado en esta entrega.

Para actualizar únicamente exportaciones: desde la carpeta del proyecto, `.\.venv\Scripts\python.exe -u src/powerbi.py` y después **Actualizar** en Desktop. La fecha de corte sigue siendo la del snapshot: no la cambie por la fecha de apertura.
