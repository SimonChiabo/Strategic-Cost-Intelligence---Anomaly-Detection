import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from dotenv import load_dotenv

load_dotenv()
url_str = os.getenv("DATABASE_URL")
print(f"Testing URL: {url_str}")

try:
    url = make_url(url_str)
    print(f"Host: {url.host}")
    print(f"Port: {url.port}")
    print(f"User: {url.username}")
    print(f"Password: {url.password}")
    print(f"Database: {url.database}")
    
    engine = create_engine(url_str)
    with engine.connect() as conn:
        print("Success! Connected to database.")
except Exception as e:
    print(f"Error: {e}")
