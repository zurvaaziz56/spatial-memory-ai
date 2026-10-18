# Antigravity Autonomous Mission Spec

Paste the prompt below directly into **Google Antigravity (Mission Control / Agent Manager)** or **Cursor Agent Mode** after opening this folder:

---

```text
Mission: Test, verify, and deploy this `spatial-memory-ai` FastAPI + Gemini 2.5 Flash application to Google Cloud Run and push to a public GitHub repository for the Google Cloud AI Builder Cup.

Execute the following steps autonomously:
1. Inspect the workspace files (`main.py`, `static/index.html`, `requirements.txt`, `Dockerfile`, `deploy.sh`).
2. Create a local Python virtual environment, install `requirements.txt`, and start `uvicorn main:app --port 8080`.
3. Use the embedded browser to open `http://localhost:8080`, verify that all 3 instant presets render their spatial pins on the canvas, and verify that switching between "1. Spatial Room Palace", "2. Socratic Recall Sprint", and "3. Live A/B Efficacy Lab" works with zero console errors.
4. Initialize a clean Git repository (`git init`), create a `.gitignore` (excluding `.env`, `__pycache__`, `.venv`), commit all files, and push to a new public GitHub repository named `spatial-memory-ai` using the `gh` CLI.
5. Deploy the service to Google Cloud Run using `gcloud run deploy spatial-memory-ai --source . --region us-central1 --allow-unauthenticated --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY"` and return the live `.run.app` URL.
```
