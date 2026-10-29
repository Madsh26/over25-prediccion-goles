"""Fase 6: exportación reproducible y comprobada, sin entrenar ni extraer otra vez.

Una fila de predicciones por partido/modelo. Dimensiones compartidas y un
puente de equipos permiten filtrar partidos como local O visitante sin duplicar
la tabla de predicciones. Todos los CSV son UTF-8 con BOM, coma y punto decimal.
"""
import json
import logging
import re
from pathlib import Path
import numpy as np
import pandas as pd
from config import RAIZ, reemplazar

CLEAN = RAIZ/'data/clean'
SALIDA = RAIZ/'powerbi'
MODELOS = {'Línea base': 0, 'Regresión logística': 1, 'Random Forest': 2, 'XGBoost': 3}
LIGAS = {'Todas': 0, 'Premier League': 1, 'LaLiga': 2, 'Bundesliga': 3}
TEMPORADAS = {'2023-24': 1, '2024-25': 2, '2025-26': 3, '2026-27': 4}


def exportar(df, nombre):
    assert all(re.fullmatch('[a-z][a-z0-9_]*', c) for c in df.columns), nombre
    tmp = SALIDA/(nombre+'.tmp')
    df.to_csv(tmp, index=False, encoding='utf-8-sig', float_format='%.10g', lineterminator='\n')
    reemplazar(tmp, SALIDA/nombre)


