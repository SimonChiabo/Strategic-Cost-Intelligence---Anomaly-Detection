import logging
from typing import Optional, Dict, Any
import polars as pl
import pandas as pd
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
            # Extracción eficiente con Polars
            lf = pl.read_database(query=query, connection=self.db_uri).lazy()
            
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
