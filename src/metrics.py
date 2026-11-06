# -*- coding: utf-8 -*-
"""
Funciones para el cálculo de KPIs operativos y métricas financieras/avanzadas.
"""
import pandas as pd
import numpy as np

def calcular_nivel_servicio(df: pd.DataFrame, umbral_seg: int) -> float | None:
    """% de llamadas con espera <= umbral sobre el total ofrecido."""
    if df.empty:
        return None
    return float(df["espera_seg"].le(umbral_seg).mean() * 100)

def calcular_tasa_abandono(df: pd.DataFrame) -> float | None:
    """% de llamadas abandonadas sobre el total ofrecido."""
    if df.empty:
        return None
    return float(df["abandonada"].mean() * 100)

def calcular_asa(df: pd.DataFrame) -> float | None:
    """Segundos promedio de espera de llamadas atendidas."""
    atendidas = df.loc[df["atendida"], "espera_seg"]
    if atendidas.empty:
        return None
    return float(atendidas.mean())

def calcular_aht(df: pd.DataFrame) -> float | None:
    """Segundos promedio de (duración + ACW) de llamadas atendidas."""
    atendidas = df.loc[df["atendida"], "aht_seg"].dropna()
    if atendidas.empty:
        return None
    return float(atendidas.mean())

def calcular_fcr(casos: pd.DataFrame) -> float | None:
    """% de casos resueltos en el primer contacto."""
    if casos.empty:
        return None
    return float(casos["fcr"].mean() * 100)

def calcular_csat_promedio(casos: pd.DataFrame) -> float | None:
    """Promedio de CSAT en escala 1-5."""
    if casos.empty:
        return None
    return float(casos["csat"].mean())

# ==========================================
# MÉTRICAS AVANZADAS (ENTERPRISE)
# ==========================================

def calcular_ocupacion_agentes(df: pd.DataFrame, horas_turno_agente: float = 8.0) -> float | None:
    """
    Ocupación = (Tiempo de conversación + ACW total) / (Agentes Activos * Horas Turno * 3600)
    """
    atendidas = df.loc[df["atendida"] & (df["id_agente"] != "")]
    if atendidas.empty:
        return None
    agentes_activos = atendidas["id_agente"].nunique()
    tiempo_atencion_total = atendidas["aht_seg"].sum()
    tiempo_disponible_total = agentes_activos * horas_turno_agente * 3600
    if tiempo_disponible_total == 0:
        return None
    return float(min(100.0, (tiempo_atencion_total / tiempo_disponible_total) * 100))

def calcular_repeat_callers_24h(df: pd.DataFrame) -> float | None:
    """
    % de clientes que llamaron más de una vez en un intervalo de 24 horas.
    """
    if df.empty or "id_cliente" not in df.columns:
        return None
    
    df_sorted = df.sort_values(["id_cliente", "fecha_hora_entrada"]).copy()
    df_sorted["diff_horas"] = df_sorted.groupby("id_cliente")["fecha_hora_entrada"].diff().dt.total_seconds() / 3600.0
    
    reincidentes = df_sorted["diff_horas"].between(0.0001, 24.0, inclusive="both").sum()
    total_llamadas = len(df_sorted)
    
    return float((reincidentes / total_llamadas) * 100) if total_llamadas > 0 else 0.0

def calcular_valor_en_riesgo(casos: pd.DataFrame) -> float:
    """
    Suma monetaria del valor de las órdenes asociadas a casos con reincidencia.
    """
    if casos.empty:
        return 0.0
    return float(casos.loc[casos["reincidencia"] == 1, "valor_orden"].sum())

#------------- incorporacion de funciones para una mejora en el analisis de datos -----------------
# -*- coding: utf-8 -*-
"""
Funciones para el cálculo de KPIs operativos, métricas financieras y herramientas estadísticas avanzadas.
"""
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.linear_model import LogisticRegression

def calcular_nivel_servicio(df: pd.DataFrame, umbral_seg: int) -> float | None:
    if df.empty:
        return None
    return float(df["espera_seg"].le(umbral_seg).mean() * 100)

