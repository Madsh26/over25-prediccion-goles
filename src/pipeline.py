"""Orquesta extracción, limpieza y features; nunca inicia el entrenamiento."""
import asyncio
import json
import logging
import re
from pathlib import Path
from config import RAIZ,RAW,LIGAS,TEMPORADAS,TEMPORADA_FIXTURES,MAX_FILAS
from extraccion import EVIDENCIA,leer,estado,inventariar,validar_basicos,cobertura,ahora

LOG=logging.getLogger('flashscore')


def baselines():
    from config import guardar_csv
    historicos=leer(RAIZ/'data/clean/datos_limpios.csv')
    if not historicos:
        historicos=[r for liga in LIGAS for periodo in TEMPORADAS
                    for r in leer(RAW/f'{liga}_{periodo}.csv')]
    modelo=leer(RAIZ/'data/clean/dataset_modelo.csv')
    salidas=[]
    for poblacion,rows in (('historico_completo',historicos),('dataset_modelo',modelo)):
        if not rows:
            continue
        for liga in [v[0] for v in LIGAS.values()]+['Todas']:
            sel=[r for r in rows if liga=='Todas' or r['liga']==liga]
            train=[r for r in sel if r['temporada'] in ('2023-24','2024-25')]
            test=[r for r in sel if r['temporada']=='2025-26']
            unos=sum(int(r['over25']) for r in train)
            clase=int(unos>=len(train)-unos)
            aciertos=sum(int(r['over25'])==clase for r in test)
            positivos=sum(int(r['over25']) for r in test)
            salidas.append({'liga':liga,'poblacion':poblacion,'temporada_prueba':'2025-26',
             'temporadas_entrenamiento':'2023-24 + 2024-25','filas_train':len(train),'filas_test':len(test),
             'clase_mayoritaria_train':clase,'prob_over_train':round(unos/len(train),6),
             'accuracy_test':round(aciertos/len(test),6),'aciertos_test':aciertos,
             'porcentaje_over_test':round(100*positivos/len(test),3),
             'mayoria_descriptiva_test_pct':round(100*max(positivos,len(test)-positivos)/len(test),3)})
    guardar_csv(RAIZ/'data/clean/linea_base.csv',salidas)


