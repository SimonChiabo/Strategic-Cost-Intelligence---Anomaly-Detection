import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.services.forecaster import FinancialForecaster
from src.services.audit import PredictiveAuditService
from src.services.exceptions import InsufficientDataError
from src.models.schema import DimCostCenter
from src.schemas import DashboardReport

# 1. Configuración de Entorno y Estética
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

st.set_page_config(
    page_title="FinancialForecaster | Strategic Cost Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS para Badges y Estilo Profesional
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .badge {
        padding: 4px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin-right: 10px;
    }
    .badge-healthy { background-color: #238636; color: white; }
    .badge-risk { background-color: #da3633; color: white; }
    .insight-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 8px;
        border-left: 5px solid #58a6ff;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Gestión de Conexión y Datos (Caché)
@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL)

@st.cache_data
def get_cost_centers():
    engine = get_engine()
    with sessionmaker(bind=engine)() as session:
        result = session.execute(select(DimCostCenter))
        return {cc.cost_center_name: cc.id for cc in result.scalars().all()}

# 3. Sidebar
st.sidebar.title("🛠️ Command Center")
st.sidebar.markdown("---")

cost_centers = get_cost_centers()
selected_cc_name = st.sidebar.selectbox("Centro de Costo", options=list(cost_centers.keys()))
selected_cc_id = cost_centers[selected_cc_name]

st.sidebar.date_input("Horizonte de Análisis", value=[datetime.now() - pd.Timedelta(days=365), datetime.now()])

run_pipeline = st.sidebar.button("🚀 Run Forecast Pipeline", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info("FinancialForecaster Engine v1.1.5")

# 4. Main Panel
st.title("📈 Cost Intelligence Dashboard")

if run_pipeline:
    try:
        with st.spinner("Sintetizando Inteligencia Probabilística..."):
            # Inicialización de Servicios
            forecaster = FinancialForecaster(db_uri=DATABASE_URL)
            audit_service = PredictiveAuditService()
            
            # Ejecución del Pipeline (Modo Reporte)
            engine = get_engine()
            with sessionmaker(bind=engine)() as session:
                # Obtener Historial Limpio
                history_df = forecaster._get_clean_history(cost_center_id=selected_cc_id)
                
                # Entrenar y Evaluar
                model, mape_score = forecaster.train_baseline(history_df)
                
                # Generar Proyecciones Futuras (12 meses)
                future = model.make_future_dataframe(periods=12, freq='MS')
                forecast_df = model.predict(future)
                
                # Generar Reporte de Auditoría (DashboardReport Pydantic)
                report: DashboardReport = audit_service.generate_intelligence_report(
                    mape_score=mape_score,
                    history_df=history_df,
                    forecast_df=forecast_df,
                    cost_center_id=selected_cc_id,
                    execution_timestamp=datetime.now().isoformat()
                )

                # --- HEADER: Badges y Métricas ---
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    status_class = "badge-healthy" if report.health_status == "Healthy" else "badge-risk"
                    st.markdown(f"""
                        <h3>Estado Actual: 
                        <span class='badge {status_class}'>{report.health_status.upper()}</span>
                        </h3>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.metric("Reliability Index", f"{report.reliability_index*100:.1f}%")
                
                with col3:
                    st.metric("Burn Rate", report.burn_rate_status)

                # --- MAIN CHART: Plotly Probabilístico ---
                st.subheader("Proyección Estratégica de Costos")
                
                fig = go.Figure()

                # Banda de Confianza (Sombreada)
                fig.add_trace(go.Scatter(
                    x=forecast_df['ds'].tolist() + forecast_df['ds'].tolist()[::-1],
                    y=forecast_df['yhat_upper'].tolist() + forecast_df['yhat_lower'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(88, 166, 255, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Intervalo de Confianza (95%)',
                    hoverinfo="skip"
                ))

                # Línea Histórica
                fig.add_trace(go.Scatter(
                    x=history_df['ds'],
                    y=history_df['y'],
                    mode='lines',
                    line=dict(color='#8b949e', width=1),
                    name='Histórico Real'
                ))

                # Línea de Predicción (yhat)
                fig.add_trace(go.Scatter(
                    x=forecast_df['ds'],
                    y=forecast_df['yhat'],
                    mode='lines',
                    line=dict(color='#58a6ff', width=3),
                    name='Predicción Central (yhat)'
                ))

                fig.update_layout(
                    template="plotly_dark",
                    hovermode="x unified",
                    margin=dict(l=0, r=0, t=20, b=0),
                    height=500,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)

                # --- INSIGHTS SECTION: Columns Grid ---
                st.subheader("Auditoría y Alertas de Negocio")
                cols = st.columns(3)
                
                if not report.alerts:
                    st.success("No se detectaron anomalías significativas en el horizonte proyectado.")
                else:
                    for i, alert in enumerate(report.alerts):
                        with cols[i % 3]:
                            st.markdown(f"""
                                <div class='insight-card'>
                                    <small>{alert.level.upper()}</small>
                                    <h4>{alert.label}</h4>
                                    <p>{alert.description}</p>
                                    <b>Valor: {alert.value}</b>
                                </div>
                            """, unsafe_allow_html=True)

    except InsufficientDataError as e:
        st.warning(f"⚠️ **Datos Insuficientes**: {str(e)}")
        st.info("Para este Centro de Costo se requiere recolectar más historial transaccional antes de generar proyecciones.")
    except Exception as e:
        st.error(f"Error en el motor financiero: {str(e)}")
        st.exception(e)
else:
    st.info("Selecciona un Centro de Costo en el panel lateral y presiona 'Run Forecast Pipeline' para comenzar.")
    
    # Dashboard stats placeholders
    col1, col2, col3 = st.columns(3)
    col1.metric("Centros de Costo", len(cost_centers))
    col2.metric("Modelo Base", "Prophet v1.1.5")
    col3.metric("Frecuencia", "Agregación Diaria")
