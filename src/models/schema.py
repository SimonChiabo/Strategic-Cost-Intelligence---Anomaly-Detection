from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Date, UniqueConstraint, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DimAccount(Base):
    __tablename__ = 'dim_accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_code = Column(String(50), unique=True, nullable=False)
    account_name = Column(String(100), nullable=False)
    account_type = Column(String(50), nullable=False)

class DimCostCenter(Base):
    __tablename__ = 'dim_cost_centers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cost_center_code = Column(String(50), unique=True, nullable=False)
    cost_center_name = Column(String(100), nullable=False)

class DimVendor(Base):
    __tablename__ = 'dim_vendors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_code = Column(String(50), unique=True, nullable=False)
    vendor_name = Column(String(100), nullable=False)

class DimDate(Base):
    __tablename__ = 'dim_date'
    
    date = Column(Date, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer, nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    is_weekend = Column(Integer, nullable=False) # 1 or 0
    is_holiday = Column(Integer, nullable=False) # 1 or 0

class FactTransaction(Base):
    __tablename__ = 'fact_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=False)
    
    account_id = Column(Integer, ForeignKey('dim_accounts.id', ondelete='RESTRICT'), nullable=False)
    cost_center_id = Column(Integer, ForeignKey('dim_cost_centers.id', ondelete='RESTRICT'), nullable=False)
    vendor_id = Column(Integer, ForeignKey('dim_vendors.id', ondelete='RESTRICT'), nullable=False)
    transaction_date = Column(Date, ForeignKey('dim_date.date', ondelete='RESTRICT'), nullable=False)
    
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('external_id', name='uix_external_id'),
    )

    # Relationships
    account = relationship("DimAccount")
    cost_center = relationship("DimCostCenter")
    vendor = relationship("DimVendor")
    anomaly_details = relationship("AnomalyResult", back_populates="transaction", uselist=False, cascade="all, delete-orphan")

class AnomalyResult(Base):
    __tablename__ = 'anomaly_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey('fact_transactions.id', ondelete='CASCADE'), nullable=False, unique=True)
    anomaly_score = Column(Numeric(6, 4), nullable=False)
    is_anomaly = Column(Boolean, nullable=False)
    model_version = Column(String(50), nullable=False)
    detected_at = Column(DateTime, server_default=func.now())
    
    transaction = relationship("FactTransaction", back_populates="anomaly_details")

class ForecastResult(Base):
    __tablename__ = 'fact_forecast_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cost_center_id = Column(Integer, ForeignKey('dim_cost_centers.id', ondelete='RESTRICT'), nullable=True)
    
    ds = Column(Date, nullable=False)
    yhat = Column(Numeric(12, 2), nullable=False)
    yhat_lower = Column(Numeric(12, 2), nullable=False)
    yhat_upper = Column(Numeric(12, 2), nullable=False)
    
    model_version = Column(String(50), nullable=False)
    model_metadata = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            'ds', 'cost_center_id', 'model_version',
            name='uix_forecast_ds_cc_version',
            postgresql_nulls_not_distinct=True
        ),
    )

    # Relationships
    cost_center = relationship("DimCostCenter")
