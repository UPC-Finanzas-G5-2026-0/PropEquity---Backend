from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_simulation_no_grace():
    """Prueba 1: Crédito estándar sin periodo de gracia"""
    payload = {
        "precio_venta": 200000.0,
        "cuota_inicial": 20000.0,
        "tea": 0.12,
        "plazo_meses": 60,
        "tipo_gracia": "NINGUNO",
        "meses_gracia": 0
    }
    response = client.post("/api/v1/simulator/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
 
    assert len(data["cronograma"]) == 60
    assert data["cronograma"][-1]["saldo"] == 0.0 
    assert data["van"] > 0  

def test_simulation_total_grace():
    """Prueba 2: Crédito con 3 meses de Gracia Total (Capitalización)"""
    payload = {
        "precio_venta": 300000.0,
        "cuota_inicial": 30000.0,
        "tea": 0.10,
        "plazo_meses": 120,
        "tipo_gracia": "TOTAL",
        "meses_gracia": 3
    }
    response = client.post("/api/v1/simulator/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
 
    for i in range(3):
        assert data["cronograma"][i]["cuota"] == 0.0
  
        assert data["cronograma"][i]["saldo"] > 270000.0