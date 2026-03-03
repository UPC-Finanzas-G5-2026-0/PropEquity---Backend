import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

from .core.config import settings

# 1. Obtener la URL de la base de datos
db_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")

# 2. Corrección para Render/Supabase: Cambiar "postgres://" a "postgresql://"
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# 3. Validación estricta
if not db_url or not db_url.startswith("postgresql"):
    raise ValueError("Se requiere una URL de base de datos PostgreSQL válida en el archivo .env o en las variables de entorno de Render")

# 4. Agregar el driver de psycopg2
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# SEGURIDAD: Extraemos SOLO el host para mostrar en consola, ocultando la contraseña
host_info = db_url.split('@')[-1] if '@' in db_url else "Desconocido"

print("\n" + "="*50)
print(f"Configuración de BD cargada de forma segura.")
print(f"DATABASE ENGINE: Conectado a PostgreSQL en host: {host_info}")
print("="*50 + "\n")

# 5. Configuración del Motor (Excelente configuración de pool de conexiones)
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