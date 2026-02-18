from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from ...database import get_db
from ...models import User, RolUsuario, Client, Administrator, Advisor
from ...schemas.user import UserCreate, UserResponse, Token
from ...core.security import verify_password, get_password_hash, create_access_token
from ...core.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
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

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}