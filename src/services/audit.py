import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from src.schemas import DashboardReport, ForecastDataPoint, AuditInsight, ReportMetadata

class AuditLoggerAdapter(logging.LoggerAdapter):
    """Adapter para estructurar los logs del motor de auditoría."""
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        return f"[AuditSink] - {msg}", kwargs

# Configuración del Logger
base_logger = logging.getLogger(__name__)
if not base_logger.handlers:
    base_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    base_logger.addHandler(handler)

audit_logger = AuditLoggerAdapter(base_logger, {})

class PredictiveAuditService:
    """
    Servicio de Auditoría e Inteligencia Predictiva (Antigravity Module).
    Analiza la salud de las proyecciones, detecta anomalías estratégicas y asegura cumplimiento SOX.
    """

    def __init__(self, model_version: str = "Prophet_v1.1.5") -> None:
        self.model_version = model_version
        self.epsilon = 1e-10
        # Feriados críticos de Argentina para alertas de cuello de botella
        self.critical_holidays = {
            "05-25": "Día de la Revolución de Mayo",
            "07-09": "Día de la Independencia",
            "12-25": "Navidad",
            "01-01": "Año Nuevo"
        }

    def evaluate_model_health(self, mape_score: float, forecast_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Evalúa métricas de error y volatilidad para determinar la confiabilidad del modelo.
        """
        # Calcular Volatilidad Relativa (Vectorizado)
        # Volatility Index = (yhat_upper - yhat_lower) / yhat
        yhat = forecast_df['yhat'].values
        upper = forecast_df['yhat_upper'].values
        lower = forecast_df['yhat_lower'].values
        
        volatility_series = (upper - lower) / np.maximum(self.epsilon, np.abs(yhat))
        avg_volatility = np.nanmean(volatility_series)

        # Reliability Index (Senior Formula): 1 - (0.7 * MAPE + 0.3 * Volatility)
        # MAPE viene en formato 0-100, normalizamos a 0-1
        mape_norm = mape_score / 100.0
        reliability_index = max(0, 1 - (0.7 * mape_norm + 0.3 * avg_volatility))

        status = "Healthy"
        alerts = []

        if mape_score > 15:
            status = "High Risk"
            alerts.append(f"Model Error (MAPE: {mape_score:.2f}%) exceeds 15% threshold.")
        
        if avg_volatility > 0.5:
            alerts.append(f"Atypical Volatility detected: Interval width is {avg_volatility*100:.2f}% of predicted value.")

        return {
            "status": status,
            "reliability_index": round(reliability_index, 4),
            "avg_volatility": round(avg_volatility, 4),
            "alerts": alerts
        }

    def generate_strategic_insights(self, history_df: pd.DataFrame, forecast_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Genera insights sobre Burn Rate y cuellos de botella estacionales.
        """
        insights = []
        burn_rate_status = "Stable"

        # 1. Burn Rate Analysis (3m Forecast vs 6m History)
        # Asegurar fechas
        history_df['ds'] = pd.to_datetime(history_df['ds'])
        forecast_df['ds'] = pd.to_datetime(forecast_df['ds'])

        last_hist_date = history_df['ds'].max()
        six_months_ago = last_hist_date - timedelta(days=180)
        history_baseline = history_df[history_df['ds'] >= six_months_ago]

        # Validación de Suficiencia de Datos (Senior Defensive Logic)
        unique_months = history_baseline['ds'].dt.to_period('M').nunique()
        
        if unique_months < 3:
            burn_rate_status = "Insufficient Historical Baseline"
            insights.append("Burn Rate analysis skipped: Less than 3 months of history available for this Cost Center.")
        else:
            hist_avg = history_baseline['y'].mean()
            # Próximos 3 meses
            three_months_future = last_hist_date + timedelta(days=90)
            forecast_3m = forecast_df[forecast_df['ds'] <= three_months_future]
            forecast_avg = forecast_3m['yhat'].mean()

            if forecast_avg > hist_avg * 1.2: # 20% más
                burn_rate_status = "High Burn Rate Detected"
                perc_increase = ((forecast_avg / hist_avg) - 1) * 100
                insights.append(f"Projected spend for next 3 months is {perc_increase:.1f}% higher than 6-month historical average.")

        # 2. Holiday Bottlenecks (Casflow warnings)
        for _, row in forecast_df.iterrows():
            month_day = row['ds'].strftime('%m-%d')
            if month_day in self.critical_holidays:
                insights.append(f"Potential Cash Flow Bottleneck around {row['ds'].date()} ({self.critical_holidays[month_day]})")

        return {
            "burn_rate_status": burn_rate_status,
            "strategic_insights": insights
        }

    def validate_compliance(self, cost_center_id: Optional[int], execution_timestamp: str) -> Dict[str, Any]:
        """
        Verifica requerimientos de trazabilidad SOX.
        """
        traceability = {
            "cost_center_id": cost_center_id if cost_center_id else "Global",
            "model_version": self.model_version,
            "execution_timestamp": execution_timestamp,
            "audit_ready": True
        }
        
        return traceability

    def generate_intelligence_report(self, 
                                     mape_score: float, 
                                     history_df: pd.DataFrame, 
                                     forecast_df: pd.DataFrame,
                                     cost_center_id: Optional[int],
                                     execution_timestamp: str) -> DashboardReport:
        """
        Orquestador que genera el reporte final estructurado mediante Pydantic.
        """
        audit_logger.info("Starting predictive intelligence synthesis.")

        health = self.evaluate_model_health(mape_score, forecast_df)
        strategy = self.generate_strategic_insights(history_df, forecast_df)
        audit_trail = self.validate_compliance(cost_center_id, execution_timestamp)

        # 1. Mapeo de Forecast Data Points
        forecast_series = [
            ForecastDataPoint(
                ds=row['ds'],
                yhat=float(row['yhat']),
                yhat_lower=float(row['yhat_lower']),
                yhat_upper=float(row['yhat_upper'])
            ) for _, row in forecast_df.iterrows()
        ]

        # 2. Mapeo de Alertas e Insights a AuditInsight
        all_alerts: List[AuditInsight] = []
        
        # Procesar alertas de salud (Health)
        for msg in health["alerts"]:
            level = "critical" if "MAPE" in msg else "warning"
            label = "Model Health" if "MAPE" in msg else "Volatility"
            all_alerts.append(AuditInsight(
                label=label,
                value=f"{mape_score:.2f}%" if "MAPE" in msg else f"{health['avg_volatility']*100:.2f}%",
                level=level,
                description=msg
            ))

        # Procesar insights estratégicos (Strategy)
        for msg in strategy["strategic_insights"]:
            level = "critical" if "Burn Rate" in msg else "info"
            label = "Burn Rate" if "Burn Rate" in msg else "Seasonality"
            all_alerts.append(AuditInsight(
                label=label,
                value="High" if "Burn Rate" in msg else "Warning",
                level=level,
                description=msg
            ))

        # 3. Construcción del DashboardReport
        report = DashboardReport(
            reliability_index=health["reliability_index"],
            health_status=health["status"],
            burn_rate_status=strategy["burn_rate_status"],
            forecast_series=forecast_series,
            alerts=all_alerts,
            metadata=ReportMetadata(
                model_version=self.model_version,
                execution_timestamp=datetime.fromisoformat(execution_timestamp) if isinstance(execution_timestamp, str) else execution_timestamp
            )
        )

        audit_logger.info(f"Intelligence report synthesized. Reliability Index: {health['reliability_index']}")
        return report
