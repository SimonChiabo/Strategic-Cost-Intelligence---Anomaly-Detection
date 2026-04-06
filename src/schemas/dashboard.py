from datetime import datetime
from typing import List, Dict, Literal, Any
from pydantic import BaseModel, Field, ConfigDict


class ForecastDataPoint(BaseModel):
    """
    Representa un punto de datos individual en una serie de tiempo de pronóstico.
    """
    ds: datetime = Field(..., description="Marca de tiempo del pronóstico (Date Stamp)")
    yhat: float = Field(..., description="Valor predicho")
    yhat_lower: float = Field(..., description="Límite inferior del intervalo de confianza")
    yhat_upper: float = Field(..., description="Límite superior del intervalo de confianza")


class AuditInsight(BaseModel):
    """
    Información de auditoría o hallazgos detectados en los datos.
    """
    label: str = Field(..., description="Etiqueta corta del hallazgo")
    value: str = Field(..., description="Valor o métrica asociada")
    level: Literal["info", "warning", "critical"] = Field(..., description="Nivel de severidad")
    description: str = Field(..., description="Descripción detallada del insight")


class ReportMetadata(BaseModel):
    """
    Metadatos técnicos de la ejecución del reporte.
    """
    model_config = ConfigDict(protected_namespaces=())

    model_version: str = Field(..., description="Versión del modelo utilizado")
    execution_timestamp: datetime = Field(default_factory=datetime.now, description="Momento de generación del reporte")


class DashboardReport(BaseModel):
    """
    Contrato de datos principal para la UI del Dashboard.
    Define la estructura única de intercambio entre servicios y Streamlit/FastAPI.
    """
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    reliability_index: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Índice de confiabilidad del modelo (0 a 1)"
    )
    health_status: str = Field(..., description="Estado general de salud financiera (e.g., Healthy/High Risk)")
    burn_rate_status: str = Field(..., description="Estado actual del burn rate")
    
    forecast_series: List[ForecastDataPoint] = Field(
        ..., 
        description="Lista de puntos de datos proyectados"
    )
    alerts: List[AuditInsight] = Field(
        ..., 
        description="Lista de alertas e insights de auditoría"
    )
    metadata: ReportMetadata = Field(
        ..., 
        description="Metadatos de ejecución y versión"
    )