def main():
    SALIDA.mkdir(exist_ok=True)
    info = json.loads((CLEAN/'metadatos_modelado.json').read_text(encoding='utf-8'))
    assert info['fase']=='fase5_completa' and info.get('verificacion_entregables')
    hist = pd.read_csv(CLEAN/'datos_limpios.csv')
    pred = pd.read_csv(CLEAN/'predicciones_prueba.csv')
    fut = pd.read_csv(CLEAN/'predicciones_fixtures.csv')
    metricas = pd.read_csv(CLEAN/'metricas.csv')
    importancia = pd.read_csv(CLEAN/'importancia_variables.csv')
    inventario = json.loads((RAIZ/'data/raw/evidencia/inventario.json').read_text(encoding='utf-8'))
    cortes = {v['fecha_bogota'] for k,v in inventario.items() if 'fixtures' in k}
    assert len(cortes)==1, 'Documentar cortes distintos antes de exportar.'
    corte = next(iter(cortes))
    max_hist = hist.fecha.max()

    dim_liga = pd.DataFrame([dict(id_liga=i, liga=n, es_total=int(i==0)) for n,i in LIGAS.items()])
    dim_modelo = pd.DataFrame([dict(id_modelo=i, modelo=n, es_linea_base=int(i==0),
                                   seleccionado_cv=int(n==info['seleccionado'])) for n,i in MODELOS.items()])
    dim_temporada = pd.DataFrame([dict(id_temporada=i, temporada=n,
                          uso='entrenamiento' if i<3 else ('prueba' if i==3 else 'fixtures')) for n,i in TEMPORADAS.items()])
    equipos = set()
    for df in [hist, fut]:
        for col in ['local','visitante']:
            equipos.update(zip(df.liga, df[col]))
    claves_equipo = {tupla:i for i,tupla in enumerate(sorted(equipos),1)}
    dim_equipo = pd.DataFrame([dict(id_equipo=i,id_liga=LIGAS[liga],equipo=equipo,
                                    equipo_liga=f'{equipo} ({liga})') for (liga,equipo),i in claves_equipo.items()])

    pred['id_modelo'] = pred.modelo.map(MODELOS)
    base = pred[pred.id_modelo.eq(0)].set_index('id_partido')
    p = pred.probabilidad_over25.clip(1e-15,1-1e-15)
    pred['perdida_logaritmica_partido'] = -(pred.over25*np.log(p)+(1-pred.over25)*np.log(1-p))
    pred['probabilidad_base'] = pred.id_partido.map(base.probabilidad_over25)
    pred['clase_base'] = pred.id_partido.map(base.prediccion_over25)
    pred['acierto_base'] = pred.id_partido.map(base.acierto)
    pb = pred.probabilidad_base.clip(1e-15,1-1e-15)
    pred['perdida_logaritmica_base'] = -(pred.over25*np.log(pb)+(1-pred.over25)*np.log(1-pb))
    pred['clase_real_texto'] = np.where(pred.over25.eq(1),'Over','Under')
    pred['clase_predicha_texto'] = np.where(pred.prediccion_over25.eq(1),'Over','Under')
    pred['id_prediccion'] = pred.id_partido+'|'+pred.id_modelo.astype(str)
    for df in [pred,fut]:
        df['id_liga'] = df.liga.map(LIGAS)
        df['id_temporada'] = df.temporada.map(TEMPORADAS)
        for lado in ['local','visitante']:
            df['id_equipo_'+lado] = [claves_equipo[(l,e)] for l,e in zip(df.liga,df[lado])]

    fact = pred.rename(columns={'over25':'resultado_over25','prediccion_over25':'clase_predicha'})[
        ['id_prediccion','id_partido','id_liga','id_temporada','id_modelo','fecha','jornada',
         'id_equipo_local','id_equipo_visitante','local','visitante','resultado_over25',
         'probabilidad_over25','clase_predicha','clase_real_texto','clase_predicha_texto','acierto',
         'seleccionado_cv','perdida_logaritmica_partido','probabilidad_base','clase_base',
         'acierto_base','perdida_logaritmica_base']]

    met = metricas.rename(columns={'n':'partidos','accuracy':'exactitud','recall':'sensibilidad',
                 'log_loss':'perdida_logaritmica','brier':'error_brier',
                 'delta_accuracy_vs_base':'diferencia_exactitud_base',
                 'delta_roc_auc_vs_base':'diferencia_roc_auc_base',
                 'delta_log_loss_vs_base':'diferencia_perdida_base'}).copy()
    met['id_liga'] = met.liga.map(LIGAS)
    met['id_modelo'] = met.modelo.map(MODELOS)
    met['id_temporada'] = met.temporada.map(TEMPORADAS)
    met = met.drop(columns=['liga','modelo','temporada'])

    fut['id_modelo'] = fut.modelo.map(MODELOS)
    fut['fecha_corte_fixtures'] = corte
    fut['fecha_max_historial'] = max_hist
    fut['clase_predicha_texto'] = np.where(fut.prediccion_over25.isna(),'sin predicción',
                                         np.where(fut.prediccion_over25.eq(1),'Over','Under'))
    fut['prediccion_over25'] = fut.prediccion_over25.astype('Int64')
    futuros = fut.rename(columns={'prediccion_over25':'clase_predicha'})[
        ['id_partido','id_liga','id_temporada','id_modelo','fecha','jornada','id_equipo_local',
         'id_equipo_visitante','local','visitante','historial_suficiente','motivo_exclusion',
         'estado_prediccion','probabilidad_over25','clase_predicha','clase_predicha_texto',
         'fecha_corte_fixtures','fecha_max_historial']]

    partes = []
    for lado, otro in [('local','visitante'),('visitante','local')]:
        t = hist[['liga','temporada',lado,'over25',f'goles_{lado}',f'goles_{otro}']].copy()
        t.columns=['liga','temporada','equipo','over25','goles_favor','goles_contra']
        partes.append(t)
    largo = pd.concat(partes,ignore_index=True)
    resumen = largo.groupby(['liga','temporada','equipo'],as_index=False).agg(
        partidos=('over25','size'),partidos_over25=('over25','sum'),
        goles_favor=('goles_favor','sum'),goles_contra=('goles_contra','sum'))
    resumen['proporcion_over25'] = resumen.partidos_over25/resumen.partidos
    resumen['goles_favor_promedio'] = resumen.goles_favor/resumen.partidos
    resumen['goles_contra_promedio'] = resumen.goles_contra/resumen.partidos
    resumen['goles_totales_promedio'] = (resumen.goles_favor+resumen.goles_contra)/resumen.partidos
    resumen['id_liga'] = resumen.liga.map(LIGAS)
    resumen['id_temporada'] = resumen.temporada.map(TEMPORADAS)
    resumen['id_equipo'] = [claves_equipo[(l,e)] for l,e in zip(resumen.liga,resumen.equipo)]
    resumen = resumen.drop(columns=['liga','temporada','equipo'])

    imp = importancia.rename(columns={'n':'partidos_validacion'}).copy()
    imp['id_modelo'] = imp.modelo.map(MODELOS)
    imp = imp.drop(columns='modelo')
    imp['fecha_min_validacion'] = pd.read_csv(CLEAN/'validacion_temporal.csv').iloc[-1].fecha_min_validacion
    imp['fecha_max_validacion'] = pd.read_csv(CLEAN/'validacion_temporal.csv').iloc[-1].fecha_max_validacion

    campos = ['id_partido','id_liga','id_temporada','fecha','jornada','id_equipo_local','id_equipo_visitante','local','visitante']
    dim_partido = pd.concat([fact[campos].drop_duplicates(),futuros[campos]],ignore_index=True)
    dim_partido['uso'] = np.where(dim_partido.id_temporada.eq(3),'prueba','fixtures')
    puente = pd.concat([dim_partido[['id_partido','id_equipo_'+lado]].rename(columns={'id_equipo_'+lado:'id_equipo'})
                        for lado in ['local','visitante']],ignore_index=True)
    tablas = {'partidos_predicciones.csv':fact, 'metricas_modelos.csv':met,
              'proximos_partidos.csv':futuros, 'equipos_resumen.csv':resumen,
              'importancia_variables.csv':imp,'dim_liga.csv':dim_liga,'dim_modelo.csv':dim_modelo,
              'dim_temporada.csv':dim_temporada,'dim_equipo.csv':dim_equipo,
              'dim_partido.csv':dim_partido,'puente_partido_equipo.csv':puente}
    validar(tablas,metricas)
    for nombre,df in tablas.items():
        exportar(df,nombre)
    # Comprueba lectura real de los CSV entregados, incluido el tratamiento de vacíos.
    recargadas = {n:pd.read_csv(SALIDA/n) for n in tablas}
    validar(recargadas,metricas)
    for nombre,df in recargadas.items():
        assert len(df)==len(tablas[nombre])
        for c in [c for c in df if c.startswith('fecha')]:
            assert df[c].astype(str).str.fullmatch(r'\d{4}-\d{2}-\d{2}').all(), (nombre,c)
    log = RAIZ/'informe/scraping.log'
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(log,encoding='utf-8')])
    logging.info('FASE 6 CSV comprobados: %s; corte fixtures %s; sin extracción ni entrenamiento nuevos',
                 {n:len(t) for n,t in tablas.items()},corte)
    actualizar_reporte(tablas,corte,max_hist)
    documentos = [RAIZ/'README.md', RAIZ/'informe/borrador_informe.md',
                  SALIDA/'guia_powerbi.md', SALIDA/'medidas.dax', SALIDA/'visual_calibracion.py']
    assert all(p.is_file() and p.stat().st_size>0 for p in documentos), 'Documentación de cierre incompleta.'
    from extraccion import estado
    estado(fase='fase7_completa',entrenamiento='completado',siguiente='construccion_pbix_por_estudiante',
           historicos=3198,fixtures=865,filas_modelo=2757,fixtures_horizonte=70,
           exportacion_powerbi='validada',pbix='pendiente_por_estudiante')
    print(f'Power BI: {len(tablas)} CSV; {len(fact)} predicciones de prueba; 70 fixtures (19 sin predicción); validación OK.')


