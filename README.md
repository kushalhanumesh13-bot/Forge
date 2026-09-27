# Forge
An AI-powered engineering workspace for understanding, modifying, testing, and validating software projects.

## Run the workspace

From the repository root, run `\.venv\Scripts\python.exe -m uvicorn app.main:app --reload` and open `http://127.0.0.1:8000/`. The workspace exposes repository analysis, file inspection and saving, deterministic task planning, and a restricted `pytest` runner through the FastAPI app.
