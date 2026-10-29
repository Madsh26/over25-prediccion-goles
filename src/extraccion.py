"""Extracción secuencial, limitada y reanudable de Flashscore.

Primero inventaría las nueve temporadas y los fixtures para controlar el
límite agregado ANTES de solicitar miles de fichas. No hay paralelismo de red.
"""
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
    EXTRAER, pausa, comprobar_bloqueo, guardar_csv, DetenerExtraccion, reemplazar,
)

LOG = logging.getLogger('flashscore')
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


def evidencia(page, nombre):
    """DOM comprimido, sin ejecutar su contenido; URL y hash en metadatos."""
    import gzip
    contenido = page.content().encode('utf-8')
    with gzip.open(EVIDENCIA / 'ultima_pagina.html.gz', 'wb') as f:
        f.write(contenido)
    return hashlib.sha256(contenido).hexdigest()


def navegar(page, url):
    from playwright.sync_api import Error
    for intento in range(3):
        pausa()
        try:
            r = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            status = r.status if r else None
            comprobar_bloqueo(page, status)
            if status and status >= 400:
                raise RuntimeError(f'HTTP {status}: {url}')
            return
        except DetenerExtraccion:
            raise
        except (Error, RuntimeError) as exc:
            LOG.warning('Navegación intento %s/3: %s', intento+1, exc)
            try:
                comprobar_bloqueo(page)
            except DetenerExtraccion:
                raise
            except Error:
                pass
            if intento == 2:
                raise DetenerExtraccion(f'URL no carga después de reintentos: {url}') from exc
            time.sleep(5 * 2 ** intento)


def verificar_identidad(page, liga, temporada):
    nombre = page.locator('.heading__name').inner_text(timeout=20000)
    periodo = page.locator('.heading__info').inner_text(timeout=20000)
    if LIGAS[liga][0].casefold() not in nombre.casefold():
        raise DetenerExtraccion(f'Liga incorrecta: {nombre!r}; esperada {LIGAS[liga][0]}')
    if temporada.replace('-', '/') not in periodo:
        raise DetenerExtraccion(f'Temporada incorrecta: {periodo!r}; esperada {temporada}')


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


