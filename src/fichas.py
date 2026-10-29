"""Extracción histórica con tres contextos como máximo y escritura única."""
import asyncio
import hashlib
import json
import logging
import random
import re
import time
from collections import deque
from urllib.parse import urlsplit,parse_qs,urlunsplit
from playwright.async_api import async_playwright,TimeoutError as PWTimeout,Error as PWError
from extraccion import RAIZ,RAW,LIGAS,TEMPORADAS,STATS,leer,ahora,estado,cobertura,validar_basicos,EVIDENCIA
from config import SEMILLA,guardar_csv,DetenerExtraccion

LOG=logging.getLogger('flashscore')
AD_DOMAINS=('doubleclick.net','googlesyndication.com','googletagmanager.com',
 'google-analytics.com','adnxs.com','scorecardresearch.com','ads.fs.lsapp.tech',
 'facebook.net','amazon-adsystem.com')


class Transitorio(RuntimeError):
    pass


class Control:
    def __init__(self):
        self.lento=False
        previo=RAIZ/'informe/estado_extraccion.json'
        if previo.exists():
            self.lento=json.loads(previo.read_text(encoding='utf-8')).get('paralelismo')==1
        self.errores=0
        self.estables=0
        self.fallos_lentos=0
        self.recientes=deque(maxlen=30)
        self.parar=asyncio.Event()
        self.incidentes=[]

    def fallo(self,motivo):
        self.errores+=1
        self.estables=0
        self.recientes.append(False)
        urgente='429' in motivo or 'vacía' in motivo
        alta_tasa=len(self.recientes)>=15 and sum(not x for x in self.recientes)>=3
        if not self.lento and (urgente or self.errores>=3 or alta_tasa):
            self.lento=True
            self.errores=0
            self.fallos_lentos=0
            self.incidentes.append({'fecha':ahora(),'motivo':motivo,'accion':'un worker; pausas 5–8s'})
            LOG.warning('REDUCCIÓN AUTOMÁTICA: %s; un worker, pausas 5–8s',motivo)
        elif self.lento:
            self.fallos_lentos+=1
            if self.fallos_lentos>=3 or '429' in motivo:
                self.parar.set()
                raise DetenerExtraccion(f'Errores persistentes tras reducir ritmo: {motivo}')

    def exito(self):
        self.errores=0
        self.estables+=1
        self.recientes.append(True)
        if self.lento and self.estables>=20:
            self.lento=False
            self.fallos_lentos=0
            self.recientes.clear()
            self.incidentes.append({'fecha':ahora(),'accion':'recuperar hasta tres workers tras 20 fichas correctas'})
            LOG.info('RECUPERACIÓN DE RITMO: 20 fichas consecutivas correctas; hasta tres pestañas')


async def filtrar(route):
    req=route.request
    host=urlsplit(req.url).hostname or ''
    if req.resource_type in ('image','font','media') or any(host==d or host.endswith('.'+d) for d in AD_DOMAINS):
        await route.abort()
    else:
        await route.continue_()


async def proteccion(page,status=None):
    if status in (401,403):
        raise DetenerExtraccion(f'HTTP {status}: restricción de acceso en {page.url}')
    if status and status>=400:
        raise Transitorio(f'HTTP {status} en {page.url}')
    texto=await page.locator('body').inner_text(timeout=10000)
    if re.search(r'verify you are human|access denied|unusual traffic|checking your browser|robot verification',texto,re.I):
        raise DetenerExtraccion(f'Restricción o verificación humana visible: {page.url}')
    if await page.locator('iframe[src*="captcha"]:visible,[id*="captcha"]:visible').count():
        raise DetenerExtraccion(f'CAPTCHA visible: {page.url}')
    if len(texto.strip())<100:
        raise Transitorio(f'Página vacía: {page.url}')


def url_stats(r):
    # Ruta real observada en el piloto; conserva equipos y mid originales.
    p=urlsplit(r['url_partido'])
    return urlunsplit((p.scheme,p.netloc,p.path.rstrip('/')+'/summary/stats/overall/',p.query,''))


