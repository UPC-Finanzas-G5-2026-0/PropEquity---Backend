import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    PROJECT_NAME: str = "PropEquity"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres.xwsoccjotosoowatjihj:123456789finanzas@aws-0-us-east-1.pooler.supabase.com:6543/postgres")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mi_clave_secreta_super_segura_123")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

settings = Settings()