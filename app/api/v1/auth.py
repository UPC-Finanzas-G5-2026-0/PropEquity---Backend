from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.models import User, RolUsuario, Client, Administrator, Advisor
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings


router = APIRouter(tags=["Authentication"])


from sqlalchemy import text

@router.post("/signup", response_model=UserResponse)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    # --- DEBUG START ---
    try:
        with open("debug_auth.log", "w") as f:
            f.write(f"DEBUG REQUEST: Binding URL = {db.get_bind().url}\n")
            tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            f.write(f"DEBUG REQUEST: Tables in DB = {[t[0] for t in tables]}\n")
            
            # Test RAW SELECT
            try:
                db.execute(text("SELECT * FROM users LIMIT 1"))
                f.write("DEBUG RAW SELECT: Success\n")
            except Exception as e:
                 f.write(f"DEBUG RAW SELECT ERROR: {e}\n")

            # Test ORM Generation
            try:
                stmt = db.query(User).statement
                f.write(f"DEBUG ORM SQL: {stmt.compile(db.get_bind(), compile_kwargs={'literal_binds': True})}\n")
            except Exception as e:
                f.write(f"DEBUG ORM SQL ERROR: {e}\n")
            
            # Test RolUsuario Query
            try:
                roles_count = db.query(RolUsuario).count()
                f.write(f"DEBUG ROLE QUERY: Success, count={roles_count}\n")
            except Exception as e:
                f.write(f"DEBUG ROLE QUERY ERROR: {e}\n")

    except Exception as e:
        with open("debug_auth.log", "a") as f:
            f.write(f"DEBUG REQUEST ERROR: {e}\n")
    # --- DEBUG END ---

    try:
        # 1. Verificar si el email existe
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise HTTPException(status_code=400, detail="El email ya está registrado.")

        # 2. Obtener el ID del rol solicitado
        role = db.query(RolUsuario).filter(RolUsuario.tipo_rol == user_in.rol_usuario).first()
        if not role:
            raise HTTPException(status_code=400, detail=f"El rol '{user_in.rol_usuario}' no existe en el sistema.")

        # 3. Crear el Usuario base (ID se autogenera)
        new_user = User(
            email=user_in.email,
            nombres=user_in.nombres,
            apellidos=user_in.apellidos,
            password=get_password_hash(user_in.password),
            codigo_rol=role.codigo_rol
        )
        db.add(new_user)
        db.flush() # Para obtener el ID generado sin commit total
        
        # 4. Crear el Subtipo correspondiente
        if not user_in.dni:
            raise HTTPException(status_code=400, detail="El DNI es obligatorio para todos los perfiles de usuario.")

        if user_in.rol_usuario == "Administrador":
            new_profile = Administrator(
                codigo_administrador=new_user.codigo_usuario,
                dni_administrador=user_in.dni,
                telefono_administrador=user_in.telefono
            )
            db.add(new_profile)
        elif user_in.rol_usuario == "Asesor":
            new_profile = Advisor(
                codigo_asesor=new_user.codigo_usuario,
                dni_asesor=user_in.dni,
                telefono_asesor=user_in.telefono
            )
            db.add(new_profile)
        elif user_in.rol_usuario == "Cliente":
            new_profile = Client(
                codigo_cliente=new_user.codigo_usuario,
                dni_cliente=user_in.dni,
                telefono_cliente=user_in.telefono,
                ingreso_mensual=user_in.ingreso_mensual or 0.0
            )
            db.add(new_profile)

        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener el nombre del rol
    role_name = user.rol_rel.tipo_rol if user.rol_rel else "Cliente"
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": role_name
        }, 
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": role_name,
        "nombres": user.nombres,
        "apellidos": user.apellidos,
        "codigo_usuario": user.codigo_usuario
    }