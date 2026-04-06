import os
import streamlit as st
from typing import Tuple

def get_db_uris() -> Tuple[str, str]:
    """
    Obtiene y limpia las URIs de conexión para SQLAlchemy y Polars/ConnectorX.
    Centraliza la lógica para evitar errores de dialecto y drivers.
    """
    # 1. Intentamos obtener de Streamlit Secrets, fallback a Variables de Entorno
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

    # 2. Limpieza Universal (Soporte para postgres:// y postgresql://)
    # SQLAlchemy 1.4+ requiere 'postgresql://' obligatoriamente
    clean_uri = base_uri.replace("postgres://", "postgresql://")
    
    # 3. Versión para SQLAlchemy (inyectamos el driver psycopg2)
    if "postgresql+psycopg2://" not in clean_uri:
        sqlalchemy_uri = clean_uri.replace("postgresql://", "postgresql+psycopg2://")
    else:
        sqlalchemy_uri = clean_uri
        
    # 4. Versión para ConnectorX (Pura, sin drivers de Python)
    # ConnectorX es un motor en Rust, no entiende '+psycopg2'
    connectorx_uri = clean_uri.replace("postgresql+psycopg2://", "postgresql://")
    
    return sqlalchemy_uri, connectorx_uri
