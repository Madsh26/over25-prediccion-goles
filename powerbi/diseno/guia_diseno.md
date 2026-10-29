# Over 2.5 · Night Match

Diseño deportivo oscuro, con azul noche, paneles elevados discretos y acentos menta/azul. Segoe UI. La información y los colores semánticos tienen prioridad sobre decoración.

## Revisión del archivo real

Se inspeccionó `proyecto_over25/PROYECTO OVER 2,5.pbix`, que contiene definiciones PBIR y cuatro páginas de 1920×1080: Resumen (14 visuales), Comparación de modelos (6), Análisis por liga y equipo (11) y Próximos partidos (8). El archivo está dentro de proyecto_over25, no en la raíz académica indicada inicialmente.

Los visuales elegidos son adecuados. Los problemas principales son tamaño excesivo de tarjetas, desalineaciones, columnas redundantes en comparación y fechas en jerarquía en el calendario. Falta el segmentador de jornada en la definición guardada de la página 4. No hace falta añadir tablas nuevas.

El usuario detuvo el control de Desktop con Escape. No se guardaron cambios en el PBIX. Estas posiciones son una propuesta de aplicación manual, no una afirmación de que el archivo ya esté reorganizado.

## Archivos

- tema_over25.json: tema JSON validado con JSON Schema Draft 7 oficial de Microsoft 2.157, compatible con las propiedades utilizadas. El informe tiene tarjetas modernas cardVisual; se incluyen estilos específicos para ellas y para tarjetas clásicas.
- banner_superior.png / .svg: 1280×90.
- banner_lateral.png / .svg: 200×630.
- maqueta_resumen.png: referencia del diseño, no captura de Power BI.
- El visual Python oscuro está en ../visual_calibracion.py. Su código debe pegarse en el visual existente: el tema no modifica imágenes producidas por Python.

## Paleta

| Uso | HEX |
|---|---|
| Fondo del lienzo | #080F1B |
| Fondo exterior | #050A12 |
| Paneles y tarjetas | #111E30 |
| Panel alterno / filas alternas | #16263B |
| Cabeceras de tabla | #1B3048 |
| Bordes / rejilla | #293B52 |
| Texto principal | #F3F7FC |
| Texto secundario | #A9B8CC |
| Random Forest / acento / mejora positiva | #35D9B0 |
| Regresión logística | #54AAFF |
| XGBoost | #B69CFF |
| Línea base | #91A5BF |
| Umbral 50% / advertencia | #FFCB66 |
| Error / cambio desfavorable | #FF7D89 |
| Series adicionales | #5DDBE6 y #E99ADB |

Los ocho dataColors son menta, azul, violeta, ámbar, coral, cian, gris azulado y rosa. Para colores estables por modelo, asigne manualmente las cuatro series según la tabla anterior: el orden automático de la paleta depende del visual y sus filtros.

## Aplicación en Desktop

1. Abra el PBIX existente. Ver > Temas > flecha desplegable > Examinar temas. Seleccione tema_over25.json. No es necesario copiar el bloque del chat si usa este archivo.
2. Si un visual conserva formato blanco o colores anteriores, restablezca solo la propiedad de formato correspondiente al valor predeterminado del tema. No pulse una restauración general sin revisar qué personalizaciones útiles perdería. Un tema define valores por defecto, no sobrescribe todos los formatos manuales.
3. En cada página, haga clic en una zona vacía > Formato de página > Configuración del lienzo/Tamaño de página > Personalizado > Ancho 1280, Alto 720. Cambiar estas dimensiones no reubica ni escala automáticamente los visuales existentes: aplique las posiciones siguientes antes de dar la página por terminada. Ver > Vista de página > Ajustar a la página.
4. Insertar > Imagen > banner_superior.png. Formato > General > Propiedades: X=0, Y=0, ancho=1280, alto=90. Quitar borde/fondo propios de la imagen si aparecen; ajuste de imagen Ajustar.
5. Insertar > Imagen > banner_lateral.png: X=0, Y=90, ancho=200, alto=630.
6. Ver > Selección. Envíe las imágenes al fondo y nómbrelas Banner superior y Banner lateral. Bloquee su posición con Bloquear objetos cuando termine de ajustar el resto.
7. Para cambiar un visual: seleccionarlo > Formato del visual > General > Propiedades > Tamaño/Posición; introduzca X, Y, ancho y alto. Las coordenadas son píxeles del lienzo, no de la pantalla.
8. Insertar > Botones > Navegador > Navegador de páginas. Colóquelo en X=14,Y=270,ancho=172,alto=190. Disposición vertical y cuatro páginas visibles. Texto 11, fondo normal #111E30, texto #A9B8CC; seleccionado fondo #183C3B y texto #35D9B0. Los banners son imágenes estáticas; la navegación la proporciona este objeto nativo. En modo edición se usa Ctrl+clic para seguir el botón.
9. Copie ambos banners y el navegador a las otras páginas; conserve posiciones. Un tema no instala imágenes ni crea navegación automáticamente.
10. Guarde con Ctrl+S sobre el mismo PBIX. No cree copias ni ZIP.

