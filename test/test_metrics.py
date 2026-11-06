# -*- coding: utf-8 -*-
"""
Pruebas unitarias con pytest para funciones en src/metrics.py.
"""
import pytest
import pandas as pd
from src.metrics import (
    calcular_nivel_servicio,
    calcular_tasa_abandono,
    calcular_repeat_callers_24h,
    calcular_valor_en_riesgo
)

def test_calcular_nivel_servicio():
    df = pd.DataFrame({"espera_seg": [10, 15, 25, 30]})
    # Con umbral de 20s, solo 10 y 15 cumplen -> 2/4 = 50.0%
    assert calcular_nivel_servicio(df, umbral_seg=20) == 50.0

def test_calcular_tasa_abandono():
    df = pd.DataFrame({"abandonada": [True, False, False, False]})
    # 1 de 4 abandonadas -> 25.0%
    assert calcular_tasa_abandono(df) == 25.0

def test_calcular_repeat_callers_24h():
    datos = {
        "id_cliente": ["CLI-001", "CLI-001", "CLI-002"],
        "fecha_hora_entrada": pd.to_datetime([
            "2026-08-25 10:00:00",
            "2026-08-25 14:00:00",  # Reincidente dentro de 24h
            "2026-08-25 11:00:00"
        ])
    }
    df = pd.DataFrame(datos)
    # 1 reincidente de 3 llamadas -> 33.33%
    resultado = calcular_repeat_callers_24h(df)
    assert round(resultado, 1) == 33.3

def test_calcular_valor_en_riesgo():
    casos = pd.DataFrame({
        "reincidencia": [1, 0, 1],
        "valor_orden": [100.0, 50.0, 200.0]
    })
    # Reincidentes: 100 + 200 = 300.0
    assert calcular_valor_en_riesgo(casos) == 300.0