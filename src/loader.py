# -*- coding: utf-8 -*-
"""
Carga, limpieza y consultas vectoriales usando DuckDB + Pandas.
"""
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st
from src.config import RUTA_LLAMADAS, RUTA_CASOS

@st.cache_data(show_spinner=False)
def cargar_datos_duckdb(ruta_cdr: Path, ruta_casos: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carga y normaliza los datasets ejecutando consultas analíticas SQL en DuckDB.
    """
    con = duckdb.connect(database=":memory:")
    
    # Cargar y preprocesar Llamadas CDR
    query_cdr = f"""
    SELECT 
        CAST(id_llamada AS VARCHAR) AS id_llamada,
        CAST(fecha AS DATE) AS fecha,
        CAST(hora AS INTEGER) AS hora,
        CAST(fecha_hora_entrada AS TIMESTAMP) AS fecha_hora_entrada,
        COALESCE(TRIM(id_cliente), '') AS id_cliente,
        COALESCE(TRIM(id_agente), '') AS id_agente,
        COALESCE(TRIM(cola), '') AS cola,
        COALESCE(TRIM(tipo_llamada), '') AS tipo_llamada,
        COALESCE(TRIM(motivo), '') AS motivo,
        LOWER(COALESCE(TRIM(resultado_llamada), '')) AS resultado_llamada,
        CAST(espera_seg AS INTEGER) AS espera_seg,
        CAST(duracion_seg AS INTEGER) AS duracion_seg,
        CAST(acw_seg AS INTEGER) AS acw_seg,
        COALESCE(TRIM(escalado_a), '') AS escalado_a,
        COALESCE(TRIM(dia_semana), '') AS dia_semana,
        (resultado_llamada = 'atendida') AS atendida,
        (resultado_llamada = 'abandonada') AS abandonada,
        CASE WHEN resultado_llamada = 'atendida' THEN (duracion_seg + acw_seg) ELSE NULL END AS aht_seg
    FROM read_csv_auto('{ruta_cdr}')
    WHERE fecha IS NOT NULL AND hora IS NOT NULL
    """
    df_llamadas = con.execute(query_cdr).df()
    
    # Mapeos descriptivos
    map_cola = {
        "Soporte_Pedidos": "Soporte pedidos",
        "Soporte_Envios": "Soporte envíos",
        "Retenciones": "Retenciones",
        "Ventas": "Ventas"
    }
    map_motivo = {
        "estado_envio": "Estado de envío", "devolucion": "Devolución",
        "problema_pago": "Problema de pago", "cambio_producto": "Cambio de producto",
        "facturacion": "Facturación", "cuenta_claves": "Cuenta / claves",
        "reclamo_calidad": "Reclamo de calidad", "informacion_preventa": "Información preventa"
    }
    df_llamadas["cola_etiqueta"] = df_llamadas["cola"].map(map_cola).fillna(df_llamadas["cola"])
    df_llamadas["motivo_etiqueta"] = df_llamadas["motivo"].map(map_motivo).fillna(df_llamadas["motivo"])

    # Cargar y preprocesar Casos/Tickets
    query_casos = f"""
    SELECT 
        CAST(id_caso AS VARCHAR) AS id_caso,
        CAST(id_llamada AS VARCHAR) AS id_llamada,
        CAST(fecha_apertura AS DATE) AS fecha_apertura,
        COALESCE(TRIM(id_cliente), '') AS id_cliente,
        COALESCE(TRIM(id_agente), '') AS id_agente,
        COALESCE(TRIM(categoria), '') AS categoria,
        COALESCE(TRIM(estado_caso), '') AS estado_caso,
        CAST(COALESCE(fcr, 0) AS INTEGER) AS fcr,
        CAST(COALESCE(reincidencia, 0) AS INTEGER) AS reincidencia,
        CAST(COALESCE(horas_resolucion, 0) AS DOUBLE) AS horas_resolucion,
        GREATEST(1.0, LEAST(5.0, CAST(csat AS DOUBLE))) AS csat,
        CAST(COALESCE(valor_orden, 0) AS DOUBLE) AS valor_orden
    FROM read_csv_auto('{ruta_casos}')
    WHERE fecha_apertura IS NOT NULL
    """
    df_casos = con.execute(query_casos).df()
    df_casos["categoria_etiqueta"] = df_casos["categoria"].map(map_motivo).fillna(df_casos["categoria"])

    con.close()
    return df_llamadas, df_casos