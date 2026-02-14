from fastapi.testclient import TestClient

from vulture.api.app import create_app


def test_common_icon_routes_never_404() -> None:
    app = create_app()
    client = TestClient(app)

    for path in ("/favicon.ico", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):
        response = client.get(path)
        assert response.status_code in {200, 204}


def test_dashboard_includes_icon_links() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert 'rel="icon"' in response.text
    assert 'href="/favicon.ico"' in response.text
    assert 'rel="apple-touch-icon"' in response.text
