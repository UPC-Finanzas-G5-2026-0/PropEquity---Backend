import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

from .core.config import settings

db_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")

print("\n" + "="*50)
print(f"Buscando .env en: {ENV_PATH}")
print(f"DATABASE_URL original encontrada: {db_url}")
print("="*50 + "\n")

if not db_url or not db_url.startswith("postgresql"):
    raise ValueError("Se requiere una URL de base de datos PostgreSQL válida en el archivo .env")

if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

host_info = db_url.split('@')[-1] if '@' in db_url else "Desconocido"
print(f"DATABASE ENGINE: Conectado a PostgreSQL ({host_info})")

engine = create_engine(
    db_url, 
    pool_pre_ping=True,  # Verifica si la conexión está viva antes de usarla
    pool_recycle=300     # Renueva las conexiones cada 5 minutos por seguridad
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()