import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .core.config import settings

# Configuración del servidor de base de datos (PostgreSQL Neon)
db_url = settings.DATABASE_URL

if not db_url or not db_url.startswith("postgresql"):
    raise ValueError("Se requiere una URL de base de datos PostgreSQL válida en el archivo .env")

print(f"DATABASE ENGINE: Conectado a PostgreSQL ({db_url.split('@')[-1]})")

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()