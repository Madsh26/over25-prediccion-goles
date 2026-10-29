"""Utilidades de lectura, estado y validación de los datos del proyecto (la extracción no se publica)."""
import csv
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, parse_qs

from config import (
    RAIZ, RAW, LIGAS, TEMPORADAS, TEMPORADA_FIXTURES, MAX_FILAS,
    guardar_csv, DetenerExtraccion, reemplazar,
)

LOG = logging.getLogger('over25')
EVIDENCIA = RAW / 'evidencia'
ESTADO = RAIZ / 'informe' / 'estado_extraccion.json'
BOGOTA = timezone(timedelta(hours=-5), 'America/Bogota')
STATS = {'Total shots':'tiros', 'Shots on target':'tiros_arco',
         'Ball possession':'posesion', 'Corner kicks':'corners'}
CAMPOS = ['fecha','jornada','local','visitante','goles_local','goles_visitante']


def ahora():
    return datetime.now(BOGOTA).isoformat(timespec='seconds')


def leer(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def estado(**datos):
    datos['actualizado'] = ahora()
    tmp = ESTADO.with_suffix('.tmp')
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
    reemplazar(tmp,ESTADO)








def normalizar_lista(rows, liga, temporada, fixtures=False):
    salida = []
    inicio = int(temporada[:4])
    for original in rows:
        r = dict(original)
        # Flashscore mezcla la eliminatoria de permanencia en esta página.
        # El alcance de 306 es únicamente liga regular (34 jornadas).
        if liga=='bundesliga' and (r['jornada_original'] or '').strip().casefold()=='final':
            LOG.info('Excluido playoff de permanencia fuera de alcance: %s',r['id_partido'])
            continue
        texto = r['fecha_original'] or ''
        # Resultados: DD.MM.AAAA; fixtures: DD.MM. HH:MM sin año.
        m = re.search(r'\b(\d{2})\.(\d{2})\.(\d{4})\b', texto)
        if m:
            dia, mes, anio = map(int, m.groups())
        else:
            m = re.search(r'\b(\d{2})\.(\d{2})\.', texto)
            if not m:
                raise DetenerExtraccion(f'Fecha no interpretable: {texto!r}')
            dia, mes = map(int, m.groups())
            anio = inicio if mes >= 7 else inicio+1
        fecha = datetime(anio,mes,dia).date().isoformat()
        if not f'{inicio}-07-01' <= fecha <= f'{inicio+1}-06-30':
            raise DetenerExtraccion(f'Partido fuera de temporada: {fecha} ({temporada})')
        j = re.search(r'\d+', r['jornada_original'] or '')
        r.update(liga=LIGAS[liga][0], temporada=f'{inicio}-{str(inicio+1)[-2:]}',
                 fecha=fecha, jornada=int(j.group()) if j else None,
                 tipo='fixture' if fixtures else 'resultado', extraido_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                 anio_fecha_origen='inferido_de_temporada_y_mes' if not re.search(r'\d{4}',texto) else 'explicito')
        if not r['local'] or not r['visitante'] or not r['jornada']:
            raise DetenerExtraccion(f'Campos básicos incompletos: {r["id_partido"]}')
        if fixtures:
            # La página fixtures debe contener solo encuentros sin marcador.
            if any(str(r[c]).isdigit() for c in ('goles_local','goles_visitante')):
                raise DetenerExtraccion('La página fixtures contiene un marcador: revisar alcance.')
            r.update(goles_local=None,goles_visitante=None,total_goles=None,over25=None)
            hm = re.search(r'(\d{2}):(\d{2})',texto)
            r['hora_bogota'] = hm.group() if hm else None
            if fecha < ahora()[:10]:
                raise DetenerExtraccion(f'Fixture en fecha pasada: {r["id_partido"]}, {fecha}')
        else:
            for c in ('goles_local','goles_visitante'):
                if not str(r[c]).isdigit():
                    raise DetenerExtraccion(f'Marcador no verificable: {r["id_partido"]}')
                r[c] = int(r[c])
            r['total_goles'] = r['goles_local'] + r['goles_visitante']
            r['over25'] = int(r['total_goles'] >= 3)
        salida.append(r)
    return salida


def conteo_global():
    """Solo archivos canónicos: excluye muestras y copias del piloto."""
    ids = set()
    for liga in LIGAS:
        for temporada in (*TEMPORADAS, TEMPORADA_FIXTURES):
            sufijo = '_fixtures' if temporada == TEMPORADA_FIXTURES else ''
            for r in leer(RAW/f'{liga}_{temporada}{sufijo}.csv'):
                ids.add(r['id_partido'])
    return ids


def validar_basicos(rows, liga, temporada, fixtures=False):
    if len(rows) != len({r['id_partido'] for r in rows}):
        raise DetenerExtraccion(f'IDs duplicados: {liga} {temporada}')
    for r in rows:
        for c in CAMPOS[:4] if fixtures else CAMPOS:
            if r.get(c) in (None,''):
                raise DetenerExtraccion(f'Nulo en {c}: {liga} {temporada}')
        if not fixtures:
            total = int(r['goles_local']) + int(r['goles_visitante'])
            if int(r['total_goles']) != total or int(r['over25']) != int(total>=3):
                raise DetenerExtraccion(f'Goles/objetivo incoherentes: {r["id_partido"]}')
    if not fixtures and len(rows) != LIGAS[liga][2]:
        raise DetenerExtraccion(f'Conteo incorrecto: {liga} {temporada}: {len(rows)}/{LIGAS[liga][2]}')




def cobertura(rows):
    if not rows:
        return {campo:None for campo in STATS.values()}
    return {campo:round(100*sum(all(r.get(f'{campo}_{lado}') not in ('',None) for lado in ('local','visitante')) for r in rows)/len(rows),3)
            for campo in STATS.values()}


