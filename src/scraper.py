"""Entrada al scraper completo aprobado el 17/10/2026.

Configuración y límites en config.py; inventario en extraccion.py y
fichas paralelas en fichas.py. Pipeline hasta Fase 3, sin entrenamiento.
"""
# Configuración explícita del alcance al inicio de la entrada principal.
from config import LIGAS, TEMPORADAS, TEMPORADA_FIXTURES, MAX_FILAS, SEMILLA
from pipeline import main

if __name__ == '__main__':
    main()
