import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import polars as pl
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import IsolationForest

from src.models.schema import AnomalyResult


class AnomalyLoggerAdapter(logging.LoggerAdapter):
    """Adapter para estructurar los logs del motor de anomalías."""
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        return f"[AnomalyEngine] - {msg}", kwargs


# Configuración del Logger de manera estructurada (No 'print')
base_logger = logging.getLogger(__name__)
base_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
base_logger.addHandler(handler)

engine_logger = AnomalyLoggerAdapter(base_logger, {})


class AnomalyService:
    """
    Motor encargado exclusivamente de la detección de anomalías usando Isolation Forest.
    Sigue el Principio de Responsabilidad Única (SRP).
    """

    def __init__(self, db_uri: str, model_version: str = "IForest_v1") -> None:
        self.db_uri = db_uri
        self.model_version = model_version
        
        # Parámetro extraído dinámicamente según requerimiento
        contamination_env = os.getenv('ANOMALY_CONTAMINATION', '0.02')
        self.contamination = float(contamination_env)
        
        self.pipeline = self._build_pipeline()

    def _build_pipeline(self) -> Pipeline:
        """
        Construye el pipeline de Scikit-Learn con Feature Engineering integrado.
        """
        numeric_features = ["amount"]
        numeric_transformer = StandardScaler()

        categorical_features = ["account_name", "cost_center_code"]
        categorical_transformer = OneHotEncoder(handle_unknown="ignore")

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, numeric_features),
                ("cat", categorical_transformer, categorical_features),
            ]
        )

        model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42
        )

        return Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("classifier", model)
        ])

    def _fetch_data(self) -> pl.DataFrame:
        """
        Método privado que recupera el contexto de la base de datos de manera
        eficiente usando Polars y resolviendo el JOIN lógico dictado en la BD.
        """
        query = '''
            SELECT 
                f.id as transaction_id, 
                f.amount, 
                a.account_name, 
                c.cost_center_code
            FROM fact_transactions f
            JOIN dim_accounts a ON f.account_id = a.id
            JOIN dim_cost_centers c ON f.cost_center_id = c.id
        '''
        # read_database_uri en Polars (Formato Blindado)
        return pl.read_database_uri(query=query, uri=self.db_uri, engine="connectorx")

    def fit_predict(self) -> Optional[pl.DataFrame]:
        """
        Entrena el modelo con el universo histórico disponible del Star Schema
        y computa los scores en la misma pasada.
        """
        engine_logger.info("Initializing data fetch cycle.")
        
        try:
            df = self._fetch_data()
        except Exception as e:
            engine_logger.error(f"Failed to fetch data from warehouse: {str(e)}")
            return None

        # Bloqueo estricto antioverfitting de micro datasets
        dataset_size = len(df)
        if dataset_size < 20:
            engine_logger.warning(f"Dataset too small ({dataset_size} records). Execution aborted to prevent overfitting.")
            return None

        engine_logger.info(f"Context ingested successfully: {dataset_size} patterns. Heating engine...")

        # sklearn pide interfaces compatibles (como pandas o numpy core)
        df_ml = df.select(["amount", "account_name", "cost_center_code"]).to_pandas()
        
        # 1: Normal, -1: Anomaly
        predictions = self.pipeline.fit_predict(df_ml)
        
        # Distancia a los límites de decisión. Más bajo / negativo indica fuerte anomalía.
        scores = self.pipeline.decision_function(df_ml)
        
        df = df.with_columns([
            pl.Series("is_anomaly", [bool(p == -1) for p in predictions]),
            pl.Series("anomaly_score", scores)
        ])
        
        engine_logger.info("Predictions computed and attached.")
        return df

    def save_results(self, result_df: pl.DataFrame, session: Session) -> None:
        """
        Guarda los resultados mediante iteración usando PostgreSQL Bulk Upsert (ON CONFLICT).
        Asegura que si vuelve a correrse sobre el mismo set, la idempotencia gane.
        """
        if result_df is None or len(result_df) == 0:
            engine_logger.info("Empty prediction frame, nothing pushed to storage.")
            return
            
        records_to_upsert = []
        # iter_rows() es extremadamente veloz en Polars
        for row in result_df.iter_rows(named=True):
            records_to_upsert.append({
                "transaction_id": row["transaction_id"],
                "anomaly_score": float(row["anomaly_score"]),
                "is_anomaly": row["is_anomaly"],
                "model_version": self.model_version,
                "detected_at": datetime.utcnow()
            })
            
        # Generar Sentencia Upsert de SQLAlchemy vinculada a PGSQL
        stmt = insert(AnomalyResult).values(records_to_upsert)
        
        update_conflict_action = stmt.on_conflict_do_update(
            index_elements=["transaction_id"], 
            set_={
                "anomaly_score": stmt.excluded.anomaly_score,
                "is_anomaly": stmt.excluded.is_anomaly,
                "model_version": stmt.excluded.model_version,
                "detected_at": stmt.excluded.detected_at
            }
        )
        
        try:
            session.execute(update_conflict_action)
            session.commit()
            engine_logger.info(f"Persisted {len(records_to_upsert)} records to fact_anomaly_results cleanly.")
        except Exception as e:
            session.rollback()
            engine_logger.error(f"Integrity trap on bulk insert: {str(e)}")
            raise e