async def extraer(page,r):
    respuesta=await page.goto(url_stats(r),wait_until='commit',timeout=40000)
    status=respuesta.status if respuesta else None
    if status in (401,403):
        raise DetenerExtraccion(f'HTTP {status}: restricción de acceso en {page.url}')
    if status and status>=400:
        raise Transitorio(f'HTTP {status} en {page.url}')
    if parse_qs(urlsplit(page.url).query).get('mid')!=[r['id_partido']]:
        raise DetenerExtraccion(f'URL de ficha incorrecta: {page.url}')
    try:
        await page.wait_for_selector('[data-testid="wcl-statistics"]',timeout=25000)
    except PWTimeout:
        await proteccion(page)
        raise
    await proteccion(page)
    if '/overall/' not in page.url:
        raise Transitorio(f'Periodo global no confirmado: {page.url}')
    textos=await page.locator('[data-testid="wcl-statistics"]').all_inner_texts()
    datos={f'{c}_{l}':None for c in STATS.values() for l in ('local','visitante')}
    for texto in textos:
        partes=[x.strip() for x in texto.splitlines() if x.strip()]
        if len(partes)!=3 or partes[1] not in STATS:
            continue
        campo=STATS[partes[1]]
        for lado,v in zip(('local','visitante'),(partes[0],partes[2])):
            if re.fullmatch(r'\d+(?:\.\d+)?%?',v):
                datos[f'{campo}_{lado}']=float(v.rstrip('%')) if campo=='posesion' else int(v)
    if all(v is None for v in datos.values()):
        raise Transitorio(f'Estadísticas vacías: {r["id_partido"]}')
    for lado in ('local','visitante'):
        a,b=datos[f'tiros_{lado}'],datos[f'tiros_arco_{lado}']
        if a is not None and b is not None and b>a:
            raise Transitorio(f'Tiros inconsistentes: {r["id_partido"]}')
    pos=[datos['posesion_local'],datos['posesion_visitante']]
    if all(v is not None for v in pos) and (any(not 0<=v<=100 for v in pos) or abs(sum(pos)-100)>1):
        raise Transitorio(f'Posesión inconsistente: {r["id_partido"]}')
    datos.update(detalle_verificado='si',url_estadisticas=page.url,detalle_extraido=ahora(),
     sha256_estadisticas=hashlib.sha256(json.dumps(textos,ensure_ascii=False).encode()).hexdigest())
    return datos


