"""Fase 2: limpieza sin imputar estadísticas ni fabricar resultados.

Solo se ejecuta cuando el scraper certifica que terminó y pasó controles.
Usa la biblioteca estándar de Python y archivos canónicos de liga/temporada.
"""
import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import date

from extraccion import RAIZ, RAW, LIGAS, TEMPORADAS, TEMPORADA_FIXTURES, MAX_FILAS, STATS, leer
from config import guardar_csv

ALIASES = {
    'Manchester Utd':'Manchester United', 'Sheffield Utd':'Sheffield United',
    'Nottingham':'Nottingham Forest', 'Wolves':'Wolverhampton Wanderers',
    'Tottenham':'Tottenham Hotspur', 'Leeds':'Leeds United',
    'Ath Bilbao':'Athletic Club',
}


def nombre(valor):
    texto=re.sub(r'\s+',' ',unicodedata.normalize('NFKC',valor or '')).strip()
    return ALIASES.get(texto,texto)


def limpiar_fila(r):
    salida={k:r.get(k) for k in ('id_partido','liga','temporada','fecha','jornada','tipo','url_partido')}
    salida.update(local=nombre(r['local']),visitante=nombre(r['visitante']))
    salida['fecha']=date.fromisoformat(r['fecha']).isoformat()
    salida['jornada']=int(r['jornada'])
    fixture = r.get('tipo')=='fixture'
    for campo in ('goles_local','goles_visitante'):
        salida[campo]=None if fixture else int(r[campo])
    salida['total_goles']=None if fixture else salida['goles_local']+salida['goles_visitante']
    salida['over25']=None if fixture else int(salida['total_goles']>=3)
    for campo in STATS.values():
        for lado in ('local','visitante'):
            col=f'{campo}_{lado}'
            v=r.get(col)
            numero=None if v in (None,'') else float(v)
            if numero is not None:
                if numero<0 or (campo=='posesion' and numero>100):
                    raise ValueError(f'Valor fuera de rango {r["id_partido"]} {col}: {v}')
                if campo!='posesion':
                    if not numero.is_integer():
                        raise ValueError(f'Conteo fraccionario {col}: {v}')
                    numero=int(numero)
            salida[col]=numero
    return salida


def main():
    certificado=json.loads((RAIZ/'informe/estado_extraccion.json').read_text(encoding='utf-8'))
    if certificado.get('fase') not in ('scraping_completo','fase3_completa','fase5_completa','fase7_completa'):
        raise RuntimeError('Scraping sin completar/certificar: no se inicia la limpieza.')
    destino=RAIZ/'data/clean'
    destino.mkdir(parents=True,exist_ok=True)
    resultados,fixtures,calidad=[],[],[]
    ids=set()
    descartados=[]
    for liga in LIGAS:
        for temporada in (*TEMPORADAS,TEMPORADA_FIXTURES):
            fixture=temporada==TEMPORADA_FIXTURES
            sufijo='_fixtures' if fixture else ''
            rows=leer(RAW/f'{liga}_{temporada}{sufijo}.csv')
            limpias=[]
            for r in rows:
                if r['id_partido'] in ids:
                    descartados.append({'id_partido':r['id_partido'],'motivo':'id_duplicado'})
                    continue
                ids.add(r['id_partido'])
                limpia=limpiar_fila(r)
                if not limpia['local'] or not limpia['visitante'] or limpia['local']==limpia['visitante']:
                    raise ValueError(f'Equipos inválidos: {r["id_partido"]}')
                limpias.append(limpia)
            if not fixture and len(limpias)!=LIGAS[liga][2]:
                raise ValueError(f'Conteo tras limpieza no esperado {liga} {temporada}: {len(limpias)}')
            (fixtures if fixture else resultados).extend(limpias)
            for campo in limpias[0] if limpias else []:
                nulos=sum(r[campo] in ('',None) for r in limpias)
                calidad.append({'liga':LIGAS[liga][0],'temporada':temporada,'tipo':'fixture' if fixture else 'resultado',
                                'campo':campo,'filas':len(limpias),'nulos':nulos,
                                'porcentaje_nulos':round(100*nulos/len(limpias),3)})
    if len(resultados)>MAX_FILAS:
        raise ValueError(f'Máximo histórico excedido: {len(resultados)}')
    resultados.sort(key=lambda r:(r['fecha'],r['liga'],r['id_partido']))
    fixtures.sort(key=lambda r:(r['fecha'],r['liga'],r['id_partido']))
    guardar_csv(destino/'datos_limpios.csv',resultados)
    guardar_csv(destino/'fixtures_limpios.csv',fixtures)
    guardar_csv(destino/'calidad_datos.csv',calidad)
    if descartados:
        guardar_csv(destino/'duplicados_descartados.csv',descartados)
    resumen={'filas_historicas':len(resultados),'filas_fixtures':len(fixtures),
             'duplicados_descartados':len(descartados),'tarjetas':'excluidas; sin asociación tabular validada',
             'por_liga_temporada':dict(Counter(f'{r["liga"]}|{r["temporada"]}' for r in resultados+fixtures)),
             'imputacion':'ninguna; las estadísticas ausentes permanecen nulas'}
    (destino/'resumen_limpieza.json').write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Limpieza: {len(resultados)} históricos, {len(fixtures)} fixtures; {len(descartados)} duplicados.')


if __name__=='__main__':
    main()
