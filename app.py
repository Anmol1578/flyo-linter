from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from linter import lint, summarize
from linter.examples import bad_example, good_example

BASE = Path(__file__).parent
app = FastAPI(title="Flyo payload linter", docs_url="/docs")


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


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
