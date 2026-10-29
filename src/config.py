"""Configuración común. La copia manual de recuperación nunca se lee aquí."""
from pathlib import Path
import csv
import random
import re
import time

LIGAS={
    'premier_league':('Premier League','england/premier-league',380),
    'laliga':('LaLiga','spain/laliga',380),
    'bundesliga':('Bundesliga','germany/bundesliga',306),
}
TEMPORADAS=('2023-2024','2024-2025','2025-2026')
TEMPORADA_FIXTURES='2026-2027'
MAX_FILAS=4000  # Solo históricos; fixtures exentos por autorización expresa.
SEMILLA=42
RAIZ=Path(__file__).resolve().parents[1]
RAW=RAIZ/'data/raw'
RNG=random.Random(SEMILLA)
EXTRAER=r'''() => {
 let jornada=null; const rows=[];
 for(const e of document.querySelectorAll('.event__round,[id^="g_1_"]')){
  if(e.matches('.event__round')){jornada=e.innerText;continue;}
  const t=s=>e.querySelector(s)?.innerText?.trim()||null;
  rows.push({id_partido:e.id.replace('g_1_',''),jornada_original:jornada,
   fecha_original:t('.event__stageTime'),
   local:t('.event__homeParticipant [data-testid="wcl-simple-text-01"]'),
   visitante:t('.event__awayParticipant [data-testid="wcl-simple-text-01"]'),
   goles_local:t('.event__score--home'),goles_visitante:t('.event__score--away'),
   url_partido:e.querySelector('a.eventRowLink')?.href||null});
 }return rows;
}'''


class DetenerExtraccion(RuntimeError):
    pass


def pausa():
    time.sleep(RNG.uniform(2,5))


def comprobar_bloqueo(page,status=None):
    if status in (401,403,429):
        raise DetenerExtraccion(f'HTTP {status}: acceso restringido.')
    texto=page.locator('body').inner_text(timeout=15000)
    if re.search(r'verify you are human|access denied|unusual traffic|checking your browser|robot verification',texto,re.I):
        raise DetenerExtraccion('Restricción de acceso visible.')
    if page.locator('iframe[src*="captcha"]:visible,[id*="captcha"]:visible').count():
        raise DetenerExtraccion('CAPTCHA visible: no resolver ni eludir.')


def guardar_csv(path,rows):
    """Guardar atómicamente; no crear versiones del archivo canónico."""
    if not rows:
        if not path.exists():
            return
        with path.open(encoding='utf-8-sig',newline='') as f:
            campos=csv.DictReader(f).fieldnames or []
        if not campos:
            return
    else:
        campos=list(dict.fromkeys(k for r in rows for k in r))
    temporal=path.with_suffix('.tmp')
    with temporal.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=campos)
        w.writeheader();w.writerows(rows)
    reemplazar(temporal,path)


def reemplazar(temporal,path):
    """OneDrive/antivirus pueden bloquear brevemente el reemplazo en Windows."""
    for intento in range(12):
        try:
            temporal.replace(path)
            return
        except PermissionError:
            if intento==11:
                raise
            time.sleep(min(0.25*1.7**intento,2))