def validar(t, origen):
    p, f = t['partidos_predicciones.csv'],t['proximos_partidos.csv']
    assert len(p)==4032 and p.id_partido.nunique()==1008
    assert not p.duplicated(['id_partido','id_modelo']).any()
    assert p.groupby('id_partido').id_modelo.nunique().eq(4).all()
    assert p.probabilidad_over25.between(0,1).all()
    assert np.array_equal(p.acierto,(p.clase_predicha==p.resultado_over25).astype(int))
    assert len(f)==70 and f.id_partido.is_unique
    sin=f.estado_prediccion.eq('sin predicción')
    assert sin.sum()==19 and f.loc[sin,['probabilidad_over25','clase_predicha']].isna().all().all()
    assert f.loc[~sin,'probabilidad_over25'].between(0,1).all()
    for n,key in [('dim_liga.csv','id_liga'),('dim_modelo.csv','id_modelo'),
                  ('dim_temporada.csv','id_temporada'),('dim_equipo.csv','id_equipo'),('dim_partido.csv','id_partido')]:
        assert t[n][key].is_unique and t[n][key].notna().all()
        permitidos=set(t[n][key])
        for nombre,df in t.items():
            if nombre!=n and key in df:
                assert df[key].notna().all() and set(df[key])<=permitidos,(nombre,key)
    puente=t['puente_partido_equipo.csv']
    assert not puente.duplicated().any() and puente.groupby('id_partido').size().eq(2).all()
    for df in [p,f,t['dim_partido.csv']]:
        for lado in ['local','visitante']:
            assert set(df['id_equipo_'+lado])<=set(t['dim_equipo.csv'].id_equipo)
    r=t['equipos_resumen.csv']
    assert r.partidos.sum()==6396 and (r.goles_favor.sum()==r.goles_contra.sum())
    assert not r.duplicated(['id_equipo','id_temporada']).any()
    for fila in t['metricas_modelos.csv'].itertuples():
        sel=p[p.id_modelo.eq(fila.id_modelo)]
        if fila.id_liga:
            sel=sel[sel.id_liga.eq(fila.id_liga)]
        assert len(sel)==fila.partidos==fila.tn+fila.fp+fila.fn+fila.tp
        np.testing.assert_allclose(sel.acierto.mean(),fila.exactitud,atol=1e-9)
        np.testing.assert_allclose(sel.perdida_logaritmica_partido.mean(),fila.perdida_logaritmica,atol=1e-8)
        for real,clase,col in [(0,0,'tn'),(0,1,'fp'),(1,0,'fn'),(1,1,'tp')]:
            assert ((sel.resultado_over25==real)&(sel.clase_predicha==clase)).sum()==getattr(fila,col)
    assert len(origen)==len(t['metricas_modelos.csv'])==16


