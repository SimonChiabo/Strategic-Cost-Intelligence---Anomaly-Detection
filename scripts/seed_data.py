import os
import numpy as np
import polars as pl
import pandas as pd
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Importar modelos para asegurar que las tablas existen y mapear columnas
from src.models.db import Base
from src.models.schema import DimAccount, DimCostCenter, DimVendor, DimDate, FactTransaction

# Cargar variables de entorno
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def clear_data():
    """Limpia todas las tablas en orden de dependencia."""
    print("🧹 Cleaning existing data...")
    with engine.connect() as conn:
        # Desactivar temporalmente FKs si es necesario (Postgres specific) OR Truncate Cascade
        conn.execute(text("TRUNCATE TABLE anomaly_results CASCADE;"))
        conn.execute(text("TRUNCATE TABLE fact_forecast_results CASCADE;"))
        conn.execute(text("TRUNCATE TABLE fact_transactions CASCADE;"))
        conn.execute(text("TRUNCATE TABLE dim_date CASCADE;"))
        conn.execute(text("TRUNCATE TABLE dim_cost_centers CASCADE;"))
        conn.execute(text("TRUNCATE TABLE dim_accounts CASCADE;"))
        conn.execute(text("TRUNCATE TABLE dim_vendors CASCADE;"))
        conn.commit()

def generate_dim_date(start_date: date, end_date: date):
    """Genera la dimension de fechas con feriados de Argentina."""
    print("📅 Generating DimDate...")
    dates = []
    curr = start_date
    
    # Feriados fijos de Argentina (Simplificado para el seed)
    fixed_holidays = [(1, 1), (3, 24), (4, 2), (5, 1), (5, 25), (6, 20), (7, 9), (8, 17), (10, 12), (11, 20), (12, 8), (12, 25)]
    
    while curr <= end_date:
        is_weekend = 1 if curr.weekday() >= 5 else 0
        is_holiday = 1 if (curr.month, curr.day) in fixed_holidays else 0
        
        dates.append({
            "date": curr,
            "year": curr.year,
            "month": curr.month,
            "day": curr.day,
            "quarter": (curr.month - 1) // 3 + 1,
            "fiscal_quarter": (curr.month - 1) // 3 + 1,
            "fiscal_year": curr.year,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday
        })
        curr += timedelta(days=1)
    
    df_date = pd.DataFrame(dates)
    df_date.to_sql('dim_date', engine, if_exists='append', index=False)

def seed_dimensions():
    """Puebla las dimensiones básicas."""
    print("🏗️ Seeding main dimensions...")
    with Session() as session:
        # Accounts
        session.add(DimAccount(account_code="61000", account_name="Operating Expenses", account_type="Expense"))
        session.add(DimAccount(account_code="62000", account_name="Marketing & Sales", account_type="Expense"))
        
        # Scenarios (Cost Centers)
        scenarios = [
            ("CC_001", "Stable_Ops"),
            ("CC_002", "Aggressive_Growth"),
            ("CC_003", "High_Volatility"),
            ("CC_004", "Burn_Rate_Crisis")
        ]
        for code, name in scenarios:
            session.add(DimCostCenter(cost_center_code=code, cost_center_name=name))
            
        # Vendors
        session.add(DimVendor(vendor_code="V_AWS", vendor_name="Amazon Web Services"))
        session.add(DimVendor(vendor_code="V_GOOG", vendor_name="Google Cloud"))
        
        session.commit()

def generate_stochastic_transactions(start_date: date, end_date: date):
    """Genera transacciones financieras simuladas con perfiles complejos."""
    print("📈 Generating stochastic transactions via Polars...")
    
    with Session() as session:
        cc_map = {cc.cost_center_name: cc.id for cc in session.query(DimCostCenter).all()}
        account_id = session.query(DimAccount).first().id
        vendor_id = session.query(DimVendor).first().id
        
    dates = pd.date_range(start=start_date, end=end_date).date
    n_days = len(dates)
    
    all_transactions = []

    # Perfiles de simulación
    for cc_name, cc_id in cc_map.items():
        # Componente 1: Trend (Random Walk with Drift)
        drift = 0.5 # Crecimiento base diario
        noise = np.random.normal(0, 10, n_days) # Ruido base
        
        # Iniciar valor base según el perfil
        base_value = 5000 if cc_name != "Aggressive_Growth" else 2000
        values = [base_value]
        
        for i in range(1, n_days):
            # Agregar Drift y Ruido
            v = values[-1] + drift + noise[i]
            
            # Aplicar modificadores de escenario
            if cc_name == "Aggressive_Growth":
                # Crecimiento exponencial + estructural break en el mes 12
                v *= 1.002 # Pequeño interés compuesto diario
                if i > (n_days // 2): v += 100 # Structural break
            
            elif cc_name == "High_Volatility":
                # Gran varianza
                v += np.random.normal(0, 50)
            
            elif cc_name == "Burn_Rate_Crisis":
                # Salto del 40% en los últimos 30 días
                if i > (n_days - 30):
                    v *= 1.4
            
            values.append(max(v, 100)) # No montos negativos

        # Componente 2: Seasonality (Weekly & Monthly)
        for i, d in enumerate(dates):
            # Picos de Lunes (Operativo)
            if d.weekday() == 0: values[i] *= 1.2
            # Picos de fin de mes (Administrativo)
            if (d + timedelta(days=1)).day == 1: values[i] *= 1.3
            
            # Componente 3: Regional Context (Holidays)
            # Reducción drástica de actividad en feriados
            # (Simplificamos chequeo de feriado usando la misma lógica que DimDate)
            fixed_holidays = [(1, 1), (3, 24), (4, 2), (5, 1), (5, 25), (6, 20), (7, 9), (8, 17), (10, 12), (11, 20), (12, 8), (12, 25)]
            if (d.month, d.day) in fixed_holidays:
                values[i] *= 0.1 # Actividad cae al 10%
                
            all_transactions.append({
                "external_id": f"TX_{cc_name}_{d.strftime('%Y%m%d')}",
                "account_id": account_id,
                "cost_center_id": cc_id,
                "vendor_id": vendor_id,
                "transaction_date": d,
                "amount": round(values[i], 2),
                "currency": "USD"
            })

    # Inserción masiva
    df_tx = pd.DataFrame(all_transactions)
    df_tx.to_sql('fact_transactions', engine, if_exists='append', index=False, chunksize=1000)
    print(f"✅ Successfully seeded {len(all_transactions)} transactions.")

if __name__ == "__main__":
    # Rango de 2 años
    today = date.today()
    start = today - timedelta(days=730)
    
    try:
        clear_data()
        generate_dim_date(start, today + timedelta(days=365)) # Date dim hasta el futuro
        seed_dimensions()
        generate_stochastic_transactions(start, today)
        print("🚀 Seeding process completed successfully!")
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
