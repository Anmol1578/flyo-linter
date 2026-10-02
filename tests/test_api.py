from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_index_page_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Check booking" in response.text


def test_lint_endpoint_valid_example():
    payload = client.get("/examples/good").json()
    body = client.post("/lint", json=payload).json()
    assert body["ok"] is True
    assert body["counts"]["error"] == 0


def test_lint_endpoint_bad_example():
    payload = client.get("/examples/bad").json()
    body = client.post("/lint", json=payload).json()
    assert body["ok"] is False
    assert body["issues"][0]["level"] == "error"


def test_lint_endpoint_rejects_invalid_json():
    response = client.post("/lint", content="{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400


def test_unknown_example_is_404():
    assert client.get("/examples/nope").status_code == 404