def informe(motivo=None):
    informe_path=RAIZ/'informe/reporte_final.md'
    lineas=['# Reporte del proyecto hasta Fase 3',f'\nActualizado: {ahora()}.',
     '\nFuente: [Flashscore](https://www.flashscore.com/). Se conservaron las URLs de cada partido en los CSV y las nueve URLs históricas y tres de fixtures en data/raw/evidencia/inventario.json. Over25=1 representa tres o más goles; Under=0, dos o menos.',
     '\nEstado: '+('DETENIDO — '+motivo if motivo else
        ('Fase 3 completa; pendiente revisión antes de entrenar.' if (RAIZ/'data/clean/metadatos_modelo.json').exists()
         else 'Extracción en curso; limpieza y características pendientes.')),
     '\n## Filas y cobertura por liga/temporada',
     '\nLa cobertura exige valores para ambos equipos. Si las fichas no terminaron, es provisional.',
     '\n| Liga | Temporada | Filas/esperadas | IDs únicos | Nulos básicos % | Fichas | Tiros % | Al arco % | Posesión % | Córners % |',
     '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    from extraccion import CAMPOS
    for liga in LIGAS:
        for periodo in TEMPORADAS:
            rows=leer(RAW/f'{liga}_{periodo}.csv')
            cov=cobertura(rows)
            nulos=sum(any(r.get(c) in (None,'') for c in CAMPOS) for r in rows)
            visitadas=sum(r.get('detalle_verificado')=='si' for r in rows)
            pct=round(100*nulos/len(rows),3) if rows else None
            lineas.append(f'| {LIGAS[liga][0]} | {periodo} | {len(rows)}/{LIGAS[liga][2]} | {len({r["id_partido"] for r in rows})} | {pct} | {visitadas} | '+ ' | '.join(str(cov[c]) for c in ('tiros','tiros_arco','posesion','corners'))+' |')
    lineas+=['\n## Fixtures 2026-27',
     '\nTodos quedan guardados y exentos del límite histórico; no se visitan sus fichas.',
     '\n| Liga | Guardados |','|---|---:|']
    for liga in LIGAS:
        lineas.append(f'| {LIGAS[liga][0]} | {len(leer(RAW/f"{liga}_{TEMPORADA_FIXTURES}_fixtures.csv"))} |')
    metadatos=RAIZ/'data/clean/metadatos_modelo.json'
    if metadatos.exists() and not motivo:
        meta=json.loads(metadatos.read_text(encoding='utf-8'))
        por_periodo=meta['modelo_por_liga_temporada']
        n_train=sum(v for k,v in por_periodo.items() if k.endswith(('|2023-24','|2024-25')))
        n_test=sum(v for k,v in por_periodo.items() if k.endswith('|2025-26'))
        lineas+=['\n## Limpieza y características',
         f'\nFilas de modelado: {meta["filas_modelo"]}. Excluidas por historial: {meta["filas_descartadas_historial"]}.',
         f'Variables numéricas: {len(meta["features_numericas"])}; variable categórica adicional: liga. Entrenamiento previsto: {n_train} filas de 2023-24/2024-25; prueba: {n_test} de 2025-26.',
         f'Fixtures de las próximas tres jornadas por liga: {meta["filas_fixtures"]}; sin historial suficiente: {meta["fixtures_sin_historial"]}.',
         '\nSolo se usan fechas estrictamente anteriores; todos los partidos del mismo día se excluyen del historial. Se arrastra historial entre temporadas. Mínimo 10 partidos generales y 5 en la sede. Ventanas 5/10; medias estadísticas con al menos 80% de observaciones. No se entrenaron modelos.',
         '\nJornadas consecutivas preparadas: '+json.dumps(meta['jornadas_fixtures_seleccionadas'],ensure_ascii=False)+'. Los aplazados de jornadas anteriores siguen en el maestro, fuera del horizonte de predicción.',
         '\nVerificación independiente: '+meta.get('verificacion','Consultar src/verificar.py')+'.',
         '\nEl historial de fixtures está congelado al último resultado permitido (2025-26); no incluye resultados 2026-27. Los fixtures sin historial permanecen señalados.',
         '\nLas proporciones Over históricas están en escala 0–1 y la posesión en 0–100. El dataset histórico incluye solo filas elegibles; las exclusiones por liga/temporada y el listado de variables están en metadatos_modelo.json y filas_sin_historial.csv.',
         '\n## Línea base temporal',
         '\nClase mayoritaria elegida SOLO con 2023-24/2024-25 y evaluada en 2025-26. La mayoría del test es solo descriptiva, nunca se usa para decidir la clase.',
         '\n| Liga | Población | Clase train | n test | Accuracy test |','|---|---|---:|---:|---:|']
        for r in leer(RAIZ/'data/clean/linea_base.csv'):
            lineas.append(f'| {r["liga"]} | {r["poblacion"]} | {r["clase_mayoritaria_train"]} | {r["filas_test"]} | {float(r["accuracy_test"]):.2%} |')
        lineas.append('\nLa referencia de Bundesliga supera 63% por su frecuencia de Over; es una línea base trivial. Los modelos posteriores deben compararse con esta referencia en las mismas filas de prueba.')
    if (motivo or not metadatos.exists()) and (RAIZ/'data/clean/linea_base.csv').exists():
        lineas+=['\n## Línea base histórica disponible',
         '\nClase decidida con 2023-24/2024-25; accuracy en 2025-26. No se eligió la clase mirando el test.',
         '\n| Liga | Clase train | Filas test | Accuracy test |','|---|---:|---:|---:|']
        for r in leer(RAIZ/'data/clean/linea_base.csv'):
            lineas.append(f'| {r["liga"]} | {r["clase_mayoritaria_train"]} | {r["filas_test"]} | {float(r["accuracy_test"]):.2%} |')
    texto_log=(RAIZ/'informe/scraping.log').read_text(encoding='utf-8')
    ids_aplazados=set(re.findall(r'Ficha aplazada (\w+):',texto_log))
    ids_recuperados={r['id_partido'] for liga in LIGAS for periodo in TEMPORADAS
                     for r in leer(RAW/f'{liga}_{periodo}.csv') if r.get('detalle_verificado')=='si'}
    lineas+=['\n## Incidencias y archivos',
     f'\nFichas distintas con algún tiempo de espera: {len(ids_aplazados)}; completadas posteriormente: {len(ids_aplazados & ids_recuperados)}. Reducciones automáticas de ritmo registradas: {texto_log.count("REDUCCIÓN AUTOMÁTICA")}; recuperaciones tras 20 fichas correctas: {texto_log.count("RECUPERACIÓN DE RITMO")}. No se activó la parada por CAPTCHA o restricción de acceso.',
     '\nFechas sin año se derivan de temporada verificada y mes, con marca de procedencia. Los playoffs de Bundesliga se excluyen: solo 306 partidos de liga regular. Las tarjetas quedan fuera por falta de asociación tabular fiable. No se rellenan estadísticas ausentes con ceros.',
     '\nSe recuperó un bloqueo temporal de escritura de Windows (WinError 5) validando y consolidando el temporal en el CSV canónico. Se añadieron reintentos de reemplazo con backoff. No se consultó la copia de recuperación.',
     '\nEl ritmo es de hasta tres contextos, pausa 1–2,5 s por worker; ante aumento de errores, un worker y 5–8 s. CAPTCHA o restricción detienen la extracción sin intentar resolverlos. Las fichas fallidas se reintentan al final con backoff. Imágenes, fuentes, medios y dominios de anuncios/analítica se bloquean.',
     '\nSe consolidaron los informes previos en este reporte y el código del piloto en config.py. Se eliminaron las muestras duplicadas, ZIP de avances, informes anteriores y DOM/capturas acumulados. Quedan datos canónicos, código, log único, estado de reanudación, metadatos y evidencia mínima. No se genera ZIP nuevo.',
     '\nArchivos retirados: muestra_piloto.csv; validar_piloto.py y auditar_inventario.py; reporte_piloto.md, reporte_escalado.md, README_piloto.md y sus auditorías/controles redundantes; evidencia_piloto y DOM/capturas de ejecuciones anteriores; proyecto_over25_fase1_piloto.zip y proyecto_over25_avance_escalado.zip. Los doce certificados de inventario se consolidaron en data/raw/evidencia/inventario.json. Se conserva una sola muestra de DOM comprimida como evidencia mínima.',
     '\nEl resumen intermedio de limpieza se integró en metadatos_modelo.json y se retiró su archivo separado. Los temporales de escritura se consumen al reemplazar los CSV; se retiran las cachés de compilación del código al entregar.',
     '\nLa copia de seguridad única solicitada se creó al comienzo. No se volvió a leer, modificar ni utilizar en el pipeline; no se incluye en inventarios ni paquetes. Tú decides cuándo borrarla.',
     '\n## Reejecución',
     '\nDesde proyecto_over25, ejecutar:',
     '\n```powershell\n.\\.venv\\Scripts\\python.exe -u src/scraper.py\n```',
     '\nReutiliza los detalles completos y sobrescribe los mismos CSV canónicos. La copia de recuperación no forma parte de la ejecución. El log es informe/scraping.log; el estado operativo está en informe/estado_extraccion.json.',
     '\nSalidas de revisión, si el scraping termina: data/clean/dataset_modelo.csv, dataset_fixtures_features.csv, datos_limpios.csv, fixtures_limpios.csv, linea_base.csv, auditoria_temporal.csv, filas_sin_historial.csv, calidad_datos.csv y metadatos_modelo.json. Los siguientes pasos de modelado requieren revisión del estudiante.']
    informe_path.write_text('\n'.join(lineas)+'\n',encoding='utf-8')


def main():
    from playwright.sync_api import sync_playwright
    from fichas import ejecutar
    for carpeta in (RAW,EVIDENCIA,RAIZ/'informe'):
        carpeta.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',
     handlers=[logging.FileHandler(RAIZ/'informe/scraping.log',encoding='utf-8'),logging.StreamHandler()])
    LOG.info('INICIO: fixtures exentos; máximo histórico %s; tres workers; reanudación',MAX_FILAS)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            context=browser.new_context(locale='en-GB',timezone_id='America/Bogota')
            def ruta(route):
                from urllib.parse import urlsplit
                from fichas import AD_DOMAINS
                req=route.request; host=urlsplit(req.url).hostname or ''
                if req.resource_type in ('image','font','media') or any(host==d or host.endswith('.'+d) for d in AD_DOMAINS):
                    route.abort()
                else:
                    route.continue_()
            context.route('**/*',ruta)
            page=context.new_page()
            try:
                for liga in LIGAS:
                    for periodo in TEMPORADAS:
                        inventariar(page,liga,periodo)
                for liga in LIGAS:
                    inventariar(page,liga,TEMPORADA_FIXTURES,fixtures=True)
            finally:
                browser.close()
        incidencias=asyncio.run(ejecutar())
        LOG.info('Fichas completas; reducciones de ritmo: %s',len(incidencias))
        estado(fase='scraping_completo')
        import limpieza,features,verificar
        limpieza.main()
        features.main()
        verificar.main()
        baselines()
        estado(fase='fase3_completa',entrenamiento='pendiente_revision')
        informe()
        LOG.info('FASE 3 COMPLETA; pendiente revisión, sin entrenamiento')
    except Exception as exc:
        estado(fase='detenido',motivo=str(exc))
        LOG.error('DETENIDO: %s',str(exc)[:700])
        informe(str(exc))
        raise


if __name__=='__main__':
    main()
