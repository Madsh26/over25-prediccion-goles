"""Fase 3: ventanas históricas con exclusión estricta de la misma fecha.

Se procesa cada fecha en dos pasos: primero calcular, después actualizar
historiales. Es equivalente a rolling + shift(1), reforzado para excluir
todos los encuentros del mismo día cuando se desconoce la hora real.
"""
import json
import math
from collections import defaultdict, Counter
from itertools import groupby
from statistics import mean
from datetime import date

from extraccion import RAIZ, STATS, leer
from config import guardar_csv

MIN_HISTORIAL=10
MIN_HISTORIAL_SEDE=5
VENTANAS=(5,10)


def valor(v):
    return None if v in (None,'') else float(v)


def resumen_equipo(historial, sede):
    """Ventanas recientes; estadísticas con mínimo 80% de observaciones."""
    datos={}
    subconjuntos={'general':historial,'sede':[h for h in historial if h['sede']==sede]}
    for grupo,items in subconjuntos.items():
        for ventana in VENTANAS:
            seleccion=items[-ventana:]
            prefijo=f'{grupo}_{ventana}'
            datos[f'{prefijo}_n']=len(seleccion)
            for campo in ('gf','gc','over25',*STATS.values()):
                disponibles=[h[campo] for h in seleccion if h[campo] is not None]
                suficiente=len(disponibles)>=math.ceil(0.8*len(seleccion)) and bool(seleccion)
                datos[f'{prefijo}_{campo}']=round(mean(disponibles),6) if suficiente else None
    return datos


