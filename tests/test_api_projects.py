from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_create_project():
    response = client.post(
        "/projects",
        json={"idea": "test project"},
    )

    assert response.status_code == 200
    assert "project_id" in response.json()


def test_project_status_not_found():
    response = client.get("/projects/proj_does_not_exist/status")

    assert response.status_code == 404