def inventariar(page, liga, temporada, fixtures=False):
    from playwright.sync_api import TimeoutError as PWTimeout
    sufijo = '_fixtures' if fixtures else ''
    archivo = RAW/f'{liga}_{temporada}{sufijo}.csv'
    previo = {r['id_partido']:r for r in leer(archivo)}
    ruta = LIGAS[liga][1]
    url = (f'https://www.flashscore.com/football/{ruta}/fixtures/' if fixtures else
           f'https://www.flashscore.com/football/{ruta}-{temporada}/results/')
    # Un inventario completo y certificado puede reutilizarse para reanudar.
    clave = f'{liga}_{temporada}{sufijo}'
    sello = EVIDENCIA / 'inventario.json'
    registro = json.loads(sello.read_text(encoding='utf-8')) if sello.exists() else {}
    if clave in registro and previo:
        cert = registro[clave]
        if cert.get('inventario_completo') and cert.get('fecha_bogota') == ahora()[:10]:
            validar_basicos(list(previo.values()),liga,temporada,fixtures)
            LOG.info('Inventario reutilizado %s %s: %s',liga,temporada,len(previo))
            return list(previo.values())
    for intento in range(3):
        navegar(page,url)
        rechazar = page.get_by_role('button',name='Reject All',exact=True)
        try:
            rechazar.wait_for(state='visible',timeout=3000)
            rechazar.click()
        except PWTimeout:
            pass
        verificar_identidad(page,liga,temporada)
        try:
            page.locator('[id^="g_1_"]').first.wait_for(timeout=25000)
        except PWTimeout:
            comprobar_bloqueo(page)
            if fixtures and re.search(r'no matches found|no matches',page.locator('main').inner_text(),re.I):
                guardar_csv(archivo,[])
                registro[clave]={'url':url,'filas':0,'fecha_bogota':ahora()[:10],
                                 'inventario_completo':True}
                sello.write_text(json.dumps(registro,ensure_ascii=False,indent=2),encoding='utf-8')
                return []
            if intento == 2:
                raise DetenerExtraccion(f'No se cargan partidos: {url}')
            time.sleep(5*2**intento)
            continue
        agotada = False
        for carga in range(16):
            comprobar_bloqueo(page)
            brutas = page.evaluate(EXTRAER)
            nuevas = normalizar_lista(brutas,liga,temporada,fixtures)
            # Nunca elimina partidos ya obtenidos al escribir una carga parcial.
            fusion = dict(previo)
            for r in nuevas:
                fusion[r['id_partido']] = dict(fusion.get(r['id_partido'],{}),**r)
            rows = list(fusion.values())
            total = len(conteo_global() | set(fusion))
            estado(fase='inventario',liga=liga,temporada=temporada,filas_cargadas=len(nuevas),total_proyectado=total)
            historicos_ids = set()
            for clave in LIGAS:
                for periodo in TEMPORADAS:
                    historicos_ids.update(r['id_partido'] for r in leer(RAW/f'{clave}_{periodo}.csv'))
            if not fixtures:
                historicos_ids.update(fusion)
            if len(historicos_ids) > MAX_FILAS:
                # Conserva solo evidencia y diagnóstico; NO trunca ni guarda >4000 filas.
                evidencia(page,f'limite_{liga}_{temporada}')
                raise DetenerExtraccion(f'Límite histórico excedido: {len(historicos_ids)}; máximo {MAX_FILAS}. Fixtures exentos.')
            guardar_csv(archivo,rows)
            LOG.info('Inventario %s %s carga=%s visibles=%s guardados=%s total=%s',liga,temporada,carga,len(nuevas),len(rows),total)
            boton = page.get_by_role('button',name='Show more matches',exact=True)
            if not boton.count():
                agotada = True
                break
            pausa()
            boton.click()
            try:
                page.wait_for_function('(n)=>document.querySelectorAll(\'[id^="g_1_\"]\').length > n',arg=len(brutas),timeout=30000)
            except PWTimeout:
                comprobar_bloqueo(page)
                LOG.warning('Mostrar más no creció; se reintentará inventario %s %s',liga,temporada)
                break
        if (fixtures and agotada) or (not fixtures and len(nuevas) == LIGAS[liga][2]):
            validar_basicos(nuevas,liga,temporada,fixtures)
            # Tras verificar la lista COMPLETA, conservar solo sus IDs actuales.
            # La unión incremental protege la reanudación, pero no debe retener
            # fixtures que ya desaparecieron por haberse jugado al reejecutar.
            rows=[fusion[r['id_partido']] for r in nuevas]
            guardar_csv(archivo,rows)
            sha = evidencia(page,f'{liga}_{temporada}{sufijo}')
            registro[clave]={'url':url,'filas':len(nuevas),'sha256_html':sha,
                'fecha_bogota':ahora()[:10],'inventario_completo':True}
            sello.write_text(json.dumps(registro,ensure_ascii=False,indent=2),encoding='utf-8')
            return rows
        LOG.warning('Temporada incompleta %s %s: %s; intento %s/3',liga,temporada,len(nuevas),intento+1)
        previo = {r['id_partido']:r for r in rows}
        time.sleep(5*2**intento)
    raise DetenerExtraccion(f'Temporada incompleta tras reintentos: {liga} {temporada}')


def cobertura(rows):
    if not rows:
        return {campo:None for campo in STATS.values()}
    return {campo:round(100*sum(all(r.get(f'{campo}_{lado}') not in ('',None) for lado in ('local','visitante')) for r in rows)/len(rows),3)
            for campo in STATS.values()}


