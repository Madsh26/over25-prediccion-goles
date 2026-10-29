"""Configuración común del proyecto (rutas, ligas, temporadas y utilidades de archivo)."""
from pathlib import Path
import csv
import random
import re
import time

LIGAS={
    'premier_league':('Premier League','',380),
    'laliga':('LaLiga','',380),
    'bundesliga':('Bundesliga','',306),
}
TEMPORADAS=('2023-2024','2024-2025','2025-2026')
TEMPORADA_FIXTURES='2026-2027'
MAX_FILAS=4000  # Solo históricos; fixtures exentos por autorización expresa.
SEMILLA=42
RAIZ=Path(__file__).resolve().parents[1]
RAW=RAIZ/'data/raw'
RNG=random.Random(SEMILLA)


class DetenerExtraccion(RuntimeError):
    pass






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