def calcular_tasa_abandono(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    return float(df["abandonada"].mean() * 100)

def calcular_asa(df: pd.DataFrame) -> float | None:
    atendidas = df.loc[df["atendida"], "espera_seg"]
    if atendidas.empty:
        return None
    return float(atendidas.mean())

def calcular_aht(df: pd.DataFrame) -> float | None:
    atendidas = df.loc[df["atendida"], "aht_seg"].dropna()
    if atendidas.empty:
        return None
    return float(atendidas.mean())

def calcular_fcr(casos: pd.DataFrame) -> float | None:
    if casos.empty:
        return None
    return float(casos["fcr"].mean() * 100)

def calcular_csat_promedio(casos: pd.DataFrame) -> float | None:
    if casos.empty:
        return None
    return float(casos["csat"].mean())

def calcular_ocupacion_agentes(df: pd.DataFrame, horas_turno_agente: float = 8.0) -> float | None:
    atendidas = df.loc[df["atendida"] & (df["id_agente"] != "")]
    if atendidas.empty:
        return None
    agentes_activos = atendidas["id_agente"].nunique()
    tiempo_atencion_total = atendidas["aht_seg"].sum()
    tiempo_disponible_total = agentes_activos * horas_turno_agente * 3600
    if tiempo_disponible_total == 0:
        return None
    return float(min(100.0, (tiempo_atencion_total / tiempo_disponible_total) * 100))

def calcular_repeat_callers_24h(df: pd.DataFrame) -> float | None:
    if df.empty or "id_cliente" not in df.columns:
        return None
    df_sorted = df.sort_values(["id_cliente", "fecha_hora_entrada"]).copy()
    df_sorted["diff_horas"] = df_sorted.groupby("id_cliente")["fecha_hora_entrada"].diff().dt.total_seconds() / 3600.0
    reincidentes = df_sorted["diff_horas"].between(0.0001, 24.0, inclusive="both").sum()
    total_llamadas = len(df_sorted)
    return float((reincidentes / total_llamadas) * 100) if total_llamadas > 0 else 0.0

def calcular_valor_en_riesgo(casos: pd.DataFrame) -> float:
    if casos.empty:
        return 0.0
    return float(casos.loc[casos["reincidencia"] == 1, "valor_orden"].sum())

# ==============================================================================
# HERRAMIENTAS ESTADÍSTICAS Y MATEMÁTICAS AVANZADAS
# ==============================================================================

def calcular_estadisticas_espera(df: pd.DataFrame) -> dict:
    """Calcula Mediana (P50) y Percentil 90 (P90) de tiempo de espera sin sesgo por outliers."""
    if df.empty:
        return {"p50": 0.0, "p90": 0.0, "iqr": 0.0}
    espera = df["espera_seg"].dropna()
    p25 = np.percentile(espera, 25)
    p50 = np.percentile(espera, 50)
    p75 = np.percentile(espera, 75)
    p90 = np.percentile(espera, 90)
    return {"p50": float(p50), "p90": float(p90), "iqr": float(p75 - p25)}

def modelo_regresion_abandono(df: pd.DataFrame) -> pd.DataFrame:
    """Regresión Logística para predecir curva de probabilidad de abandono según tiempo de espera."""
    if df.empty or len(df) < 50:
        return pd.DataFrame(columns=["espera_seg", "prob_abandono"])
    
    X = df[["espera_seg"]].values
    y = df["abandonada"].astype(int).values
    
    model = LogisticRegression()
    model.fit(X, y)
    
    rango_espera = np.arange(0, int(df["espera_seg"].max() or 300), 5).reshape(-1, 1)
    probs = model.predict_proba(rango_espera)[:, 1] * 100
    
    return pd.DataFrame({"espera_seg": rango_espera.flatten(), "prob_abandono": probs})

def modelo_arbol_csat_critico(df_unido: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Árbol de Decisión para identificar patrones clave de CSAT Crítico (<= 2 estrellas)."""
    if df_unido.empty or "csat" not in df_unido.columns:
        return pd.DataFrame(), "Datos insuficientes"
    
    data = df_unido.dropna(subset=["csat", "espera_seg", "duracion_seg", "acw_seg"]).copy()
    if len(data) < 50:
        return pd.DataFrame(), "Se requieren más de 50 casos para entrenar el árbol."
    
    data["target"] = (data["csat"] <= 2).astype(int)
    
    X = data[["espera_seg", "duracion_seg", "acw_seg"]]
    y = data["target"]
    
    clf = DecisionTreeClassifier(max_depth=3, random_state=42)
    clf.fit(X, y)
    
    importancias = pd.DataFrame({
        "Variable": ["Tiempo Espera (s)", "Tiempo Atención (s)", "Trabajo Post-Llamada (s)"],
        "Importancia (%)": clf.feature_importances_ * 100
    }).sort_values("Importancia (%)", ascending=False)
    
    reglas = export_text(clf, feature_names=["Espera", "Atención", "ACW"])
    return importancias, reglas

def calcular_pareto_reincidencia(casos: pd.DataFrame) -> pd.DataFrame:
    """Análisis de Pareto (80/20) sobre el Valor Financiero en Riesgo por Categoria."""
    if casos.empty:
        return pd.DataFrame()
    
    pareto = casos.loc[casos["reincidencia"] == 1].groupby("categoria_etiqueta")["valor_orden"].sum().reset_index()
    pareto = pareto.sort_values("valor_orden", ascending=False)
    
    pareto["pct_acumulado"] = (pareto["valor_orden"].cumsum() / pareto["valor_orden"].sum()) * 100
    return pareto