def actualizar_reporte(tablas,corte,max_hist):
    from extraccion import ahora
    path=RAIZ/'informe/reporte_final.md'
    texto=path.read_text(encoding='utf-8').split('\n## Fases 6 y 7')[0]
    texto=re.sub(r'^Actualizado:.*$',f'Actualizado: {ahora()}.',texto,flags=re.MULTILINE)
    texto=texto.replace('# Reporte del proyecto hasta Fase 5','# Reporte del proyecto hasta Fase 7')
    texto=texto.replace('Estado: Fases 4 y 5 completas; detenido antes de Power BI.',
                        'Estado: Fases 6 y 7 completas. Preparación de Power BI entregada; el estudiante construirá el .pbix.')
    texto=texto.replace('Se detiene aquí; Power BI corresponde a una fase posterior.',
                        'Las Fases 6 y 7 se describen al final de este reporte.')
    texto=texto.replace('Se detiene el trabajo al terminar la Fase 5.',
                        'La Fase 5 fue aprobada por el estudiante antes de continuar a las Fases 6 y 7.')
    texto+='\n## Fases 6 y 7\n\nExportación validada en powerbi: nombres de columnas sin tildes ni espacios, UTF-8 con BOM, delimitador coma, punto decimal y fechas ISO. Se conservaron todos los CSV originales aprobados.\n\n| Tabla | Filas |\n|---|---:|\n'
    for n,df in tablas.items():
        texto+=f'| {n} | {len(df)} |\n'
    texto+=f'\nPrueba: 2025-26; 1.008 partidos únicos y cuatro modelos. Los totales de métricas son filas independientes de los desgloses y no deben sumarse con ellos. Snapshot de fixtures: {corte}; último resultado permitido para features: {max_hist}. Los pronósticos son de ese corte, no se han actualizado con resultados posteriores.\n'
    texto+='\nGuía, relaciones, tipos, diseño y comprobaciones: powerbi/guia_powerbi.md. Medidas listas para crear individualmente: powerbi/medidas.dax. Visual opcional: powerbi/visual_calibracion.py, con configuración explícita del intérprete. Se comprobó su ejecución con los datos exportados fuera de Desktop; las relaciones, DAX y el visual quedan pendientes de verificación en el .pbix que construirá el estudiante.\n'
    texto+='\nDocumentación: README.md renovado y borrador académico en informe/borrador_informe.md, con metodología, resultados por liga, limitaciones y anexos. No se entrega ni se afirma haber generado un .pbix. Anexo pendiente: powerbi/informe_over25.pbix, a guardar por el estudiante. No se generaron ZIP, versiones ni nuevas copias de seguridad.\n'
    texto+='\nReejecución de exportaciones: `.\\.venv\\Scripts\\python.exe -u src/powerbi.py`. Sobrescribe las mismas once tablas y actualiza este reporte. No vuelve a extraer ni ajustar modelos. Trabajo detenido al terminar la Fase 7.\n'
    path.write_text(texto,encoding='utf-8')


if __name__=='__main__':
    main()
