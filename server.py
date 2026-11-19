"""API для React-фронтенду.

Запуск:  .venv\\Scripts\\python.exe -m uvicorn server:app --port 8000
Слухає лише 127.0.0.1: дані завантажених файлів нікуди не передаються і не зберігаються.
"""
import json
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

import engine
import report

ROOT = Path(__file__).parent
DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="Access Review")


@app.post("/api/analyze")
def analyze(
    files: list[UploadFile] = File(...),
    overrides: str = Form("{}"),
    review_date: str | None = Form(None),
    inactive_days: int | None = Form(None),
    domain: str | None = Form(None),
    policy: str | None = Form(None),
):
    try:
        ov = json.loads(overrides or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "Некоректні налаштування колонок.")
    try:
        data = [(f.filename or f"file{i}", f.file.read()) for i, f in enumerate(files)]
        return engine.run(data, overrides=ov, review_date=review_date or None,
                          inactive_days=inactive_days, domain=domain, policy_text=policy)
    except engine.AnalysisError as e:
        raise HTTPException(400, str(e))


@app.post("/api/export")
def export(payload: dict = Body(...)):
    """Excel-звіт зі знахідок. Приймає {rows, summary, params}, повертає .xlsx."""
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise HTTPException(400, "Немає даних для звіту.")
    data = report.build_xlsx(rows, payload.get("summary"), payload.get("params"))
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="access_review_report.xlsx"'},
    )


@app.get("/api/policy")
def policy():
    return engine.load_policy()


@app.get("/api/policy/text")
def policy_text():
    """Стандартні правила (policy.json) у текстовому форматі — як заготовка для редагування."""
    return {"text": engine.policy_to_text(engine.load_policy())}


# приклади файлів для кнопки «Спробувати на прикладі»
app.mount("/api/sample", StaticFiles(directory=ROOT / "sample_data"), name="sample")

# зібраний фронтенд (після `npm run build`) віддається цим же сервером
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    # index.html не кешуємо: після перезбирання інтерфейсу браузер одразу бере нову версію
    NO_CACHE = {"Cache-Control": "no-cache"}

    @app.get("/{path:path}")
    def spa(path: str):
        target = (DIST / path).resolve()
        if path and target.is_file() and DIST.resolve() in target.parents:
            return FileResponse(target, headers=NO_CACHE)
        return FileResponse(DIST / "index.html", headers=NO_CACHE)
