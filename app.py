"""
Dashboard principal Call Center Ecommerce & NLP Intelligence.
"""
import concurrent.futures
from datetime import datetime, timedelta
import io
import sqlite3
import warnings

import laya
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import RUTA_LLAMADAS, RUTA_CASOS, UMBRALES_DEFAULT, AZUL, ROJO, VERDE, AMBAR
from src.loader import cargar_datos_duckdb
from src.metrics import (
    calcular_nivel_servicio, calcular_tasa_abandono, calcular_asa, calcular_aht,
    calcular_fcr, calcular_csat_promedio, calcular_ocupacion_agentes,
    calcular_repeat_callers_24h, calcular_valor_en_riesgo,
    calcular_estadisticas_espera, modelo_regresion_abandono,
    modelo_arbol_csat_critico, calcular_pareto_reincidencia
)
from src.components import aplicar_estilo_grafico, popup_umbrales, popup_definiciones

# Configuración de página
st.set_page_config(
    page_title="Call Center Ecommerce | Enterprise Dashboard",
    page_icon=":material/phone_callback:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo CSS personalizado
st.markdown("""
<style>
div[class*='st-key-kpi'] {
    background-color: #FFFFFF;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

# Inicializar Session State para Umbrales
if "umbrales" not in st.session_state:
    st.session_state["umbrales"] = UMBRALES_DEFAULT.copy()

# Base de datos SQLite local para persistencia histórica de NLP
DB_NLP_FILE = "call_center_nlp_history.db"

def init_nlp_db():
    conn = sqlite3.connect(DB_NLP_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS analisis_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            id_cliente TEXT,
            comentario TEXT,
            motivo_detectado TEXT,
            sentimiento TEXT,
            prob_churn REAL,
            modelo_routing TEXT
        )
    """)
    conn.commit()
    conn.close()

init_nlp_db()

# Helper para exportar DataFrame a Excel en memoria
def to_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Evaluacion_NLP_Laya")
    return output.getvalue()

# Carga cacheada del Router LAYA para análisis de texto natural
@st.cache_resource
def load_laya_router():
    router = laya.Router(preload=False)
    router.load("multilingual")
    return router

router = load_laya_router()

# Cargar datos operativos
try:
    llamadas, casos = cargar_datos_duckdb(RUTA_LLAMADAS, RUTA_CASOS)
except Exception as e:
    st.error(f"Error al cargar datos con DuckDB: {e}")
    st.stop()

# ----------------------------------------------------
# SIDEBAR: FILTROS DE OPERACIÓN (Fechas robustas)
# ----------------------------------------------------
st.sidebar.subheader(":material/search: Filtros de Operación")

# fecha_min = llamadas["fecha"].min().date() if not llamadas.empty else datetime.now().date()
fecha_max = llamadas["fecha"].max().date() if not llamadas.empty else datetime.now().date()
fecha_min_calculada = fecha_max - timedelta(days=30)
fecha_min_real = llamadas["fecha"].min().date() if not llamadas.empty else fecha_min_calculada
fecha_min = max(fecha_min_calculada, fecha_min_real)


# Inicializar estado en session_state para evitar conflictos en el date_input
if "rango_fechas" not in st.session_state:
    st.session_state["rango_fechas"] = (fecha_min, fecha_max)

fechas_input = st.sidebar.date_input(
    "Rango de fechas",
    value=st.session_state["rango_fechas"],
    min_value=fecha_min,
    max_value=fecha_max,
    key="widget_rango_fechas"
)

# Validar y actualizar el rango de fechas de forma robusta
if isinstance(fechas_input, (list, tuple)):
    if len(fechas_input) == 2:
        inicio, fin = fechas_input
    elif len(fechas_input) == 1:
        inicio = fin = fechas_input[0]
    else:
        inicio, fin = fecha_min, fecha_max
else:
    inicio = fin = fechas_input

if inicio > fin:
    inicio, fin = fin, inicio

st.session_state["rango_fechas"] = (inicio, fin)

inicio_ts = pd.Timestamp(inicio)
fin_ts = pd.Timestamp(fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# Filtrado por DuckDB / Pandas asegurando integridad temporal
mask_llamadas = (llamadas["fecha"] >= inicio_ts) & (llamadas["fecha"] <= fin_ts)
llamadas_f = llamadas.loc[mask_llamadas].copy()

#casos_f = casos.loc[casos["id_llamada"].isin(llamadas_f["id_llamada"])].copy() if "id_llamada" in casos.columns and "id_llamada" in llamadas_f.columns else pd.DataFrame()
# modificacion de id para analizar 
#------------------------------------------------
if "fecha_apertura" in casos.columns:
    casos["fecha_apertura_dt"] = pd.to_datetime(casos["fecha_apertura"])
    mask_casos = (casos["fecha_apertura_dt"] >= inicio_ts) & (casos["fecha_apertura_dt"] <= fin_ts)
    casos_f = casos.loc[mask_casos].copy()
else:
    casos_f = casos.loc[casos["id_llamada"].isin(llamadas_f["id_llamada"])].copy()

#----------------------------------------------------------


# Controles adicionales para LAYA en la barra lateral
st.sidebar.divider()
st.sidebar.subheader(":material/settings: Configuración LAYA NLP")
umbral_churn = st.sidebar.slider("Umbral Alerta Churn/Abandono (%):", 10, 90, 40) / 100.0

# Botones de configuración
st.sidebar.divider()
if st.sidebar.button(":material/settings: Umbrales", width='stretch'):
    popup_umbrales(st.session_state["umbrales"])

if st.sidebar.button(":material/rule_settings: Definiciones", width='stretch'):
    popup_definiciones()

# ----------------------------------------------------
# TABLERO PRINCIPAL
# ----------------------------------------------------
st.subheader(":material/add_call: Call Center Ecommerce Analytics")
st.caption(f"Período analizado: {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')} | Total llamadas en rango: {len(llamadas_f):,} | Casos en rango: {len(casos_f):,}")

umbrales = st.session_state["umbrales"]

# Pestañas principales
tab_operaciones, tab_calidad, tab_estadistica, tab_agentes, tab_datos, tab_nlp = st.tabs([
    "Operaciones & Capacidad", 
    "Calidad & Finanzas", 
    "Estadística Avanzada", 
    "Desempeño Equipos", 
    "Vista de Datos",
    "Inteligencia NLP (Laya)"
])

# ----------------------------------------------------
# PESTAÑA 1: OPERACIONES
# ----------------------------------------------------
with tab_operaciones:
    sl_val = calcular_nivel_servicio(llamadas_f, umbrales["tiempo_min_espera"])
    abandono_val = calcular_tasa_abandono(llamadas_f)
    asa_val = calcular_asa(llamadas_f)
    aht_val = calcular_aht(llamadas_f)
    ocupacion_val = calcular_ocupacion_agentes(llamadas_f)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Nivel Servicio (SL)", f"{sl_val:.1f}%" if sl_val else "--", delta=f"Meta: {umbrales['nivel_servicio']}%")
    c2.metric("Abandono", f"{abandono_val:.1f}%" if abandono_val else "--", delta=f"Meta: <{umbrales['abandono']}%", delta_color="inverse")
    c3.metric("ASA (Espera Promedio)", f"{asa_val:.0f}s" if asa_val else "--")
    c4.metric("AHT (Atención Promedio)", f"{aht_val:.0f}s" if aht_val else "--")
    c5.metric("Ocupación Agentes", f"{ocupacion_val:.1f}%" if ocupacion_val else "--")

    st.subheader("Evolución de Tráfico por Franja Horaria")
    vol_hora = llamadas_f.groupby(["hora", "resultado_llamada"]).size().reset_index(name="cuenta") if not llamadas_f.empty else pd.DataFrame(columns=["hora", "resultado_llamada", "cuenta"])
    fig_hora = px.bar(
        vol_hora, x="hora", y="cuenta", color="resultado_llamada",
        color_discrete_map={"atendida": AZUL, "abandonada": ROJO},
        title="Llamadas Atendidas vs Abandonadas por Hora"
    )
    st.plotly_chart(aplicar_estilo_grafico(fig_hora), width='stretch')

# ----------------------------------------------------
# PESTAÑA 2: CALIDAD & FINANZAS
# ----------------------------------------------------
with tab_calidad:
    fcr_val = calcular_fcr(casos_f)
    csat_val = calcular_csat_promedio(casos_f)
    repeat_val = calcular_repeat_callers_24h(llamadas_f)
    riesgo_val = calcular_valor_en_riesgo(casos_f)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("FCR (Primer Contacto)", f"{fcr_val:.1f}%" if fcr_val else "--")
    k2.metric("CSAT Promedio", f"{csat_val:.2f} / 5" if csat_val else "--")
    k3.metric("Repeat Callers (24h)", f"{repeat_val:.1f}%" if repeat_val else "--", delta_color="inverse")
    k4.metric("Valor en Riesgo", f"${riesgo_val:,.0f}")

    st.subheader("Distribución de CSAT por Motivo de Contacto")
    if not casos_f.empty:
        fig_csat = px.box(
            casos_f, x="categoria_etiqueta", y="csat", color="categoria_etiqueta",
            title="Puntuación CSAT según Categoría del Ticket"
        )
        st.plotly_chart(aplicar_estilo_grafico(fig_csat), width='stretch')

# ----------------------------------------------------
# PESTAÑA 3: ESTADÍSTICA AVANZADA
# ----------------------------------------------------
with tab_estadistica:
    st.subheader("Analítica Predictiva & Herramientas Matemáticas")
    st.caption("Herramientas estadísticas para soporte en la toma de decisiones estratégicas.")

    # 1. Mediana vs Percentil 90
    st.subheader("1. Evaluación de Tiempos sin Sesgo (Robustez Estadistica)")
    stats_esp = calcular_estadisticas_espera(llamadas_f)
    
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Mediana de Espera (P50)", f"{stats_esp['p50']:.0f} seg", help="El 50% de las llamadas esperó menos que este tiempo.")
    col_e2.metric("Percentil 90 de Espera (P90)", f"{stats_esp['p90']:.0f} seg", help="Métrica de impacto severo: El 90% esperó menos de este valor.")
    col_e3.metric("Rango Intercuartílico (IQR)", f"{stats_esp['iqr']:.0f} seg", help="Dispersión central del 50% de los datos.")

    st.divider()

    # 2. Regresión Logística de Abandono
    st.subheader("2. Regresión Logística: Curva de Probabilidad de Abandono")
    df_reg = modelo_regresion_abandono(llamadas_f)
    if not df_reg.empty:
        fig_reg = px.line(
            df_reg, x="espera_seg", y="prob_abandono",
            title="Probabilidad Estimada de Abandono (%) según Tiempo de Espera (Segundos)",
            labels={"espera_seg": "Espera en Cola (s)", "prob_abandono": "Probabilidad de Abandono (%)"}
        )
        fig_reg.add_hline(y=50, line_dash="dash", line_color=ROJO, annotation_text="Punto Crítico (50%)")
        st.plotly_chart(aplicar_estilo_grafico(fig_reg), width='stretch')

    st.divider()

    # 3. Árbol de Decisión & Pareto
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.subheader("3. Árbol de Decisión: Drivers de CSAT Crítico")
        df_unido = llamadas_f.merge(casos_f, on="id_llamada", how="inner")
        imp_df, reglas = modelo_arbol_csat_critico(df_unido)
        
        if not imp_df.empty:
            fig_tree = px.bar(
                imp_df, x="Importancia (%)", y="Variable", orientation="h",
                title="Importancia de Variables en Calificaciones <= 2 Estrellas"
            )
            st.plotly_chart(aplicar_estilo_grafico(fig_tree), width='stretch')
            with st.expander("Ver reglas del árbol entrenado"):
                st.code(reglas)

    with col_p2:
        st.subheader("4. Análisis Pareto 80/20: Valor en Riesgo por Reincidencia")
        df_pareto = calcular_pareto_reincidencia(casos_f)
        if not df_pareto.empty:
            fig_pareto = go.Figure()
            fig_pareto.add_trace(go.Bar(
                x=df_pareto["categoria_etiqueta"], y=df_pareto["valor_orden"],
                name="Monto en Riesgo ($)", marker_color=AZUL
            ))
            fig_pareto.add_trace(go.Scatter(
                x=df_pareto["categoria_etiqueta"], y=df_pareto["pct_acumulado"],
                name="% Acumulado", yaxis="y2", marker_color=ROJO
            ))
            fig_pareto.update_layout(
                title="Análisis Pareto por Categoría Reincidente",
                yaxis=dict(title="Monto ($)"),
                yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 105])
            )
            st.plotly_chart(aplicar_estilo_grafico(fig_pareto), width='stretch')

