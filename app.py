import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.services.forecaster import FinancialForecaster
from src.services.audit import PredictiveAuditService
from src.services.exceptions import InsufficientDataError
from src.models.schema import DimCostCenter
from src.schemas import DashboardReport, AuditInsight, ForecastDataPoint, ReportMetadata

# 1. Configuración de Entorno y Estética
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "")

st.set_page_config(
    page_title="FinancialForecaster | Strategic Cost Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS para Badges y Estilo Profesional
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .badge { padding: 4px 12px; border-radius: 15px; font-weight: bold; font-size: 0.9rem; display: inline-block; margin-right: 10px; }
    .badge-healthy { background-color: #238636; color: white; }
    .badge-risk { background-color: #da3633; color: white; }
    .insight-card { background-color: #161b22; padding: 20px; border-radius: 8px; border-left: 5px solid #58a6ff; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. Sidebar - Gestión de Modo y Escenarios
st.sidebar.title("🛠️ Command Center")
st.sidebar.markdown("---")

demo_mode_active = st.sidebar.toggle("🚀 Activar Modo Demostración", value=(not DATABASE_URL))
MOCK_MODE = demo_mode_active

mock_scenario = "Healthy Growth"
if MOCK_MODE:
    st.sidebar.warning("Usando Datos Simulados")
    mock_scenario = st.sidebar.selectbox(
        "Simular Escenario",
        options=["Healthy Growth", "High Volatility (High Risk)", "Critical Burn Rate", "Insufficient Data"]
    )
else:
    st.sidebar.success("Conectado a Base de Datos")

# 3. Gestión de Conexión y Datos (Caché)
@st.cache_resource
def get_engine():
    if MOCK_MODE or not DATABASE_URL: return None
    return create_engine(DATABASE_URL)

@st.cache_data
def get_cost_centers():
    if MOCK_MODE:
        return {"Marketing & Growth": 1, "R&D Infrastructure": 2, "General & Administrative": 3}
    try:
        engine = get_engine()
        if engine is None: return {"Modo Real (Sin DB)": 0}
        with sessionmaker(bind=engine)() as session:
            result = session.execute(select(DimCostCenter))
            return {cc.cost_center_name: cc.id for cc in result.scalars().all()}
    except Exception: return {"Error de Conexión": 0}

cost_centers = get_cost_centers()
selected_cc_name = st.sidebar.selectbox("Centro de Costo", options=list(cost_centers.keys()))
selected_cc_id = cost_centers[selected_cc_name]

st.sidebar.date_input("Horizonte de Análisis", value=[datetime.now() - timedelta(days=365), datetime.now()])
run_pipeline = st.sidebar.button("Generar Inteligencia", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info("FinancialForecaster Engine v1.1.5")

# 4. Main Panel
st.title("📈 Cost Intelligence Dashboard")

if run_pipeline:
    try:
        with st.spinner("Sintetizando Inteligencia Probabilística..."):
            if MOCK_MODE:
                now = datetime.now()
                # Escenario de Fallo: Datos Insuficientes
                if mock_scenario == "Insufficient Data":
                    raise InsufficientDataError("Se requieren al menos 30 puntos de datos. Encontrados: 12")

                # Generar Historia según escenario
                n_days = 200
                noise_scale = 50 if mock_scenario != "High Volatility (High Risk)" else 300
                
                history_y = [1000 + (i * 2) + (np.random.randn() * noise_scale) for i in range(n_days)]
                
                if mock_scenario == "Critical Burn Rate":
                    # Forzar incremento súbito en el historial reciente
                    for i in range(150, 200): history_y[i] *= 1.8

                history_df = pd.DataFrame({
                    'ds': [now - timedelta(days=i) for i in range(n_days, 0, -1)],
                    'y': history_y
                })
                
                # Generar Forecast
                future_dates = [now + timedelta(days=i) for i in range(1, 366)]
                trend_mult = 1.5 if mock_scenario != "Critical Burn Rate" else 2.5
                
                forecast_df = pd.DataFrame({
                    'ds': future_dates,
                    'yhat': [history_df['y'].iloc[-1] + (i * trend_mult) for i in range(len(future_dates))],
                    'yhat_lower': [history_df['y'].iloc[-1] + (i * trend_mult) - (100 + i*0.5) for i in range(len(future_dates))],
                    'yhat_upper': [history_df['y'].iloc[-1] + (i * trend_mult) + (100 + i*0.5) for i in range(len(future_dates))]
                })

                # Configurar Reporte según escenario
                health_status = "Healthy"
                reliability = 0.92
                burn_status = "Stable"
                alerts = [
                    AuditInsight(label="Seasonal Trend", value="Normal", level="info", description="Incremento orgánico consistente.")
                ]

                if mock_scenario == "High Volatility (High Risk)":
                    health_status = "High Risk"
                    reliability = 0.65
                    alerts.append(AuditInsight(label="Volatility Warning", value="Critical", level="critical", description="La dispersión de los datos sugiere una predicción poco fiable."))
                
                if mock_scenario == "Critical Burn Rate":
                    burn_status = "High Burn Rate Detected"
                    reliability = 0.88
                    alerts.append(AuditInsight(label="Budget alert", value="Critical", level="critical", description="El gasto proyectado supera la media histórica en un 80%."))

                report = DashboardReport(
                    reliability_index=reliability,
                    health_status=health_status,
                    burn_rate_status=burn_status,
                    forecast_series=[],
                    alerts=alerts,
                    metadata=ReportMetadata(model_version="Prophet_v1.1.5_MOCK", execution_timestamp=now)
                )
            else:
                # Lógica Real
                forecaster = FinancialForecaster(db_uri=DATABASE_URL)
                audit_service = PredictiveAuditService()
                engine = get_engine()
                with sessionmaker(bind=engine)() as session:
                    history_df = forecaster._get_clean_history(cost_center_id=selected_cc_id)
                    model, mape_score = forecaster.train_baseline(history_df)
                    future = model.make_future_dataframe(periods=12, freq='MS')
                    forecast_df = model.predict(future)
                    report = audit_service.generate_intelligence_report(
                        mape_score=mape_score, history_df=history_df, forecast_df=forecast_df,
                        cost_center_id=selected_cc_id, execution_timestamp=datetime.now().isoformat()
                    )

            # RENDERIZADO
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                status_class = "badge-healthy" if report.health_status == "Healthy" else "badge-risk"
                st.markdown(f"<h3>Estado Actual: <span class='badge {status_class}'>{report.health_status.upper()}</span></h3>", unsafe_allow_html=True)
            with col2: st.metric("Reliability Index", f"{report.reliability_index*100:.1f}%")
            with col3: st.metric("Burn Rate", report.burn_rate_status)

            st.subheader("Proyección Estratégica de Costos")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(forecast_df['ds']) + list(forecast_df['ds'])[::-1],
                y=list(forecast_df['yhat_upper']) + list(forecast_df['yhat_lower'])[::-1],
                fill='toself', fillcolor='rgba(88, 166, 255, 0.2)', line=dict(color='rgba(255,255,255,0)'), name='Confianza (95%)'
            ))
            fig.add_trace(go.Scatter(x=history_df['ds'], y=history_df['y'], mode='lines', line=dict(color='#8b949e', width=1), name='Histórico Real'))
            fig.add_trace(go.Scatter(x=forecast_df['ds'], y=forecast_df['yhat'], mode='lines', line=dict(color='#58a6ff', width=3), name='Predicción'))
            fig.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=20, b=0), height=500)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"Auditoría y Alertas [Escenario: {mock_scenario if MOCK_MODE else 'Real'}]")
            if not report.alerts: st.success("No se detectaron alertas.")
            else:
                cols = st.columns(3)
                for i, alert in enumerate(report.alerts):
                    with cols[i % 3]:
                        st.markdown(f"<div class='insight-card'><small>{alert.level.upper()}</small><h4>{alert.label}</h4><p>{alert.description}</p><b>Valor: {alert.value}</b></div>", unsafe_allow_html=True)

    except InsufficientDataError as e:
        st.warning(f"⚠️ Datos Insuficientes: {str(e)}")
        st.info("Recolecte más historial transaccional antes de generar proyecciones.")
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Configure los parámetros y presione 'Generar Inteligencia' arriba para comenzar.")
