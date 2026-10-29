"""Pegar completo en un visual Python de Power BI Desktop.

Valores (No resumir): id_prediccion, modelo (dim_modelo), resultado_over25,
probabilidad_over25 (partidos_predicciones). id_prediccion evita que Power BI
colapse partidos con idénticos resultados/probabilidades. No se lee ningún CSV
ni se entrena un modelo: solo se usa el DataFrame `dataset` suministrado.
"""
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve

plt.rcParams.update({
    'font.family':'Segoe UI', 'font.size':11,
    'figure.facecolor':'#111E30', 'axes.facecolor':'#111E30',
    'text.color':'#F3F7FC', 'axes.labelcolor':'#A9B8CC',
    'xtick.color':'#A9B8CC', 'ytick.color':'#A9B8CC',
    'axes.edgecolor':'#293B52', 'grid.color':'#293B52',
    'legend.facecolor':'#111E30', 'legend.edgecolor':'#293B52'
})
colores={'Línea base':'#91A5BF','Regresión logística':'#54AAFF',
         'Random Forest':'#35D9B0','XGBoost':'#B69CFF'}
fig, ax = plt.subplots(figsize=(8, 5))
columnas = ['id_prediccion', 'modelo', 'resultado_over25', 'probabilidad_over25']
faltantes = set(columnas) - set(dataset.columns)
if faltantes:
    ax.text(.5, .5, 'Añadir al visual: '+', '.join(sorted(faltantes)), ha='center', va='center', wrap=True)
    ax.set_axis_off()
else:
    datos = dataset[columnas].drop_duplicates('id_prediccion').copy()
    for c in ['resultado_over25','probabilidad_over25']:
        datos[c] = pd.to_numeric(datos[c], errors='coerce')
    datos = datos.dropna(subset=['resultado_over25','probabilidad_over25'])
    for nombre, grupo in datos.groupby('modelo'):
        if len(grupo) < 2:
            continue
        real, predicha = calibration_curve(grupo.resultado_over25, grupo.probabilidad_over25,
                                           n_bins=min(8, len(grupo)), strategy='quantile')
        ax.plot(predicha, real, 'o-', color=colores.get(nombre,'#5DDBE6'), label=f'{nombre} (n={len(grupo)})')
    ax.plot([0,1], [0,1], '--', color='#FFCB66', label='Calibración ideal')
    ax.set(xlim=(0,1), ylim=(0,1), xlabel='Probabilidad Over predicha',
           ylabel='Fracción Over observada', title='Calibración sobre partidos de prueba filtrados')
    if datos.empty:
        ax.text(.5,.3,'Sin partidos de prueba en este filtro',ha='center')
    ax.legend(fontsize=8)
    ax.grid(alpha=.2)
fig.tight_layout()
plt.show()
