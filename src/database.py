import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Única fuente de verdad para el Modelo
Base = declarative_base()

def get_db_uris():
    """
    Normaliza las URIs para los diferentes motores.
    """
    base_uri = ""
    try:
        if "DATABASE_URL" in st.secrets:
            base_uri = st.secrets["DATABASE_URL"]
    except:
        pass

    if not base_uri:
        base_uri = os.getenv("DATABASE_URL", "")

    if not base_uri:
        return "", ""

    # Limpieza: Asegurar postgresql://
    clean_uri = base_uri.replace("postgres://", "postgresql://")
    
    # SQLAlchemy pide +psycopg2
    sqlalchemy_uri = clean_uri
    if "+psycopg2" not in clean_uri:
        sqlalchemy_uri = clean_uri.replace("postgresql://", "postgresql+psycopg2://")
    
    # ConnectorX pide esquema puro (si se usara), pero aquí usaremos el engine.
    connectorx_uri = clean_uri.replace("postgresql+psycopg2://", "postgresql://")
    
    return sqlalchemy_uri, connectorx_uri

def get_engine():
    sql_uri, _ = get_db_uris()
    if not sql_uri:
        return None
    # pool_pre_ping=True es VITAL para el Pooler de Supabase
    return create_engine(sql_uri, pool_pre_ping=True, pool_recycle=300)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Variables exportadas para conveniencia
SQLALCHEMY_DATABASE_URL, RAW_DATABASE_URL = get_db_uris()
