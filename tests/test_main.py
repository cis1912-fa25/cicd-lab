from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_echo():
    response = client.get("/echo")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}

def test_echo_name():
    response = client.get("/echo/DevOps")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, DevOps!"}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
