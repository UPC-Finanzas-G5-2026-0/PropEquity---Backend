import requests
import random
import string

# Configuración
BASE_URL = "https://propequity-backend.onrender.com/api/v1"

def generate_random_dni():
    return "".join(random.choices(string.digits, k=8))

def generate_random_email():
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def test_registration():
    email = generate_random_email()
    dni = generate_random_dni()
    
    payload = {
        "email": email,
        "password": "password123",
        "nombres": "Test",
        "apellidos": "User",
        "dni": dni,
        "telefono": "987654321",
        "rol_usuario": "Cliente",
        "ingreso_mensual": 5000.0,
        "codigo_tipo_ingreso": 1,
        "meses_ahorro": 0,
        "codigo_estado_civil": 1,
        "residencia": "Peruano",
        "tiene_deudor_solidario": False,
        "es_propietario_vivienda": False,
        "ha_recibido_apoyo": False,
        "tiene_credito_activo": False,
        "nombre_conyuge": "",
        "doc_conyuge": "",
        "ingreso_conyuge": 0.0,
        "conyuge_propietario": False,
        "hijos_menores_propietarios": False,
        "cantidad_creditos_fmv": 0
    }
    
    print(f"Intentando registrar usuario: {email} con DNI: {dni}...")
    
    try:
        response = requests.post(f"{BASE_URL}/auth/signup", json=payload)
        
        if response.status_code == 200:
            print("✅ Registro exitoso (Código 200)")
            data = response.json()
            print(f"ID Usuario creado: {data.get('codigo_usuario')}")
            return True
        else:
            print(f"❌ Error en el registro: Código {response.status_code}")
            print(f"Detalle: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

if __name__ == "__main__":
    test_registration()
