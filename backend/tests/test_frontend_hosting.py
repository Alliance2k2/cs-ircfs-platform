"""Hosting the React dashboard at /app/: built files, client-side routes, and safety."""
import pytest

import app.main as main


@pytest.fixture()
def built(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "secret.txt").write_text("do not serve", encoding="utf-8")
    monkeypatch.setattr(main, "frontend_dir", tmp_path)
    return tmp_path


def test_app_routes_fall_back_to_index(client, built):
    for path in ("/app/", "/app/schemes/2", "/app/anything?days=30"):
        response = client.get(path)
        assert response.status_code == 200 and "id=root" in response.text
        assert response.headers["Cache-Control"] == "no-cache"


def test_hashed_assets_are_cached_for_a_year(client, built):
    response = client.get("/app/assets/index-abc123.js")
    assert response.status_code == 200
    assert "immutable" in response.headers["Cache-Control"]


def test_paths_cannot_escape_the_build_folder(client, built):
    response = client.get("/app/..%2Fsecret.txt")
    assert "do not serve" not in response.text


def test_bare_app_path_redirects(client, built):
    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 308 and response.headers["location"] == "/app/"


def test_missing_build_explains_itself(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "frontend_dir", tmp_path / "missing")
    response = client.get("/app/")
    assert response.status_code == 503 and "npm run build" in response.text
