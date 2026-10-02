from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from linter import lint, summarize
from linter.examples import bad_example, good_example

import os
import threading
import time
import urllib.request


BASE = Path(__file__).parent
app = FastAPI(title="Flyo payload linter", docs_url="/docs")


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")

    

def _keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL")  # Render sets this automatically
    if not url:
        return  # not on Render (e.g. local dev), do nothing
    while True:
        time.sleep(14 * 60)
        try:
            urllib.request.urlopen(url, timeout=10)
        except Exception:
            pass


threading.Thread(target=_keep_alive, daemon=True).start()

@app.post("/lint")
async def lint_payload(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Body is not valid JSON."})
    issues = lint(payload)
    return {**summarize(issues), "issues": [i.to_dict() for i in issues]}


@app.get("/examples/{name}")
def example(name: str):
    if name == "good":
        return good_example()
    if name == "bad":
        return bad_example()
    raise HTTPException(status_code=404, detail="Unknown example. Use good or bad.")
