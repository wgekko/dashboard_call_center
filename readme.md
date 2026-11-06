# 📞 Call Center Ecommerce & NLP Intelligence Dashboard

Un dashboard interactivo de nivel enterprise desarrollado con **Streamlit**, diseñado para monitorear métricas de operaciones de Call Center, análisis predictivo de calidad y clasificación inteligente de texto no estructurado utilizando el motor cognitivo **LAYA NLP**.

---

## Características Principales

- **Operaciones & Capacidad:** Monitoreo en tiempo real del Nivel de Servicio (SL), Tasa de Abandono, ASA (Tiempo de Espera Promedio), AHT (Tiempo de Atención Promedio) y Ocupación de Agentes.
- **Calidad & Finanzas:** Medición del First Contact Resolution (FCR), puntuación CSAT, Repeat Callers (24h) y cálculo del Valor de Órdenes en Riesgo.
- **Estadística Avanzada & Analítica Predictiva:**
  - Tiempos de espera robustos (Percentil 90 y Rango Intercuartílico - IQR).
  - Regresión logística para estimación de curva de probabilidad de abandono por tiempo en cola.
  - Árboles de decisión para la detección de drivers críticos de CSAT (≤ 2 estrellas).
  - Análisis de Pareto 80/20 para valor financiero en riesgo por reincidencia.
- **Motor Cognitivo LAYA (NLP):**
  - Clasificación automática de motivo raíz (Logística, Pagos, Devoluciones, Soporte Web).
  - Análisis de sentimiento y asignación de score.
  - Detección de riesgo de Churn / Abandono definitivo del cliente.
  - **Caché Inteligente de Textos Únicos (SQLite):** Sistema de persistencia histórico en local (`call_center_nlp_history.db`) que filtra frases únicas antes del procesamiento en paralelo (`ThreadPoolExecutor`, `max_workers=4`), reduciendo los tiempos de ejecución de minutos a **carga instantánea (0.2s)** en consultas subsiguientes.

---

## Estructura del Proyecto

```text
streamlitDashboardCallCenter/
├── .streamlit/
│   └── config.toml           # Configuración visual de Streamlit
├── data/                     # Datasets de entrada (CSV)
│   ├── casos_tickets.csv
│   ├── casos_tickets_base.csv
│   ├── llamadas_cdr.csv
│   └── llamadas_cdr_base.csv
├── generar-datos/            # Scripts auxiliares para simulación/sintéticos
├── src/                      # Módulos core de la aplicación
│   ├── components.py         # Componentes visuales y gráficos Plotly
│   ├── config.py             # Rutas, constantes y umbrales por defecto
│   ├── loader.py             # Carga optimizada de datos con DuckDB / Pandas
│   └── metrics.py            # Cálculo de KPIs, regresiones, árboles y Pareto
├── test/                     # Pruebas unitarias
│   └── test_metrics.py
├── app.py                    # Punto de entrada principal (Dashboard Streamlit)
├── call_center_nlp_history.db # Base de datos SQLite puente para caché NLP
└── requirements.txt          # Dependencias del proyecto

Tecnologías Utilizadas

    Lenguaje: Python 3.10+

    Frontend / UI: Streamlit

    Motor de NLP: LAYA NLP Router (multilingual)

    Procesamiento de Datos: Pandas, Numpy, DuckDB

    Persistencia de Caché: SQLite3

    Machine Learning & Stats: Scikit-learn, Statsmodels

    Visualización: Plotly Express & Plotly Graph Objects

    Concurrencia: concurrent.futures (Optimizado a 4 hilos para procesadores Quad-Core)



Instalación y Configuración
1. Clonar el repositorio
Bash

git clone (https://github.com/wgekko/dashboard_call_center.git)

cd streamlitDashboardCallCenter


2. Crear y activar entorno virtual
Bash

python -m venv venv
# En Linux/macOS:
source venv/bin/activate
# En Windows:
venv\Scripts\activate

3. Instalar dependencias
Bash

pip install -r requirements.txt

4. Ejecutar la aplicación
Bash

streamlit run app.py


video demo






https://github.com/user-attachments/assets/a8d46e1d-eb7f-40ad-b21b-7a3dd6ec5948




