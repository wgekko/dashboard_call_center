# -*- coding: utf-8 -*-
"""
Configuraciones globales, rutas y temas de color.
"""
from pathlib import Path

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RUTA_LLAMADAS = DATA_DIR / "llamadas_cdr.csv"
RUTA_CASOS = DATA_DIR / "casos_tickets.csv"

# Paleta de colores corporativos
AZUL = "#0F4C81"
ROJO = "#D64550"
VERDE = "#2CA02C"
AMBAR = "#F5A623"
GRIS = "#6B7280"
GRIS_CLARO = "#E5E7EB"
TEXTO = "#1F2937"
FONDO = "#FFFFFF"

# Umbrales por defecto para la operación
UMBRALES_DEFAULT = {
    "nivel_servicio": 80.0,
    "tiempo_min_espera": 20,
    "abandono": 8.0,
    "asa": 30.0,
    "aht": 350.0,
    "escalamiento": 20.0,
    "fcr": 70.0,
    "reincidencia": 30.0,
    "csat": 3.5,
    "horas_resolucion": 24.0,
}