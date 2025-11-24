# tests/test_flask_routes.py
def test_root_redirect(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_healthcheck(client):
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert "✅ OK" in response.get_data(as_text=True)

def test_uptime_ping(client):
    response = client.get("/ping")
    assert response.status_code == 200
    assert "✅ Ping OK" in response.get_data(as_text=True)

def test_404(client):
    response = client.get("/tidakadare")
    assert response.status_code == 404
    assert "❌ Halaman tidak ditemukan" in response.get_data(as_text=True)
