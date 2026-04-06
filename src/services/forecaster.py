import logging
from typing import Optional, Dict, Any
import polars as pl
import pandas as pd
import numpy as np
from prophet import Prophet
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.models.schema import ForecastResult
from src.services.exceptions import InsufficientDataError

class ForecasterLoggerAdapter(logging.LoggerAdapter):
    """Adapter para estructurar los logs del motor de predicción."""
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        return f"[ForecasterEngine] - {msg}", kwargs

# Configuración del Logger de manera estructurada
base_logger = logging.getLogger(__name__)
# Evitar duplicados si el logger ya tiene handlers
if not base_logger.handlers:
    base_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    base_logger.addHandler(handler)

forecaster_logger = ForecasterLoggerAdapter(base_logger, {})

class FinancialForecaster:
    """
    Servicio encargado de la preparación de datos y generación de proyecciones financieras.
    Utiliza Polars para el procesamiento de datos masivos y Prophet para la predicción.
    """

    def __init__(self, db_uri: str) -> None:
        self.db_uri = db_uri

    def _get_clean_history(self, cost_center_id: Optional[int] = None) -> pd.DataFrame:
        """
        Extrae y limpia el historial de transacciones, excluyendo anomalías confirmadas.
        Garantiza granularidad diaria y compatibilidad con Prophet.
        """
        forecaster_logger.info("Initializing historical data extraction.")

        # SQL Query con LEFT JOIN para auditoría de anomalías
        # is_anomaly IS NOT TRUE incluye tanto los False (auditados limpios) como los NULL (pendientes)
        query = """
            SELECT 
                t.transaction_date,
                t.amount,
                t.cost_center_id,
                ar.is_anomaly
            FROM fact_transactions t
            LEFT JOIN anomaly_results ar ON t.id = ar.transaction_id
            WHERE ar.is_anomaly IS NOT TRUE
        """

        try:
            # Extracción eficiente con Polars (Formato Blindado)
            lf = pl.read_database_uri(query=query, uri=self.db_uri, engine="connectorx").lazy()
            
            # Filtro opcional por Centro de Costo (Granularidad)
            if cost_center_id is not None:
                lf = lf.filter(pl.col("cost_center_id") == cost_center_id)

            # Preparación de la Serie de Tiempo:
            # 1. Asegurar tipo Date (limpiar timestamps si existieran)
            # 2. Agrupar por día (ds)
            # 3. Sumar montos (y)
            df_cleaned = (
                lf.with_columns(
                    pl.col("transaction_date").cast(pl.Date).alias("ds")
                )
                .group_by("ds")
                .agg(pl.col("amount").sum().alias("y"))
                .sort("ds")
                .collect()
            )

            total_points = len(df_cleaned)
            
            # Resilience Check: Bloqueo de predicciones con datos insuficientes
            if total_points < 30:
                forecaster_logger.error(f"Insufficient data for forecasting: {total_points} points found (Min: 30).")
                raise InsufficientDataError(f"Se requieren al menos 30 puntos de datos limpios. Encontrados: {total_points}")

            # Auditoría de limpieza
            # Para reportar cuántas anomalías se excluyeron necesitamos la cuenta total vs filtrada
            # Aunque la lógica SQL ya filtra, podríamos hacer el conteo previo si fuera necesario para métricas exactas
            forecaster_logger.info(f"Cleaned time series generated: {total_points} daily points available.")

            # Conversión a Pandas para compatibilidad directa con Prophet
            return df_cleaned.to_pandas()

        except Exception as e:
            if isinstance(e, InsufficientDataError):
                raise e
            forecaster_logger.error(f"Failed to prepare cleaning pipeline: {str(e)}")
            raise e

    def _calculate_mape(self, df: pd.DataFrame) -> float:
        """
        Calcula el Mean Absolute Percentage Error (MAPE) sobre los últimos 90 días.
        Implementa ingeniería defensiva para evitar división por cero.
        """
        # Separación del Test Set (Criterio: últimos 90 días)
        df['ds'] = pd.to_datetime(df['ds'])
        last_date = df['ds'].max()
        split_date = last_date - pd.Timedelta(days=90)
        
        train_set = df[df['ds'] < split_date]
        test_set = df[df['ds'] >= split_date]

        if len(train_set) < 30 or len(test_set) == 0:
            forecaster_logger.warning("Not enough data for a robust 90-day MAPE validation. Using 0.0 as default score.")
            return 0.0

        # Entrenamiento temporal para validación
        model = Prophet(yearly_seasonality=True, interval_width=0.95)
        model.add_country_holidays(country_name='AR')
        model.fit(train_set)

        # Predicción sobre el Test Set
        forecast = model.predict(test_set[['ds']])
        
        actual = test_set['y'].values
        predicted = forecast['yhat'].values

        # Epsilon para evitar división por cero (Senior Engineering trick)
        epsilon = 1e-10
        mape = np.mean(np.abs((actual - predicted) / np.maximum(epsilon, np.abs(actual)))) * 100
        
        return float(mape)

    def train_baseline(self, df: pd.DataFrame) -> tuple[Prophet, float]:
        """
        Entrena el modelo final Prophet y calcula su métrica de error.
        """
        # Validación Técnica (MAPE)
        mape_score = self._calculate_mape(df)
        forecaster_logger.info(f"Technical validation completed. MAPE: {mape_score:.2f}%")

        # Modelo Final: Entrenado con todo el histórico
        model = Prophet(yearly_seasonality=True, interval_width=0.95)
        model.add_country_holidays(country_name='AR')
        model.fit(df)
        
        forecaster_logger.info("Training successful. Prophet Baseline Engine is hot.")
        return model, mape_score

    def persist_forecast(self, model: Prophet, session: Session, mape_score: float, cost_center_id: Optional[int] = None) -> None:
        """
        Genera proyecciones a 12 meses y las persiste mediante una operación de Upsert idempotente.
        """
        # Generar DataFrame futuro (12 meses, frecuencia mensual)
        future = model.make_future_dataframe(periods=12, freq='MS')
        forecast = model.predict(future)

        # Filtrar solo el futuro (Prophet devuelve también el histórico)
        last_history_date = model.history['ds'].max()
        future_forecast = forecast[forecast['ds'] > last_history_date]

        records_to_upsert = []
        model_version = "Prophet_Baseline_v1"

        for _, row in future_forecast.iterrows():
            records_to_upsert.append({
                "cost_center_id": cost_center_id,
                "ds": row['ds'].date(),
                "yhat": float(row['yhat']),
                "yhat_lower": float(row['yhat_lower']),
                "yhat_upper": float(row['yhat_upper']),
                "model_version": model_version,
                "model_metadata": {
                    "mape_score": mape_score,
                    "seasonality_mode": model.seasonality_mode,
                    "interval_width": model.interval_width,
                }
            })

        if not records_to_upsert:
            forecaster_logger.warning("No future points generated. Persistence skipped.")
            return

        # Operación de Upsert (Idempotencia en Postgres)
        stmt = insert(ForecastResult).values(records_to_upsert)
        
        update_stmt = stmt.on_conflict_do_update(
            index_elements=['ds', 'cost_center_id', 'model_version'],
            set_={
                "yhat": stmt.excluded.yhat,
                "yhat_lower": stmt.excluded.yhat_lower,
                "yhat_upper": stmt.excluded.yhat_upper,
                "model_metadata": stmt.excluded.model_metadata
            }
        )

        try:
            session.execute(update_stmt)
            session.commit()
            forecaster_logger.info(f"Persistence complete. {len(records_to_upsert)} projections pushed to warehouse.")
        except Exception as e:
            session.rollback()
            forecaster_logger.error(f"Failed to persist forecast results: {str(e)}")
            raise e

    def run_baseline_pipeline(self, session: Session, cost_center_id: Optional[int] = None) -> None:
        """
        Orquestador principal del flujo de predicción financiera.
        """
        try:
            # 1. Preparación y Limpieza
            df_clean = self._get_clean_history(cost_center_id=cost_center_id)

            # 2. Validación y Entrenamiento
            model, mape_score = self.train_baseline(df_clean)

            # 3. Proyección y Persistencia
            self.persist_forecast(model, session, mape_score, cost_center_id)

            forecaster_logger.info("Pipeline execution finished successfully.")

        except Exception as e:
            forecaster_logger.error(f"Pipeline execution failed: {str(e)}")
            raise e
