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
def api_app(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    monkeypatch.setenv("COMFYUI_MODEL_DIR", str(models_dir))

    # Reload modules so MODEL_DIR picks up the temporary directory
    import phserver.worker_core as worker_core
    import phserver.api_server as api_server

    worker_core = importlib.reload(worker_core)
    api_server = importlib.reload(api_server)

    monkeypatch.setattr(api_server, "init_comfy", lambda: None)

    # Ensure any attempt to perform a network download fails the test
    def _unexpected_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called for invalid paths")

    fake_requests = types.SimpleNamespace(get=_unexpected_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    return api_server.app


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
