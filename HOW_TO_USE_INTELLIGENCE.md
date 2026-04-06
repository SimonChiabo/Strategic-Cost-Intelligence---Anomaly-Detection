# Strategic Cost Intelligence - Predictive & Audit Layer

Este documento detalla cómo utilizar los servicios de Inteligencia Predictiva y Auditoría implementados hasta ahora, sirviendo como base para la integración con la interfaz de usuario (UI).

## Arquitectura de Servicios

### 1. FinancialForecaster (`src/services/forecaster.py`)
Es el motor central encargado de la limpieza de datos (`Polars`) y la generación de proyecciones (`Prophet`).

#### Flujo de Uso:
```python
from sqlalchemy import create_session
from src.services.forecaster import FinancialForecaster

# 1. Instanciar servicio
forecaster = FinancialForecaster(db_uri="postgresql+psycopg2://...")

# 2. Ejecutar Pipeline Completo (Limpieza -> Entrenamiento -> Persistencia)
# cost_center_id=None ejecuta un forecast global
forecaster.run_baseline_pipeline(session=db_session, cost_center_id=101)
```

**Qué sucede internamente:**
- Se excluyen anomalías confirmadas (`is_anomaly IS NOT TRUE`).
- Se agrupan los datos diariamente para asegurar patrones estacionales limpios.
- Se entrena un modelo Prophet con feriados de Argentina.
- Se persisten los resultados (12 meses a futuro) en la tabla `fact_forecast_results`.

---

### 2. PredictiveAuditService (`src/services/audit.py`)
El módulo de "Inteligencia Estratégica" que analiza los resultados persistidos y genera reportes de salud y riesgo.

#### Flujo de Uso:
```python
from src.services.audit import PredictiveAuditService

# 1. Instanciar servicio con la versión del modelo
auditor = PredictiveAuditService(model_version="Prophet_v1.1.5")

# 2. Generar Reporte de Inteligencia (JSON)
# Se le pasan los históricos, proyecciones y métricas obtenidas del Forecaster
report_json = auditor.generate_intelligence_report(
    mape_score=12.5,
    history_df=df_historia,
    forecast_df=df_proyeccion,
    cost_center_id=101,
    execution_timestamp="2026-04-06T12:00:00"
)
```

**Indicadores Generados:**
- **Reliability Index**: Puntuación de 0 a 1 ponderando el error histórico vs. la incertidumbre futura.
- **Burn Rate**: Alerta si el gasto proyectado (3 meses) excede el histórico (6 meses).
- **Audit Traceability**: Asegura que el reporte sea compatible con estándares SOX.

---

## Estructura de Datos para la UI

La UI consumirá principalmente la tabla `fact_forecast_results` y el `JSON report`. Los campos clave son:

| Campo | Propósito en UI |
| :--- | :--- |
| `ds` | Eje X del gráfico de serie de tiempo. |
| `yhat` | Línea principal del pronóstico. |
| `yhat_lower`/`upper` | Sombreado del intervalo de confianza (Área de riesgo). |
| `model_metadata` | Contiene el `mape_score` para mostrar el badge de salud del modelo. |

> [!IMPORTANT]
> **Idempotencia**: Al usar `UniqueConstraints` con `NULLS NOT DISTINCT`, la UI puede re-ejecutar predicciones sin temor a duplicar datos en la base de datos.
> **Resiliencia**: Si la UI intenta graficar un centro de costo con menos de 30 días de historia, el sistema lanzará un `InsufficientDataError` controlado.

## Próximos Pasos (Interface/UI)
- Visualización de Gráfico "Area Chart" con `yhat_lower/upper`.
- Dashboard de Alertas Estratégicas basado en el JSON de auditoría.
- Selector de Granularidad (Global vs. Centro de Costo).