## Retícula común

Cabecera y barra lateral ocupan X<200 o Y<90. Área útil: X=220 a 1260, Y=110 a 700. Separación principal 16 px. Los banners no deben tapar visuales. Títulos visuales 13 pt, datos/etiquetas 10–11 pt, valores principales de tarjetas 28 pt. No reduzca todo para eliminar el desplazamiento de una tabla.

### 1. Resumen

Conservar los 12 indicadores y dos segmentadores. Reagrupar por función, sin añadir gráficos redundantes.

| Elemento / campo | X | Y | Ancho | Alto |
|---|---:|---:|---:|---:|
| Segmentador dim_modelo[modelo], desplegable único | 220 | 110 | 508 | 48 |
| Segmentador dim_temporada[temporada], 2025-26 | 744 | 110 | 516 | 48 |
| Tarjeta Partidos evaluados tarjeta | 220 | 174 | 336 | 68 |
| Tarjeta Aciertos | 572 | 174 | 336 | 68 |
| Tarjeta Fallos | 924 | 174 | 336 | 68 |
| ROC AUC | 220 | 258 | 336 | 126 |
| ROC AUC linea base | 572 | 258 | 336 | 126 |
| Diferencia ROC AUC base | 924 | 258 | 336 | 126 |
| Log loss | 220 | 400 | 336 | 126 |
| Log loss linea base | 572 | 400 | 336 | 126 |
| Mejora log loss base | 924 | 400 | 336 | 126 |
| Exactitud | 220 | 542 | 336 | 126 |
| Exactitud linea base | 572 | 542 | 336 | 126 |
| Diferencia exactitud base | 924 | 542 | 336 | 126 |

Columnas visuales: Modelo / Línea base / Diferencia. Valores de diferencia positivos favorables en menta; diferencias desfavorables en coral. La diferencia de exactitud debe titularse Cambio de exactitud (pp), por ejemplo −0,20 pp. AUC decimal, no porcentaje; pérdida menor es mejor. Debajo, una nota pequeña: Mejora probabilística modesta; exactitud sin mejora frente a la referencia. Mantener datos reales y filtros, no copiar textos de la maqueta como indicadores estáticos.

### 2. Comparación de modelos

La tabla, barras, matriz y calibración son adecuados. Conservar cuatro modelos en tabla y barras desactivando la interacción del segmentador de modelo con ambos. Matriz y Python sí responden al modelo. Liga filtra todos.

| Elemento | X | Y | Ancho | Alto |
|---|---:|---:|---:|---:|
| Segmentador liga | 220 | 110 | 508 | 48 |
| Segmentador modelo | 744 | 110 | 516 | 48 |
| Tabla de métricas | 220 | 174 | 1040 | 170 |
| Barras Log loss por modelo | 220 | 360 | 420 | 150 |
| Matriz de confusión | 220 | 526 | 420 | 160 |
| Calibración Python | 656 | 360 | 604 | 326 |

Tabla: dim_modelo[modelo], Partidos evaluados numérico, Exactitud, Precision Over, Sensibilidad Over, F1 Over, ROC AUC, Log loss. Quite del visual las tres diferencias ya mostradas en Resumen. Renombre encabezados para este visual: Modelo, n, Exactitud, Precisión, Recall, F1, AUC, Log loss. Desactivar total.

Barras: categoría modelo, valor Log loss, ascendente, eje desde cero. Matriz: filas clase_real_texto, columnas clase_predicha_texto, valores Partidos evaluados; totales apagados. Título corto Matriz de confusión y subtítulo Real por filas · Predicción por columnas. Calibración conserva id_prediccion, modelo, resultado_over25, probabilidad_over25, sin resumir; pegar el código oscuro actualizado. No promediar AUC de ligas; conservar los controles DAX existentes.

### 3. Análisis por liga y equipo

Mantener tabla y barras históricas, cuatro tarjetas y cuatro filtros. No hace falta otra tabla de predicciones.

