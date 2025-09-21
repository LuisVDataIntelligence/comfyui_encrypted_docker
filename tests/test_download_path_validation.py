import importlib
import pathlib
import sys
import types

import pytest
from fastapi.testclient import TestClient


ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def api_app_factory(tmp_path, monkeypatch):
    def _create(requests_get=None):
        models_dir = tmp_path / "models"
        monkeypatch.setenv("COMFYUI_MODEL_DIR", str(models_dir))

        # Reload modules so MODEL_DIR picks up the temporary directory
        import phserver.worker_core as worker_core
        import phserver.api_server as api_server

        worker_core = importlib.reload(worker_core)
        api_server = importlib.reload(api_server)

        monkeypatch.setattr(api_server, "init_comfy", lambda: None)

        if requests_get is None:
            # Ensure any attempt to perform a network download fails the test
            def _unexpected_get(*args, **kwargs):
                raise AssertionError("requests.get should not be called for invalid paths")

            requests_get = _unexpected_get

        fake_requests = types.SimpleNamespace(get=requests_get)
        monkeypatch.setitem(sys.modules, "requests", fake_requests)

        return api_server.app

    return _create


@pytest.fixture
def api_app(api_app_factory):
    return api_app_factory()


def test_download_rejects_path_traversal(api_app):
    with TestClient(api_app) as client:
        resp = client.post(
            "/download",
            json={
                "url": "http://example.com/model.ckpt",
                "filename": "../outside.bin",
            },
        )

    assert resp.status_code == 400
    assert "Invalid destination path" in resp.text


def test_download_uses_content_disposition_filename(api_app_factory, tmp_path):
    chunk = b"payload"

    class DummyResponse:
        headers = {"Content-Disposition": 'attachment; filename="from-header.safetensors"'}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1):
            yield chunk

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_get(*args, **kwargs):
        return DummyResponse()

    app = api_app_factory(requests_get=_fake_get)

    with TestClient(app) as client:
        resp = client.post(
            "/download",
            json={
                "url": "http://example.com/",
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"

    expected_path = tmp_path / "models" / "from-header.safetensors"
    assert payload["path"] == str(expected_path)
    assert expected_path.exists()
    assert expected_path.read_bytes() == chunk
