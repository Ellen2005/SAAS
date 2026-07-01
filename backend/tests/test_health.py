class TestHealthEndpoints:
    def test_ping(self, client):
        response = client.get("/api/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "timestamp" in data

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Enterprise Analytics Platform" in data["message"]