| Elemento | X | Y | Ancho | Alto |
|---|---:|---:|---:|---:|
| Liga | 220 | 110 | 248 | 56 |
| Temporada | 484 | 110 | 248 | 56 |
| Equipo | 748 | 110 | 248 | 56 |
| Modelo | 1012 | 110 | 248 | 56 |
| Partidos evaluados en prueba | 220 | 182 | 248 | 94 |
| Exactitud del modelo | 484 | 182 | 248 | 94 |
| Log loss | 748 | 182 | 248 | 94 |
| Probabilidad Over media | 1012 | 182 | 248 | 94 |
| Barras Over por equipo | 220 | 292 | 410 | 394 |
| Tabla histórica | 646 | 292 | 614 | 394 |

Use el textbox existente como nota pequeña de periodo cerca de las tarjetas, o integre Prueba 2025-26 en sus títulos. Tabla: equipo_liga, Participaciones historicas, Porcentaje Over historico, Goles favor promedio, Goles contra promedio, Goles totales promedio. Encabezados cortos: Equipo, PJ, Over %, GF, GC, Goles/partido. En GF y GC aclarar que son promedios mediante título o subtítulo. Barras: equipo_liga y Porcentaje Over historico, orden descendente, eje 0–100%, desplazamiento para todas las categorías. Las tarjetas son solo de prueba; el histórico puede incluir las tres temporadas. Mantener esa diferencia visible en títulos.

### 4. Próximos partidos

La tabla es necesaria para consultar los 19 sin pronóstico; las barras muestran solo probabilidades disponibles. Las tres tarjetas son adecuadas. Incorporar el segmentador de jornada que falta en el archivo guardado. La fecha de corte sigue siendo 2026-10-17, aunque el informe se abra más tarde.

| Elemento | X | Y | Ancho | Alto |
|---|---:|---:|---:|---:|
| Liga | 220 | 110 | 508 | 56 |
| Jornada (nuevo segmentador) | 744 | 110 | 516 | 56 |
| Partidos disponibles | 220 | 182 | 336 | 94 |
| Con pronóstico | 572 | 182 | 336 | 94 |
| Sin historial suficiente | 924 | 182 | 336 | 94 |
| Barras de probabilidad | 220 | 292 | 456 | 360 |
| Calendario | 692 | 292 | 568 | 360 |
| Textbox de fecha de corte existente | 220 | 668 | 1040 | 32 |

Reubique el título de texto existente fuera del área de gráficos o use un título de página discreto; el banner ya identifica el proyecto. Barras: Encuentro y promedio de probabilidad_over25, eje 0–1, etiquetas %, orden descendente, nulos excluidos solo en este visual. Línea de umbral 0,5: ámbar #FFCB66, discontinua, grosor 1–2 px (el archivo actual usa rojo muy grueso).

Calendario: cambiar la jerarquía de fecha por fecha simple; conservar jornada, local, visitante, probabilidad_over25 y clase_predicha_texto. estado_prediccion puede conservarse si se necesita, pero duplica parte de la información de clase_predicha_texto en los casos sin predicción. No sumar probabilidad o jornada; usar No resumir. Renombrar encabezados Fecha, Jda., Local, Visitante, P(Over), Pronóstico. Conservar null en probabilidades ausentes y mostrar sin predicción mediante el texto. La tabla completa mantiene 70 filas; las barras, 51 probabilidades.

Bandas de probabilidad: ≥60% menta, 50–<60% ámbar, <50% azul, sin pronóstico gris. Son ayudas de lectura, no niveles validados de confianza. Para coherencia con el tema, actualizar los colores de la medida Color probabilidad proximos si conserva los HEX anteriores.

## Limitaciones y comprobación final

El tema no mueve visuales, no cambia el tamaño de página, no añade imágenes y no sobrescribe todos los formatos locales ni el DAX de formato condicional. No colorea el gráfico Python: pegar su script actualizado. SVG es editable y escalable; use PNG en Insertar > Imagen para evitar diferencias de soporte entre versiones. Los banners no tienen vínculos ni texto accesible interactivo; el navegador nativo sí.

Mantenga ejes de barras desde cero, diferencias con signo y nombres legibles. No use verde para todos los resultados: RF pierde 0,20 pp de exactitud frente a base. Mantenga 1008/564/444 para RF global en prueba y 70/51/19 para fixtures sin filtros. Pruebe filtros después de reorganizar. No se aplicó ni guardó este tema en Desktop porque el usuario detuvo Computer Use. La validez contra esquema no equivale a una importación comprobada en la instalación del usuario.

Referencias oficiales: [esquemas de tema Microsoft](https://github.com/microsoft/powerbi-desktop-samples/tree/main/Report%20Theme%20JSON%20Schema), [temas personalizados](https://learn.microsoft.com/en-us/power-bi/create-reports/report-themes-create-custom).