def main():
    carpeta=RAIZ/'data/clean'
    historicos=leer(carpeta/'datos_limpios.csv')
    fixtures=leer(carpeta/'fixtures_limpios.csv')
    # Conservar todos los fixtures canónicos, preparar features solo para las
    # tres jornadas pendientes más próximas de cada liga.
    jornadas={}
    for liga in sorted({r['liga'] for r in fixtures}):
        partidos=[r for r in fixtures if r['liga']==liga]
        primera_fecha=min(r['fecha'] for r in partidos)
        # Jornada en curso/próxima en la primera fecha pendiente. Un aplazado
        # de una ronda anterior no consume una de las tres rondas consecutivas.
        inicial=max(int(r['jornada']) for r in partidos if r['fecha']==primera_fecha)
        disponibles={int(r['jornada']) for r in partidos}
        jornadas[liga]=[j for j in range(inicial,inicial+3) if j in disponibles]
    fixtures=[r for r in fixtures if int(r['jornada']) in jornadas[r['liga']]]
    if not historicos:
        raise RuntimeError('Falta la limpieza completa; no se calculan características.')
    datos=sorted(historicos+fixtures,key=lambda r:(r['fecha'],r['id_partido']))
    historial=defaultdict(list)
    modelo,proximos,excluidos,auditoria=[],[],[],[]
    columnas_features=None
    for fecha,lote in groupby(datos,key=lambda r:r['fecha']):
        lote=list(lote)
        # Leer estado ANTES de actualizar cualquier partido de esta fecha.
        for r in lote:
            local=historial[(r['liga'],r['local'])]
            visitante=historial[(r['liga'],r['visitante'])]
            causas=[]
            for lado,h,sede in (('local',local,'local'),('visitante',visitante,'visitante')):
                if len(h)<MIN_HISTORIAL:
                    causas.append(f'{lado}:menos_de_{MIN_HISTORIAL}_partidos')
                if sum(x['sede']==sede for x in h)<MIN_HISTORIAL_SEDE:
                    causas.append(f'{lado}:menos_de_{MIN_HISTORIAL_SEDE}_en_sede')
                if h and h[-1]['fecha']>=fecha:
                    raise AssertionError(f'Fuga temporal detectada {r["id_partido"]} {lado}')
            base={c:r[c] for c in ('id_partido','liga','temporada','fecha','jornada','local','visitante')}
            base['over25']=None if r['tipo']=='fixture' else int(r['over25'])
            base['historial_suficiente']=int(not causas)
            base['motivo_exclusion']='; '.join(causas)
            auditoria.append({'id_partido':r['id_partido'],'fecha':fecha,
                              'ultima_fecha_local':local[-1]['fecha'] if local else None,
                              'ultima_fecha_visitante':visitante[-1]['fecha'] if visitante else None,
                              'n_historial_local':len(local),'n_historial_visitante':len(visitante),
                              'historial_suficiente':int(not causas)})
            if causas and r['tipo']!='fixture':
                excluidos.append({**base,'tipo':'resultado'})
                continue
            features={}
            for lado,h,sede in (('local',local,'local'),('visitante',visitante,'visitante')):
                features.update({f'{lado}_{k}':v for k,v in resumen_equipo(h,sede).items()})
                features[f'{lado}_dias_desde_ultimo']=(date.fromisoformat(fecha)-date.fromisoformat(h[-1]['fecha'])).days if h else None
            for grupo in ('general','sede'):
                for ventana in VENTANAS:
                    for campo in ('gf','gc','over25',*STATS.values()):
                        sufijo=f'{grupo}_{ventana}_{campo}'
                        a,b=features[f'local_{sufijo}'],features[f'visitante_{sufijo}']
                        features[f'diferencia_{sufijo}']=round(a-b,6) if a is not None and b is not None else None
            columnas_features=list(features)
            (proximos if r['tipo']=='fixture' else modelo).append({**base,**features})
        # Actualizar únicamente con resultados reales y después de calcular el día.
        for r in lote:
            if r['tipo']=='fixture':
                continue
            for lado,opuesto in (('local','visitante'),('visitante','local')):
                registro={'fecha':fecha,'sede':lado,'gf':int(r[f'goles_{lado}']),
                          'gc':int(r[f'goles_{opuesto}']),'over25':int(r['over25'])}
                registro.update({campo:valor(r.get(f'{campo}_{lado}')) for campo in STATS.values()})
                historial[(r['liga'],r[lado])].append(registro)
    guardar_csv(carpeta/'dataset_modelo.csv',modelo)
    guardar_csv(carpeta/'dataset_fixtures_features.csv',proximos)
    guardar_csv(carpeta/'filas_sin_historial.csv',excluidos)
    guardar_csv(carpeta/'auditoria_temporal.csv',auditoria)
    descripcion={'features_numericas':columnas_features,'variable_categorica':'liga','objetivo':'over25',
                 'metadatos_excluir_del_modelo':['id_partido','temporada','fecha','jornada','local','visitante','historial_suficiente','motivo_exclusion'],
                 'ventanas':list(VENTANAS),'min_partidos_general':MIN_HISTORIAL,'min_partidos_sede':MIN_HISTORIAL_SEDE,
                 'sede_10':'Promedio de hasta 10 partidos previos en esa sede; mínimo 5. Se entrega el número observado.',
                 'estadisticas_nulas':'Ventana con menos de 80% de datos: nula. Imputador se ajustará solo en entrenamiento.',
                 'prevencion_fuga':'Historial de fecha estrictamente menor; partidos del mismo día excluidos; no se reinicia entre temporadas.',
                 'fixtures':'Historial congelado al último resultado permitido; no se incorporan resultados 2026-27 ni otros fixtures.',
                 'filas_modelo':len(modelo),'filas_descartadas_historial':len(excluidos),
                 'filas_fixtures':len(proximos),'fixtures_sin_historial':sum(not r['historial_suficiente'] for r in proximos),
                 'modelo_por_liga_temporada':dict(Counter(f'{r["liga"]}|{r["temporada"]}' for r in modelo)),
                 'descartadas_por_liga_temporada':dict(Counter(f'{r["liga"]}|{r["temporada"]}' for r in excluidos)),
                 'estado':'Fase 3 completa; pendiente revisión del usuario antes de entrenar'}
    descripcion['jornadas_fixtures_seleccionadas']=jornadas
    descripcion['criterio_horizonte']='Jornada inicial de la primera fecha pendiente, seguida de dos jornadas consecutivas; aplazados anteriores quedan fuera del horizonte, pero se conservan en fixtures_limpios.csv.'
    descripcion['unidades']={'posesion':'porcentaje 0–100','over25_historico':'proporción 0–1','goles_tiros_corners':'promedio por partido'}
    resumen_path=carpeta/'resumen_limpieza.json'
    metadatos_path=carpeta/'metadatos_modelo.json'
    if resumen_path.exists():
        descripcion['limpieza']=json.loads(resumen_path.read_text(encoding='utf-8'))
    elif metadatos_path.exists():
        anterior=json.loads(metadatos_path.read_text(encoding='utf-8'))
        if 'limpieza' in anterior:
            descripcion['limpieza']=anterior['limpieza']
    (carpeta/'metadatos_modelo.json').write_text(json.dumps(descripcion,ensure_ascii=False,indent=2),encoding='utf-8')
    if resumen_path.exists():
        resumen_path.unlink()
    print(f'Features: {len(modelo)} filas modelables; {len(excluidos)} excluidas; {len(proximos)} fixtures próximos.')


if __name__=='__main__':
    main()
