from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from pydantic import ValidationError

from app.database import get_db
from app.models import User, RolUsuario, Client, Administrator, Advisor
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings


router = APIRouter(tags=["Authentication"])


from sqlalchemy import text

@router.post("/signup", response_model=UserResponse)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        # VALIDACIONES DE LÓGICA DE NEGOCIO
        # 1. Validación Ahorro Programado (ID 3)
        if user_in.codigo_tipo_ingreso == 3:
            if not user_in.meses_ahorro or user_in.meses_ahorro < 6:
                raise HTTPException(
                    status_code=422, 
                    detail="Para 'Ahorro programado', los meses de ahorro deben ser mínimo 6."
                )
        
        # 2. Validación Cónyuge (2: Casado, 3: Conviviente)
        if user_in.codigo_estado_civil in [2, 3]:
            if not user_in.nombre_conyuge or not user_in.doc_conyuge:
                estado = "casado" if user_in.codigo_estado_civil == 2 else "conviviente"
                raise HTTPException(
                    status_code=422,
                    detail=f"Para el estado civil '{estado}', el nombre y documento del cónyuge son obligatorios."
                )

        # 1. Verificar si el email existe
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise HTTPException(status_code=400, detail="El email ya está registrado.")

        # 2. Verificar si el DNI existe en los perfiles correspondientes
        if not user_in.dni:
             raise HTTPException(status_code=400, detail="El DNI es obligatorio.")
        
        if user_in.rol_usuario == "Administrador":
            existing_dni = db.query(Administrator).filter(Administrator.dni_administrador == user_in.dni).first()
        elif user_in.rol_usuario == "Asesor":
            existing_dni = db.query(Advisor).filter(Advisor.dni_asesor == user_in.dni).first()
        elif user_in.rol_usuario == "Cliente":
            existing_dni = db.query(Client).filter(Client.dni_cliente == user_in.dni).first()
        else:
            existing_dni = None

        if existing_dni:
            raise HTTPException(status_code=400, detail=f"El DNI '{user_in.dni}' ya está registrado con otro usuario.")

        # 3. Obtener el ID del rol solicitado
        role = db.query(RolUsuario).filter(RolUsuario.tipo_rol == user_in.rol_usuario).first()
        if not role:
            raise HTTPException(status_code=400, detail=f"El rol '{user_in.rol_usuario}' no existe en el sistema.")

        # 4. Crear el Usuario base (ID se autogenera)
        new_user = User(
            email=user_in.email,
            nombres=user_in.nombres,
            apellidos=user_in.apellidos,
            password=get_password_hash(user_in.password),
            codigo_rol=role.codigo_rol
        )
        db.add(new_user)
        db.flush() # Para obtener el ID generado sin commit total
        
        # 5. Crear el Subtipo correspondiente
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
                ingreso_mensual=user_in.ingreso_mensual or 0.0,
                codigo_tipo_ingreso=user_in.codigo_tipo_ingreso,
                meses_ahorro=user_in.meses_ahorro,
                tiene_deudor_solidario=user_in.tiene_deudor_solidario,
                residencia=user_in.residencia,
                codigo_estado_civil=user_in.codigo_estado_civil,
                nombre_conyuge=user_in.nombre_conyuge,
                doc_conyuge=user_in.doc_conyuge,
                conyuge_propietario=user_in.conyuge_propietario or False,
                ingreso_conyuge=user_in.ingreso_conyuge or 0.0,
                es_propietario_vivienda=user_in.es_propietario_vivienda or False,
                recibio_apoyo_estatal=user_in.ha_recibido_apoyo or False,
                tiene_credito_fmv_activo=user_in.tiene_credito_activo or False,
                hijos_menores_propietarios=user_in.hijos_menores_propietarios or False,
                cantidad_creditos_fmv=user_in.cantidad_creditos_fmv or 0
            )
            db.add(new_profile)

        db.commit()
        db.refresh(new_user)
        return new_user
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        # Errores típicos de base de datos: claves únicas, claves foráneas, etc.
        db.rollback()
        message = str(e.orig) if getattr(e, "orig", None) else str(e)
        raise HTTPException(
            status_code=400,
            detail="No se pudo completar el registro. Es probable que el DNI o el correo ya estén registrados, o que algunos datos sean inválidos. Detalle técnico: " + message,
        )
    except Exception as e:
        db.rollback()
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error en registro: {str(e)}")

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
    
    # Inicializar campos extra
    extra_data = {
        "dni": None,
        "telefono": None,
        "ingreso_mensual": 0.0,
        "ingreso_conyuge": 0.0,
        "codigo_tipo_ingreso": 1,
        "meses_ahorro": 0,
        "tiene_deudor_solidario": False,
        "residencia": "Peruano",
        "codigo_estado_civil": 1,
        "nombre_conyuge": None,
        "doc_conyuge": None,
        "conyuge_propietario": False,
        "es_propietario_vivienda": False,
        "ha_recibido_apoyo": False,
        "tiene_credito_activo": False,
        "hijos_menores_propietarios": False,
        "cantidad_creditos_fmv": 0
    }
    
    if role_name == "Cliente":
        cp = db.query(Client).filter(Client.codigo_cliente == user.codigo_usuario).first()
        if cp:
            extra_data.update({
                "dni": cp.dni_cliente,
                "telefono": cp.telefono_cliente,
                "ingreso_mensual": float(cp.ingreso_mensual),
                "ingreso_conyuge": float(cp.ingreso_conyuge),
                "codigo_tipo_ingreso": cp.codigo_tipo_ingreso,
                "meses_ahorro": cp.meses_ahorro,
                "tiene_deudor_solidario": cp.tiene_deudor_solidario,
                "residencia": cp.residencia,
                "codigo_estado_civil": cp.codigo_estado_civil,
                "nombre_conyuge": cp.nombre_conyuge,
                "doc_conyuge": cp.doc_conyuge,
                "conyuge_propietario": cp.conyuge_propietario,
                "es_propietario_vivienda": cp.es_propietario_vivienda,
                "ha_recibido_apoyo": cp.recibio_apoyo_estatal,
                "tiene_credito_activo": cp.tiene_credito_fmv_activo,
                "hijos_menores_propietarios": cp.hijos_menores_propietarios,
                "cantidad_creditos_fmv": cp.cantidad_creditos_fmv
            })
    elif role_name == "Asesor":
        ap = db.query(Advisor).filter(Advisor.codigo_asesor == user.codigo_usuario).first()
        if ap:
            extra_data["dni"] = ap.dni_asesor
            extra_data["telefono"] = ap.telefono_asesor
    elif role_name == "Administrador":
        adp = db.query(Administrator).filter(Administrator.codigo_administrador == user.codigo_usuario).first()
        if adp:
            extra_data["dni"] = adp.dni_administrador
            extra_data["telefono"] = adp.telefono_administrador

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": role_name}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": role_name,
        "nombres": user.nombres,
        "apellidos": user.apellidos,
        "codigo_usuario": user.codigo_usuario,
        **extra_data
    }