# ----------------------------------------------------
# PESTAÑA 4: EQUIPOS
# ----------------------------------------------------
with tab_agentes:
    st.subheader("Métricas Detalladas por Agente")
    if not llamadas_f.empty:
        agentes_df = llamadas_f.loc[llamadas_f["atendida"] & (llamadas_f["id_agente"] != "")].groupby("id_agente").agg(
            atendidas=("id_llamada", "count"),
            aht=("aht_seg", "mean")
        ).reset_index().sort_values("atendidas", ascending=False)
        st.dataframe(agentes_df, width='stretch', hide_index=True)
    else:
        st.info("No hay datos de agentes en el rango seleccionado.")

# ----------------------------------------------------
# PESTAÑA 5: DATOS
# ----------------------------------------------------
with tab_datos:
    st.dataframe(llamadas_f, width='stretch', hide_index=True)

# ----------------------------------------------------
# PESTAÑA 6: INTELIGENCIA NLP (LAYA) - 
# ----------------------------------------------------

with tab_nlp:
    st.subheader("Motor Cognitivo LAYA: Análisis de Texto y Clasificación")
    st.markdown("Selecciona la fuente de datos que deseas procesar de forma independiente para el período seleccionado.")

    # Selector de fuente para Laya
    fuente_nlp = st.selectbox(
        "Seleccionar fuente de datos a procesar:",
        ["Casos de Tickets (comentario_caso)", "Llamadas de Central (llamadas_cdr)"],
        key="select_fuente_laya_principal"
    )

    st.markdown("---")

    # Criterios de Laya
    criterios_laya = {
        "questions": {
            "motivo_raiz": {
                "type": "choice",
                "instructions": "Cuál es el motivo principal del reclamo o contacto?",
                "criteria": {
                    "logistica": "envíos demorados, paquetes rotos, tracking, entregas",
                    "pagos": "problemas con tarjetas, cobros duplicados, pasarela de pago",
                    "devoluciones": "cambios de talle, reembolsos, devoluciones",
                    "soporte_web": "errores en la app, caídas de sistema, bugs",
                    "other": "everything else"
                }
            },
            "sentimiento": {
                "type": "score",
                "instructions": "Cuál es el sentimiento del cliente?",
                "criteria": ["negativo", "neutral", "positivo"]
            },
            "riesgo_abandono": {
                "type": "noul",
                "instructions": "¿El usuario amenaza con cancelar o abandonar el servicio?"
            }
        }
    }

    # Asegurar que existan ambas tablas en SQLite (Puentes independientes)
    def init_double_nlp_db():
        conn = sqlite3.connect(DB_NLP_FILE)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS analisis_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                comentario TEXT UNIQUE,
                motivo_detectado TEXT,
                sentimiento TEXT,
                prob_churn REAL,
                modelo_routing TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS analisis_llamadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                id_llamada TEXT UNIQUE,
                cola TEXT,
                motivo TEXT,
                resultado TEXT,
                espera_seg INTEGER,
                comentario TEXT,
                motivo_detectado TEXT,
                sentimiento TEXT,
                prob_churn REAL,
                modelo_routing TEXT
            )
        """)
        conn.commit()
        conn.close()

    init_double_nlp_db()

    # Opción 1: Casos de Tickets
    if fuente_nlp == "Casos de Tickets (comentario_caso)":
        try:
            casos_directos = pd.read_csv('data/casos_tickets.csv')
            if "fecha_apertura" in casos_directos.columns:
                casos_directos["fecha_apertura_dt"] = pd.to_datetime(casos_directos["fecha_apertura"])
                mask_casos = (casos_directos["fecha_apertura_dt"] >= inicio_ts) & (casos_directos["fecha_apertura_dt"] <= fin_ts)
                casos_filtrados_nlp = casos_directos.loc[mask_casos].copy()
            else:
                casos_filtrados_nlp = casos_directos.copy()
        except Exception as e:
            casos_filtrados_nlp = pd.DataFrame()
            st.error(f"Error al leer el archivo de casos: {e}")

        st.info(f"Casos de Tickets listos en este rango: **{len(casos_filtrados_nlp):,}**")
        
        col_btn1, _ = st.columns([2, 2])
        with col_btn1:
            btn_ejecutar_tickets = st.button(":material/forms_apps_script: Ejecutar Análisis en Tickets", type="primary", key="btn_nlp_tickets_unico")

        if btn_ejecutar_tickets:
            if not casos_filtrados_nlp.empty and "comentario_caso" in casos_filtrados_nlp.columns:
                todos_los_textos = casos_filtrados_nlp["comentario_caso"].fillna("Sin comentario registrado").astype(str).tolist()
            else:
                todos_los_textos = []

            if len(todos_los_textos) == 0:
                st.warning("No hay comentarios disponibles en los casos para el rango seleccionado.")
            else:
                conn = sqlite3.connect(DB_NLP_FILE)
                cursor = conn.cursor()
                
                cursor.execute("SELECT comentario, motivo_detectado, sentimiento, prob_churn, modelo_routing FROM analisis_tickets")
                rows = cursor.fetchall()
                cache_dict = {row[0]: {"comentario": row[0], "motivo": row[1], "sentimiento": row[2], "prob_churn": row[3], "modelo": row[4]} for row in rows}
                
                textos_unicos_pendientes = list(set([t for t in todos_los_textos if t not in cache_dict]))
                st.toast(f"Total: {len(todos_los_textos):,} | En caché: {len(todos_los_textos) - len(textos_unicos_pendientes):,} | Únicos a procesar: {len(textos_unicos_pendientes):,}")

                if len(textos_unicos_pendientes) > 0:
                    progress_bar = st.progress(0, text=f"Procesando {len(textos_unicos_pendientes):,} textos únicos con LAYA (4 núcleos)...")
                    
                    def procesar_comentario(texto):
                        try:
                            res = router.predict(state=texto, questions=criterios_laya["questions"])
                            return {
                                "comentario": texto,
                                "motivo": res["answers"]["motivo_raiz"]["choice"],
                                "sentimiento": res["answers"]["sentimiento"]["legend"].get(str(round(res["answers"]["sentimiento"]["score"])), "neutral"),
                                "prob_churn": res["answers"]["riesgo_abandono"]["noul"],
                                "modelo": res["routing"]["model"]
                            }
                        except Exception as e:
                            return {"comentario": texto, "motivo": "error", "sentimiento": "neutral", "prob_churn": 0.0, "modelo": "error", "error": str(e)}

                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                        futures = {executor.submit(procesar_comentario, c): c for c in textos_unicos_pendientes}
                        completados = 0
                        for f in concurrent.futures.as_completed(futures):
                            res_res = f.result()
                            try:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO analisis_tickets (timestamp, comentario, motivo_detectado, sentimiento, prob_churn, modelo_routing)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (datetime.now().isoformat(), res_res["comentario"], res_res["motivo"], res_res["sentimiento"], res_res["prob_churn"], res_res.get("modelo", "multilingual")))
                                conn.commit()
                            except Exception:
                                pass
                            
                            completados += 1
                            progress_bar.progress(completados / len(textos_unicos_pendientes), text=f"Procesando con LAYA... ({completados:,}/{len(textos_unicos_pendientes):,})")
                    
                    progress_bar.empty()
                
                cursor.execute("SELECT comentario, motivo_detectado, sentimiento, prob_churn, modelo_routing FROM analisis_tickets")
                rows_updated = cursor.fetchall()
                cache_completo = {row[0]: {"comentario": row[0], "motivo": row[1], "sentimiento": row[2], "prob_churn": row[3], "modelo": row[4]} for row in rows_updated}
                conn.close()

                resultados_nlp = [cache_completo.get(t, {"comentario": t, "motivo": "other", "sentimiento": "neutral", "prob_churn": 0.0, "modelo": "multilingual"}) for t in todos_los_textos]

                df_nlp_res = pd.DataFrame(resultados_nlp)
                st.session_state["df_nlp_res"] = df_nlp_res
                st.success(f"¡Análisis NLP completado con éxito para {len(df_nlp_res):,} tickets!")
                st.rerun()

    # Opción 2: Llamadas de Central 
    else:
        st.info(f"Llamadas listas en este rango: **{len(llamadas_f):,}**")
        
        col_btn2, _ = st.columns([2, 2])
        with col_btn2:
            btn_ejecutar_llamadas = st.button(":material/forms_apps_script: Ejecutar Análisis en Llamadas", type="primary", key="btn_nlp_llamadas_unico")

        if btn_ejecutar_llamadas:
            if not llamadas_f.empty:
                # Estandarizamos el texto agrupando por tipificación (sin segundos exactos para maximizar la unicidad)
                llamadas_f["texto_llamada"] = (
                    "Llamada en cola " + llamadas_f["cola"].astype(str) + 
                    " por motivo " + llamadas_f["motivo"].astype(str) + 
                    " con resultado " + llamadas_f["resultado_llamada"].astype(str) + "."
                )
                todos_los_textos_llamadas = llamadas_f["texto_llamada"].tolist()
            else:
                todos_los_textos_llamadas = []

            if len(todos_los_textos_llamadas) == 0:
                st.warning("No hay datos de llamadas disponibles para el rango seleccionado.")
            else:
                conn = sqlite3.connect(DB_NLP_FILE)
                cursor = conn.cursor()
                
                # 1. Cargar caché de llamadas existente en SQLite
                cursor.execute("SELECT comentario, motivo_detectado, sentimiento, prob_churn, modelo_routing FROM analisis_llamadas")
                rows = cursor.fetchall()
                cache_llamadas_dict = {row[0]: {"comentario": row[0], "motivo": row[1], "sentimiento": row[2], "prob_churn": row[3], "modelo": row[4]} for row in rows}
                
                # 2. Extraer únicamente los textos ÚNICOS que NO estén en caché
                textos_unicos_llamadas_pendientes = list(set([t for t in todos_los_textos_llamadas if t not in cache_llamadas_dict]))
                
                st.toast(f"Total llamadas: {len(todos_los_textos_llamadas):,} | En caché: {len(todos_los_textos_llamadas) - len(textos_unicos_llamadas_pendientes):,} | Frases únicas a procesar: {len(textos_unicos_llamadas_pendientes):,}")

                # 3. Procesar solo las frases únicas nuevas con LAYA (respetando los 4 hilos del i7-8650U)
                if len(textos_unicos_llamadas_pendientes) > 0:
                    progress_bar = st.progress(0, text=f"Procesando {len(textos_unicos_llamadas_pendientes):,} frases únicas de llamadas con LAYA (4 núcleos)...")
                    
                    def procesar_texto_llamada(texto):
                        try:
                            res = router.predict(state=texto, questions=criterios_laya["questions"])
                            return {
                                "comentario": texto,
                                "motivo": res["answers"]["motivo_raiz"]["choice"],
                                "sentimiento": res["answers"]["sentimiento"]["legend"].get(str(round(res["answers"]["sentimiento"]["score"])), "neutral"),
                                "prob_churn": res["answers"]["riesgo_abandono"]["noul"],
                                "modelo": res["routing"]["model"]
                            }
                        except Exception as e:
                            return {"comentario": texto, "motivo": "error", "sentimiento": "neutral", "prob_churn": 0.0, "modelo": "error", "error": str(e)}

                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                        futures = {executor.submit(procesar_texto_llamada, c): c for c in textos_unicos_llamadas_pendientes}
                        completados = 0
                        for f in concurrent.futures.as_completed(futures):
                            res_res = f.result()
                            try:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO analisis_llamadas 
                                    (timestamp, comentario, motivo_detectado, sentimiento, prob_churn, modelo_routing)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (
                                    datetime.now().isoformat(), res_res["comentario"], res_res["motivo"], 
                                    res_res["sentimiento"], res_res["prob_churn"], res_res.get("modelo", "multilingual")
                                ))
                                conn.commit()
                            except Exception:
                                pass
                            
                            completados += 1
                            # CORREGIDO AQUÍ: Usando la variable correcta textos_unicos_llamadas_pendientes
                            progress_bar.progress(completados / len(textos_unicos_llamadas_pendientes), text=f"Procesando frases de llamadas... ({completados:,}/{len(textos_unicos_llamadas_pendientes):,})")
                    
                    progress_bar.empty()

                # 4. Reconstruir caché completa y mapear de forma instantánea a todas las llamadas del rango
                cursor.execute("SELECT comentario, motivo_detectado, sentimiento, prob_churn, modelo_routing FROM analisis_llamadas")
                rows_updated = cursor.fetchall()
                cache_ll_completo = {row[0]: {"comentario": row[0], "motivo": row[1], "sentimiento": row[2], "prob_churn": row[3], "modelo": row[4]} for row in rows_updated}
                conn.close()

                resultados_nlp = [cache_ll_completo.get(t, {"comentario": t, "motivo": "other", "sentimiento": "neutral", "prob_churn": 0.0, "modelo": "multilingual"}) for t in todos_los_textos_llamadas]

                df_nlp_res = pd.DataFrame(resultados_nlp)
                st.session_state["df_nlp_res"] = df_nlp_res
                st.success(f"¡Análisis NLP completado con éxito para {len(df_nlp_res):,} llamadas!")
                st.rerun()

    # Renderizar resultados comunes si existen en session_state
    if "df_nlp_res" in st.session_state and not st.session_state["df_nlp_res"].empty:
        df_act = st.session_state["df_nlp_res"].copy()

        st.markdown("---")
        st.markdown("### :material/forms_apps_script: Resumen Ejecutivo de Evaluación")

        with st.container(border=True):
            df_choice = df_act["motivo"].str.title().value_counts().reset_index()
            df_choice.columns = ["Motivo Detectado", "Cantidad"]

            df_score = df_act["sentimiento"].str.title().value_counts().reset_index()
            df_score.columns = ["Sentimiento", "Cantidad"]

            noul_counts = (df_act["prob_churn"] >= umbral_churn).value_counts()
            df_noul = pd.DataFrame([
                {"Riesgo Abandono": "SÍ (Alta Probabilidad)", "Cantidad": noul_counts.get(True, 0)},
                {"Riesgo Abandono": "NO (Baja Probabilidad)", "Cantidad": noul_counts.get(False, 0)},
            ])

            col_sum1, col_sum2, col_sum3 = st.columns(3)
            with col_sum1:
                st.markdown("**Motivo Clasificado:**")
                st.dataframe(df_choice, hide_index=True, width='stretch')
            with col_sum2:
                st.markdown("**Sentimiento / Criticidad:**")
                st.dataframe(df_score, hide_index=True, width='stretch')
            with col_sum3:
                st.markdown("**Riesgo de Abandono (Churn):**")
                st.dataframe(df_noul, hide_index=True, width='stretch')

            st.markdown("---")

            col_info_sum, col_btn_csv, col_btn_excel = st.columns([2, 1, 1])
            with col_info_sum:
                st.markdown(f"**Total registros procesados:** {len(df_act):,} | **Período:** {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}")
            
            with col_btn_csv:
                csv_data = df_act[["comentario", "motivo", "sentimiento", "prob_churn", "modelo"]].to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=":material/download: Descargar CSV",
                    data=csv_data,
                    file_name=f"laya_evaluacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width='stretch',
                )
            
            with col_btn_excel:
                df_export = df_act.rename(columns={
                    "comentario": "Texto / Registro",
                    "motivo": "Motivo Raíz",
                    "sentimiento": "Sentimiento",
                    "prob_churn": "Prob. Abandono",
                    "modelo": "Modelo LAYA"
                })
                excel_data = to_excel(df_export)
                st.download_button(
                    label=":material/download: Descargar Excel",
                    data=excel_data,
                    file_name=f"laya_evaluacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch',
                )

        st.markdown("---")
        st.subheader(":material/warning: Detalle y Alertas de Churn (Abandono Definitivo)")
        df_criticos = df_act[df_act["prob_churn"] >= umbral_churn]

        col_c1, col_c2 = st.columns(2)
        col_c1.metric("Registros en Alto Riesgo de Abandono", len(df_criticos), delta="Atención Prioritaria", delta_color="inverse")
        col_c2.metric("Tasa de Riesgo Detectada", f"{(len(df_criticos)/len(df_act)):.1%}" if len(df_act) > 0 else "0.0%")

        if not df_criticos.empty:
            st.markdown("#### :material/list: Listado Prioritario de Retención")
            st.dataframe(df_criticos[["comentario", "motivo", "prob_churn"]], width='stretch', hide_index=True)
    else:
        st.info("Selecciona una fuente arriba y haz clic en el botón de ejecución correspondiente para procesar los datos del rango de fechas seleccionado.")

