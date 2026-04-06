from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import date
from typing import Any, Dict, List

import polars as pl
from pydantic import BaseModel, Field, field_validator


# ==========================================
# 1. VALIDADOR DE DATOS (PYDANTIC)
# ==========================================

class FinancialTransaction(BaseModel):
    """Modelo Pydantic para asegurar tipos estrictos y precisión financiera."""
    external_id: str
    account_code: str
    cost_center_code: str
    vendor_code: str
    transaction_date: date
    amount: Decimal
    currency: str = Field(default="USD", max_length=3)

    @field_validator("amount", mode="before")
    @classmethod
    def force_decimal_precision(cls, value: Any) -> Decimal:
        """
        Garantiza que cualquier flotante ingrese como representación de cadena
        primero para evitar arrastre de precisión del binario flotante.
        """
        if isinstance(value, float):
            return Decimal(str(value))
        return Decimal(value)


class DataValidator:
    """Clase utilitaria enfocada exclusivamente en la validación de lotes."""
    
    @staticmethod
    def validate_batch(records: List[Dict[str, Any]]) -> List[FinancialTransaction]:
        """
        Valida que cada diccionario del lote cumpla el esquema de FinancialTransaction.
        Rechazará de manera temprana tipos inválidos.
        """
        return [FinancialTransaction(**record) for record in records]


# ==========================================
# 2. PATRÓN ESTRATEGIA (INGESTIÓN Y POLARS)
# ==========================================

class IngestionStrategy(ABC):
    """
    Abstract Base Class para las estrategias de ingesta.
    Cualquier nueva fuente de datos debe heredar e implementar `scan`.
    """
    
    @abstractmethod
    def scan(self, source: str, **kwargs: Any) -> pl.LazyFrame:
        """
        Devuelve un Polars LazyFrame para cumplir la regla del 50% de memoria,
        aplazando la carga y armando un grafo de dependencias hasta que se llame `collect()`.
        """
        pass


class CSVIngestionStrategy(IngestionStrategy):
    def scan(self, source: str, **kwargs: Any) -> pl.LazyFrame:
        return pl.scan_csv(source, **kwargs)


class JSONIngestionStrategy(IngestionStrategy):
    def scan(self, source: str, **kwargs: Any) -> pl.LazyFrame:
        return pl.scan_ndjson(source, **kwargs)


class SQLIngestionStrategy(IngestionStrategy):
    def scan(self, source: str, **kwargs: Any) -> pl.LazyFrame:
        """
        A diferencia de CSV/JSON, SQL usa `read_database` típicamente. Para hacerlo Lazy,
        se puede simular delegando el límite a la base de datos o usando conector de backend Arrow.
        El engine lo requiere Polars en modo lazy temporal.
        """
        query: str = kwargs.get("query", f"SELECT * FROM {source}")
        uri: str = kwargs.get("connection_uri", "")
        # Nota: read_database (Estabilidad Total) usando el objeto engine de SQLAlchemy
        df = pl.read_database(query=query, connection=uri)
        
        # Parche de Normalización: Convertir Decimal (Postgres) a Float64 (Python/ML)
        # Esto previene errores de "unsupported operand type" entre decimal y float.
        return df.with_columns(
            pl.col(pl.Decimal).cast(pl.Float64)
        ).lazy()


class ParquetIngestionStrategy(IngestionStrategy):
    """
    Refleja el Principio Open-Closed: Añadido como nueva extensión sin 
    modificar al DataIngestor.
    """
    def scan(self, source: str, **kwargs: Any) -> pl.LazyFrame:
        return pl.scan_parquet(source, **kwargs)


# ==========================================
# 3. ORQUESTADOR (CONTEXTO DE LA ESTRATEGIA)
# ==========================================

class DataIngestionEngine:
    """
    Motor principal desacoplado. No conoce sobre formatos de archivos,
    solo delega a su estrategia inyectada.
    """
    
    def __init__(self, strategy: IngestionStrategy) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: IngestionStrategy) -> None:
        """Permite inyectar distintas estrategias en tiempo de ejecución."""
        self._strategy = strategy

    def extract(self, source_path_or_name: str, **kwargs: Any) -> pl.LazyFrame:
        """
        Retorna la referencia diferida al dataset, cumpliendo la regla 
        de control de huella de memoria masiva.
        """
        return self._strategy.scan(source_path_or_name, **kwargs)
