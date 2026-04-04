from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

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
