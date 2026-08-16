from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_allows_local_frontend_origin():
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_models():
    with TestClient(app) as client:
        response = client.get("/api/models")
    assert response.status_code == 200
    assert "small" in [model["name"] for model in response.json()]


def test_rejects_unsupported_language():
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            files={"audio": ("voice.wav", b"not audio", "audio/wav")},
            data={"language": "zz"},
        )
    assert response.status_code == 422


def test_accepts_persian_display_name():
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            files={"audio": ("voice.wav", b"not audio", "audio/wav")},
            data={
                "model": "small",
                "language": "Persian",
                "interval": "40",
                "smoothing": "true",
            },
        )
    assert response.status_code == 202


def test_backend_websocket_pushes_health_and_models():
    with TestClient(app) as client:
        with client.websocket_connect("/api/ws") as socket:
            health_message = socket.receive_json()
            models_message = socket.receive_json()
    assert health_message == {
        "type": "health",
        "health": {"status": "ok", "version": "1.0.0"},
    }
    assert models_message["type"] == "models"
    assert "small" in [model["name"] for model in models_message["models"]]


def test_backend_websocket_accepts_analyze_command():
    with TestClient(app) as client:
        with client.websocket_connect("/api/ws") as socket:
            socket.receive_json()
            socket.receive_json()
            socket.send_json(
                {
                    "type": "analyze",
                    "file_name": "voice.wav",
                    "model": "small",
                    "language": "English",
                    "interval": 40,
                    "device": "CPU",
                }
            )
            message = socket.receive_json()
    assert message == {"type": "upload_ready"}


def test_backend_websocket_accepts_binary_upload_after_command():
    with TestClient(app) as client:
        with client.websocket_connect("/api/ws") as socket:
            socket.receive_json()
            socket.receive_json()
            socket.send_json(
                {
                    "type": "analyze",
                    "file_name": "voice.wav",
                    "model": "small",
                    "language": "English",
                    "interval": 40,
                    "device": "CPU",
                }
            )
            assert socket.receive_json() == {"type": "upload_ready"}
            socket.send_bytes(b"not valid audio")
            accepted = socket.receive_json()
    assert accepted["type"] == "accepted"
    assert accepted["job"]["status"] in {"pending", "processing"}
