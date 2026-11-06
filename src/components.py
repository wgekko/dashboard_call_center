# -*- coding: utf-8 -*-
"""
Componentes reutilizables de UI y diálogos en Streamlit.
"""
import streamlit as st

def aplicar_estilo_grafico(fig, altura: int = 400):
    """
    Aplica estilo interactivo a los gráficos Plotly con fondo transparente 
    para integrarse perfectamente con el diseño de la app.
    """
    fig.update_layout(
        height=altura,
        template="plotly",              # Plantilla neutra por defecto
        paper_bgcolor="rgba(0,0,0,0)",  # Fondo exterior transparente
        plot_bgcolor="rgba(0,0,0,0)",   # Fondo interno del gráfico transparente
        font=dict(color="#1F2937", family="sans-serif"),
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="",
        title_font_size=18,
        hovermode="closest",
    )
    
    # Mejorar la visibilidad de las líneas de cuadrícula y ejes en modo transparente
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(229, 231, 235, 0.5)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(229, 231, 235, 0.5)")
    
    return fig

@st.dialog("Umbrales de Evaluación")
def popup_umbrales(umbrales_actuales: dict) -> None:
    """Popup modal para modificar umbrales en session_state."""
    st.subheader("Ajuste de parámetros operacionales")
    col1, col2 = st.columns(2)

    with col1:
        nuevo_tiempo_espera = st.number_input("Tiempo min. espera (seg)", min_value=0, max_value=600, value=int(umbrales_actuales["tiempo_min_espera"]))
        nuevo_sl = st.number_input("Nivel de Servicio (%)", min_value=0, max_value=100, value=int(umbrales_actuales["nivel_servicio"]))
        nuevo_abandono = st.number_input("Tasa Abandono (%)", min_value=0, max_value=100, value=int(umbrales_actuales["abandono"]))
        nuevo_asa = st.number_input("ASA (seg)", min_value=0, max_value=3600, value=int(umbrales_actuales["asa"]))

    with col2:
        nuevo_aht = st.number_input("AHT (seg)", min_value=0, max_value=3600, value=int(umbrales_actuales["aht"]))
        nuevo_fcr = st.number_input("FCR (%)", min_value=0, max_value=100, value=int(umbrales_actuales["fcr"]))
        nueva_reincidencia = st.number_input("Reincidencia (%)", min_value=0, max_value=100, value=int(umbrales_actuales["reincidencia"]))
        nuevo_csat = st.number_input("CSAT Meta", min_value=1, max_value=5, value=int(umbrales_actuales["csat"]))

    if st.button("Guardar Cambios", type="primary", width='stretch'):
        st.session_state["umbrales"].update({
            "tiempo_min_espera": float(nuevo_tiempo_espera),
            "nivel_servicio": float(nuevo_sl),
            "abandono": float(nuevo_abandono),
            "asa": float(nuevo_asa),
            "aht": float(nuevo_aht),
            "fcr": float(nuevo_fcr),
            "reincidencia": float(nueva_reincidencia),
            "csat": float(nuevo_csat),
        })
        st.rerun()

@st.dialog(" Definiciones de Métricas", width="large")
def popup_definiciones() -> None:
    """Popup con el diccionario formal de métricas."""
    st.subheader("Glosario operacional")
    definiciones = [
        {"Métrica": "Nivel de Servicio (SL)", "Fórmula": "(Llamadas con espera ≤ umbral) / Total", "Meta": "≥ 80%"},
        {"Métrica": "Tasa de Abandono", "Fórmula": "Llamadas cortadas / Total", "Meta": "< 8%"},
        {"Métrica": "ASA", "Fórmula": "Tiempo medio de espera", "Meta": "≤ 30s"},
        {"Métrica": "AHT", "Fórmula": "(Duración conversación + ACW) / Atendidas", "Meta": "≤ 350s"},
        {"Métrica": "Ocupación de Agentes", "Fórmula": "AHT Total / Tiempo de Turno Disponible", "Meta": "75% - 85%"},
        {"Métrica": "Repeat Callers (24h)", "Fórmula": "% Clientes reincidentes en 24h", "Meta": "< 5%"},
    ]
    st.table(definiciones)