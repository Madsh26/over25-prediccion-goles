"""Fase 5: gráficas canónicas y consolidación del único reporte final."""
import json
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import confusion_matrix, roc_curve, roc_auc_score
from config import RAIZ
from modelo import CLEAN, NOMBRES

GRAFICAS = RAIZ/'graficas'
COLORES = dict(zip(NOMBRES, ['#778899', '#157f8c', '#d28a20', '#8254a1']))


def guardar(fig, nombre):
    fig.savefig(GRAFICAS/nombre, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def reporte(info):
    """Integra fases anteriores y resultados sin crear reportes adicionales."""
    from pipeline import informe
    informe()
    path = RAIZ/'informe/reporte_final.md'
    texto = path.read_text(encoding='utf-8')
    texto = texto.replace('# Reporte del proyecto hasta Fase 3', '# Reporte del proyecto hasta Fase 5')
    texto = texto.replace('Estado: Fase 3 completa; pendiente revisión antes de entrenar.',
                          'Estado: Fases 4 y 5 completas; detenido antes de Power BI.')
    texto = texto.replace('No se entrenaron modelos.', 'Las Fases 4 y 5 se completaron; resultados más abajo.')
    texto = texto.replace('Entrenamiento previsto:', 'Entrenamiento:')
    texto = texto.replace('Los siguientes pasos de modelado requieren revisión del estudiante.',
                          'El dataset fue aprobado por el estudiante antes del entrenamiento. Se detiene el trabajo al terminar la Fase 5.')
    if info['backup_eliminado']:
        texto = texto.replace('La copia de seguridad única solicitada se creó al comienzo. No se volvió a leer, modificar ni utilizar en el pipeline; no se incluye en inventarios ni paquetes. Tú decides cuándo borrarla.',
                              'La copia de seguridad única se creó una sola vez y no se leyó ni utilizó en el pipeline. Se eliminó al terminar las Fases 4 y 5 por autorización expresa del estudiante.')
    m = pd.read_csv(CLEAN/'metricas.csv')
    texto += '\n## Fases 4 y 5: evaluación temporal y predicciones\n\n'
    texto += f"Entrenamiento: {info['train']} filas de 2023-24/2024-25. Prueba independiente: {info['test']} de 2025-26. Cuatro cortes TimeSeriesSplit sobre fechas únicas, sin dividir un día entre entrenamiento y validación. Preprocesamiento ajustado dentro de cada fold. Variables: las 94 numéricas aprobadas y liga; motivo_exclusion, IDs, equipos, temporada, fecha y resultado actual quedan fuera.\n\n"
    texto += f"Modelo seleccionado: **{info['seleccionado']}**, por {info['criterio']}. Umbral fijo 0,5. La línea base aprende la frecuencia y clase mayoritaria por liga solo del entrenamiento; se evalúa sobre exactamente las mismas filas que los demás modelos. El conjunto de prueba nunca decide hiperparámetros, selección, umbral ni calibración.\n\n"
    texto += '| Modelo | Log loss CV | ROC-AUC CV |\n|---|---:|---:|\n'
    for r in info['comparacion_cv']:
        texto += f"| {r['modelo']} | {r['cv_log_loss']:.4f} | {r['cv_roc_auc']:.4f} |\n"
    texto += '\nMétricas de prueba (clase positiva = Over; TN/FP/FN/TP en metricas.csv). Menor log loss y mayor ROC-AUC son preferibles.\n\n'
    texto += '| Liga | Modelo | n | Accuracy | Precisión | Recall | F1 | ROC-AUC | Log loss |\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in m.to_dict('records'):
        texto += f"| {r['liga']} | {r['modelo']} | {r['n']} | {r['accuracy']:.2%} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | {r['roc_auc']:.4f} | {r['log_loss']:.4f} |\n"
    globales = m[m.liga.eq('Todas')].set_index('modelo')
    sel, base = globales.loc[info['seleccionado']], globales.loc['Línea base']
    texto += f"\nEn prueba, el seleccionado cambia ROC-AUC en {sel.roc_auc-base.roc_auc:+.4f} y log loss en {sel.log_loss-base.log_loss:+.4f} frente a la referencia. Estos resultados son una evaluación, no una garantía de mejora futura.\n"
    altos = info['auditoria']['casos_accuracy_mayor_66']
    texto += '\nAuditoría: verificación independiente de historiales previos, exclusión de resultados actuales y metadatos, fechas estrictas en los cuatro folds y en train/test, IDs disjuntos y lista blanca de predictores. '
    texto += ('Ninguna evaluación superó 66% de accuracy.\n' if not altos else
              f"Se revisaron {len(altos)} evaluaciones superiores al 66%; controles con etiquetas de entrenamiento permutadas documentados en metadatos_modelado.json. Una métrica alta por liga no prueba por sí sola fuga.\n")
    texto += '\nImportancia por permutación para los tres modelos aprendidos: ocho repeticiones sobre la última validación interna, con ajuste solo en fechas anteriores. Se mide aumento de log loss; valores negativos también se conservan. Las ventanas correlacionadas pueden repartir la importancia. La curva de calibración es diagnóstica del test y no se utiliza para recalibrar.\n'
    if info.get('verificacion_entregables'):
        texto += '\nVerificación de entrega: '+info['verificacion_entregables']+'\n'
    texto += '\nPredicciones: 1.008 partidos de prueba por cada uno de los cuatro modelos (4.032 filas, no partidos nuevos). Fixtures: 70 filas canónicas; 51 con probabilidad y clase del modelo elegido y 19 como **sin predicción**, con ambas salidas vacías. Se mantienen sus motivos de exclusión. El modelo no se reajusta con la prueba; los historiales de fixtures sí incluyen los resultados permitidos hasta 2025-26. No se usan resultados 2026-27.\n'
    texto += '\nGráficas: distribución de goles, Over por liga y por equipo, matrices de confusión, ROC, permutación, calibración y probabilidad frente al resultado. Distribuciones descriptivas usan los 3.198 resultados históricos; evaluación usa solo los 1.008 elegibles de prueba. Las proporciones por equipo muestran también su tamaño muestral.\n'
    texto += '\nLimitaciones: muestras pequeñas por liga, incertidumbre del fútbol, cambios de plantel y ausencia de alineaciones/lesiones. Las medias móviles se actualizan con resultados anteriores durante la prueba, como en una evaluación cronológica; no son un pronóstico de toda la temporada realizado en una sola fecha. Los futuros equipos sin historial suficiente quedan sin pronóstico.\n'
    texto += '\nArchivos canónicos nuevos: src/modelo.py, src/estimadores.py, src/graficas.py; data/modelo/modelo.joblib (cuatro estimadores y selector en un único contenedor); data/clean/metricas.csv, resultados_cv.csv, validacion_temporal.csv, importancia_variables.csv, predicciones_prueba.csv, predicciones_fixtures.csv y metadatos_modelado.json; ocho PNG en graficas. No se crearon ZIP ni versiones.\n'
    texto += '\nReejecutar únicamente modelado y gráficas, desde proyecto_over25:\n\n```powershell\npython -m pip --python .venv/Scripts/python.exe install -r requirements.txt\n.\\.venv\\Scripts\\python.exe -u src/modelo.py\n.\\.venv\\Scripts\\python.exe -u src/graficas.py\n.\\.venv\\Scripts\\python.exe -u src/verificar_modelado.py\n```\n\nLos comandos sobrescriben sus archivos canónicos y no vuelven a extraer datos ni recrean la copia de seguridad. El artefacto joblib requiere las versiones de requirements.txt y que src esté en sys.path para cargar estimadores. Se detiene aquí; Power BI corresponde a una fase posterior.\n'
    path.write_text(texto, encoding='utf-8')


def main():
    GRAFICAS.mkdir(exist_ok=True)
    sns.set_theme(style='whitegrid', context='notebook')
    plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'font.family': 'DejaVu Sans'})
    datos = pd.read_csv(CLEAN/'datos_limpios.csv')
    pred = pd.read_csv(CLEAN/'predicciones_prueba.csv')
    info = json.loads((CLEAN/'metadatos_modelado.json').read_text(encoding='utf-8'))
    fig, ax = plt.subplots(figsize=(10, 5))
    frecuencias = datos.total_goles.value_counts().sort_index()
    ax.bar(frecuencias.index, frecuencias, color='#157f8c')
    ax.axvline(2.5, color='#d28a20', ls='--', label='Umbral Over 2.5')
    ax.set(xlabel='Goles totales', ylabel='Partidos', title='Distribución de goles · 3.198 partidos históricos')
    ax.legend(); guardar(fig, 'distribucion_goles.png')

    fig, ax = plt.subplots(figsize=(9, 5))
    tasas = datos.groupby('liga').over25.agg(['mean', 'size'])
    bars = ax.bar(tasas.index, tasas['mean']*100, color=['#157f8c','#8254a1','#d28a20'])
    ax.bar_label(bars, labels=[f'{r["mean"]:.1%} · n={int(r["size"])}' for _,r in tasas.iterrows()], padding=6)
    ax.set(ylim=(0, 85), ylabel='% Over 2.5', title='Over por liga · temporadas 2023-24 a 2025-26')
    guardar(fig, 'over_por_liga.png')

    equipos = pd.concat([datos[['liga','local','over25']].rename(columns={'local':'equipo'}),
                         datos[['liga','visitante','over25']].rename(columns={'visitante':'equipo'})])
    fig, axes = plt.subplots(1, 3, figsize=(19, 12), layout='constrained')
    for ax, (liga, grupo) in zip(axes, equipos.groupby('liga')):
        t = grupo.groupby('equipo').over25.agg(['mean','size']).sort_values('mean')
        ax.barh([f'{s} (n={int(n)})' for s,n in zip(t.index,t['size'])], t['mean']*100, color='#157f8c')
        ax.set(xlim=(0,100), xlabel='% Over 2.5', title=liga)
        ax.tick_params(axis='y', labelsize=8)
    fig.suptitle('Over por equipo · todos los históricos · muestra indicada por equipo', fontsize=15)
    guardar(fig, 'over_por_equipo.png')

    fig, axes = plt.subplots(2, 2, figsize=(10, 9), layout='constrained')
    for ax, nombre in zip(axes.flat, NOMBRES):
        t = pred[pred.modelo.eq(nombre)]
        sns.heatmap(confusion_matrix(t.over25,t.prediccion_over25, labels=[0,1]), annot=True,
                    fmt='d', cmap='Blues', cbar=False, ax=ax, xticklabels=['Under','Over'], yticklabels=['Under','Over'])
        ax.set(title=nombre, xlabel='Predicción', ylabel='Resultado real')
    fig.suptitle('Matrices de confusión · prueba 2025-26 · n=1.008 por modelo')
    guardar(fig, 'matrices_confusion.png')

    fig, ax = plt.subplots(figsize=(8, 7))
    for nombre in NOMBRES:
        t = pred[pred.modelo.eq(nombre)]
        fpr, tpr, _ = roc_curve(t.over25,t.probabilidad_over25)
        ax.plot(fpr,tpr,color=COLORES[nombre], label=f'{nombre} · AUC {roc_auc_score(t.over25,t.probabilidad_over25):.3f}')
    ax.plot([0,1],[0,1],'k--',alpha=.4)
    ax.set(xlabel='Tasa de falsos positivos',ylabel='Tasa de verdaderos positivos',title='Curvas ROC · prueba 2025-26')
    ax.legend(loc='lower right'); guardar(fig, 'curvas_roc.png')

    imp = pd.read_csv(CLEAN/'importancia_variables.csv')
    fig, axes = plt.subplots(3,1,figsize=(13,16),layout='constrained')
    for ax,nombre in zip(axes,NOMBRES[1:]):
        t = imp[imp.modelo.eq(nombre)].nlargest(12,'aumento_log_loss').sort_values('aumento_log_loss')
        ax.barh(t.variable,t.aumento_log_loss,xerr=t.desviacion,color=COLORES[nombre],alpha=.85)
        ax.axvline(0,color='black',lw=.7)
        ax.set(title=nombre,xlabel='Aumento de log loss al permutar · media ± desviación (8 repeticiones)')
    fig.suptitle('Importancia por permutación · validación interna final, no test',fontsize=15)
    guardar(fig, 'importancia_variables.png')

    fig, ax = plt.subplots(figsize=(8,7))
    for nombre in NOMBRES:
        t = pred[pred.modelo.eq(nombre)]
        real, media = calibration_curve(t.over25,t.probabilidad_over25,n_bins=8,strategy='quantile')
        ax.plot(media,real,'o-',label=nombre,color=COLORES[nombre])
    ax.plot([0,1],[0,1],'k--',alpha=.4,label='Calibración ideal')
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Probabilidad Over predicha',ylabel='Fracción Over observada',title='Calibración · prueba 2025-26 · hasta 8 grupos de igual frecuencia')
    ax.legend(); guardar(fig,'calibracion.png')

    t = pred[pred.modelo.eq(info['seleccionado'])].copy()
    fig, axes = plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for valor, label, color in [(0,'Under real','#157f8c'),(1,'Over real','#d28a20')]:
        axes[0].hist(t.loc[t.over25.eq(valor),'probabilidad_over25'],bins=np.linspace(0,1,21),alpha=.6,label=label,color=color)
    axes[0].set(xlabel='Probabilidad Over predicha',ylabel='Partidos',title='Distribución según resultado real')
    axes[0].legend()
    t['grupo'] = pd.qcut(t.probabilidad_over25,q=8,duplicates='drop')
    grupos = t.groupby('grupo',observed=True).agg(predicha=('probabilidad_over25','mean'),real=('over25','mean'),n=('over25','size'))
    axes[1].plot(grupos.predicha,grupos.real,'o-',color='#8254a1')
    axes[1].text(.03,.94,f'{len(grupos)} grupos · {grupos.n.min()}–{grupos.n.max()} partidos por grupo',
                 transform=axes[1].transAxes,fontsize=9,va='top')
    axes[1].plot([0,1],[0,1],'k--',alpha=.4)
    axes[1].set(xlim=(0,1),ylim=(0,1),xlabel='Probabilidad media predicha',ylabel='Proporción Over real',title='Probabilidad frente al resultado agregado')
    fig.suptitle(f"{info['seleccionado']} · seleccionado por CV · prueba 2025-26")
    guardar(fig,'probabilidad_resultado.png')
    info['fase'] = 'fase5_completa'
    (CLEAN/'metadatos_modelado.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    reporte(info)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(RAIZ/'informe/scraping.log',encoding='utf-8')])
    logging.info('FASE 5 COMPLETA: ocho gráficas; 70 fixtures, 19 sin predicción; detener antes de Power BI')
    print('Fase 5: ocho PNG y reporte consolidado; 70 fixtures, 19 sin predicción.')


if __name__ == '__main__':
    main()
