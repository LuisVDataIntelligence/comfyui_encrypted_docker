Third-Party Notices

This project includes or uses the following third‑party components. Their licenses are included below or linked.

- ComfyUI — GPL‑3.0 — https://github.com/comfyanonymous/ComfyUI — see LICENSES/COMFYUI.GPL-3.0.txt
- PyNaCl — Apache‑2.0 — https://github.com/pyca/pynacl — see LICENSES/Apache-2.0.txt
- requests — Apache‑2.0 — https://github.com/psf/requests — see LICENSES/Apache-2.0.txt
- websocket-client — Apache‑2.0 — https://github.com/websocket-client/websocket-client — see LICENSES/Apache-2.0.txt
- FastAPI — MIT — https://github.com/tiangolo/fastapi — see LICENSES/MIT.txt
- Uvicorn — BSD‑3‑Clause — https://github.com/encode/uvicorn — see LICENSES/BSD-3-Clause.txt
- runpod (Python SDK) — MIT — https://github.com/runpod/runpod-python — see LICENSES/MIT.txt

Notes on GPL compliance (ComfyUI):
- This repository does not embed ComfyUI source; the Docker image clones ComfyUI during build, and the container includes the ComfyUI LICENSE at /opt/ComfyUI/LICENSE. Upstream source is available at the URL above.
- ComfyUI runs as a separate process; our wrapper code is licensed under MIT. If you distribute a modified ComfyUI, you must follow GPL‑3.0 terms for those modifications.