async def temporada(browser,liga,periodo,control):
    path=RAW/f'{liga}_{periodo}.csv'
    rows=leer(path)
    validar_basicos(rows,liga,periodo)
    for r in rows:
        for c in ('amarillas_local','amarillas_visitante','rojas_local','rojas_visitante'):
            r.pop(c,None)
    pendientes=[i for i,r in enumerate(rows) if not (r.get('detalle_verificado')=='si' and
     all(r.get(f'{c}_{l}') not in ('',None) for c in STATS.values() for l in ('local','visitante')))]
    terminados=len(rows)-len(pendientes)
    LOG.info('Fichas %s %s: %s guardadas; %s pendientes',liga,periodo,terminados,len(pendientes))
    if not pendientes:
        cov=cobertura(rows)
        if any(v<80 for v in cov.values()):
            raise DetenerExtraccion(f'Cobertura menor al 80%: {liga} {periodo}: {cov}')
        LOG.info('COMPLETA %s %s: %s filas; cobertura=%s (reutilizadas)',liga,periodo,len(rows),cov)
        return
    ultimo_log=time.monotonic()
    fallidas=[]
    resultados=asyncio.Queue()
    cola=asyncio.Queue()
    for i in pendientes:
        cola.put_nowait(i)
    contexts=[]
    pages=[]
    for _ in range(3):
        context=await browser.new_context(locale='en-GB',timezone_id='America/Bogota')
        contexts.append(context)
        await context.route('**/*',filtrar)
        pages.append(await context.new_page())

    async def worker(numero):
        rng=random.Random(SEMILLA+numero)
        page=pages[numero]
        if page is None:
            page=await contexts[numero].new_page()
            pages[numero]=page
        navegaciones=0
        while not control.parar.is_set():
            if control.lento and numero!=0:
                await page.close()
                pages[numero]=None
                return
            try:
                i=cola.get_nowait()
            except asyncio.QueueEmpty:
                return
            await asyncio.sleep(rng.uniform(5,8) if control.lento else rng.uniform(1,2.5))
            if control.parar.is_set():
                return
            try:
                if navegaciones and navegaciones%20==0:
                    # Liberar historial/renderizadores sin cambiar contexto,
                    # cookies ni identidad. No se utiliza ante un bloqueo.
                    await page.close()
                    page=await contexts[numero].new_page()
                    pages[numero]=page
                navegaciones+=1
                datos=await extraer(page,rows[i])
                control.exito()
                await resultados.put((i,datos,None))
            except DetenerExtraccion as exc:
                control.parar.set()
                try:
                    (EVIDENCIA/'ultima_pagina.html').write_text(await page.content(),encoding='utf-8')
                    await page.screenshot(path=str(EVIDENCIA/'ultima_pagina.png'))
                except PWError:
                    pass
                await resultados.put((i,None,exc));return
            except (PWError,Transitorio,ValueError) as exc:
                LOG.warning('Ficha aplazada %s: %s',rows[i]['id_partido'],str(exc)[:150])
                try:
                    control.fallo(str(exc))
                except DetenerExtraccion as fatal:
                    await resultados.put((i,None,fatal));return
                await resultados.put((i,None,Transitorio(str(exc))))
            finally:
                cola.task_done()

    tasks=[asyncio.create_task(worker(i)) for i in range(3)]
    try:
        while any(not t.done() for t in tasks) or not resultados.empty():
            try:
                i,datos,error=await asyncio.wait_for(resultados.get(),timeout=1)
            except asyncio.TimeoutError:
                continue
            if isinstance(error,DetenerExtraccion):
                control.parar.set()
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks,return_exceptions=True)
                raise error
            if error:
                fallidas.append(i)
                rows[i]['detalle_verificado']='reintentar'
            else:
                rows[i].update(datos);terminados+=1
            if not control.lento and not cola.empty():
                for numero in (1,2):
                    if tasks[numero].done():
                        if tasks[numero].exception():
                            raise tasks[numero].exception()
                        tasks[numero]=asyncio.create_task(worker(numero))
            await asyncio.to_thread(guardar_csv,path,rows)
            await asyncio.to_thread(estado,fase='estadisticas',liga=liga,temporada=periodo,completados=terminados,
             total_temporada=len(rows),fallidas=len(fallidas),paralelismo=1 if control.lento else 3)
            if time.monotonic()-ultimo_log>=30:
                LOG.info('PROGRESO %s %s: %s/%s; fallidas=%s; workers=%s',liga,periodo,terminados,len(rows),len(fallidas),1 if control.lento else 3)
                ultimo_log=time.monotonic()
        for t in tasks:
            if t.exception():
                raise t.exception()
        while not cola.empty():
            fallidas.append(cola.get_nowait())
        # Reintento final secuencial, reutilizando una de las tres pestañas.
        for i in sorted(set(fallidas)):
            for intento in range(3):
                await asyncio.sleep(5*2**intento+random.Random(SEMILLA+i+intento).uniform(1,2.5))
                try:
                    rows[i].update(await extraer(pages[0],rows[i]))
                    control.exito()
                    guardar_csv(path,rows)
                    break
                except DetenerExtraccion:
                    raise
                except (PWError,Transitorio,ValueError) as exc:
                    LOG.warning('Reintento final %s %s/3: %s',rows[i]['id_partido'],intento+1,str(exc)[:140])
                    if intento==2:
                        raise DetenerExtraccion(f'Una URL de ficha no carga tras reintentos: {rows[i]["url_partido"]}. {exc}') from exc
        cov=cobertura(rows)
        validar_basicos(rows,liga,periodo)
        LOG.info('COMPLETA %s %s: %s filas; cobertura=%s',liga,periodo,len(rows),cov)
        bajas={k:v for k,v in cov.items() if v<80}
        if bajas:
            raise DetenerExtraccion(f'Cobertura menor al 80% en {liga} {periodo}: {bajas}. Elegir ignorar estas variables o usar solo goles.')
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        for context in contexts:
            await context.close()


async def ejecutar():
    control=Control()
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='msedge',headless=True,args=['--disable-features=BackForwardCache'])
        try:
            for liga in LIGAS:
                for periodo in TEMPORADAS:
                    await temporada(browser,liga,periodo,control)
        finally:
            await browser.close()
    return control.incidentes
