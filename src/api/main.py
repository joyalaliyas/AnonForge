from pathlib import Path
import csv
import re
from io import StringIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from src.agent1.context_classifier import LLMProcessingError
from src.contracts.schemas import ProcessRequest, ProcessResponse
from src.pipeline.orchestrator import PrivacyPipeline


app = FastAPI(title="Privacy-Preserving Synthetic Data API", version="0.1.0")
pipeline = PrivacyPipeline()
STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _compose_row_text(row: dict[str, str], fieldnames: list[str]) -> str:
    parts: list[str] = []
    for col in fieldnames:
        value = (row.get(col) or "").strip()
        if not value:
            continue
        if col.lower() in {"id", "uuid"}:
            continue
        parts.append(f"{col}: {value}")
    return " | ".join(parts)


def _apply_replacements(value: str, replacements: list[tuple[str, str]]) -> str:
    updated = value
    # Longer matches first avoids partial replacement collisions.
    ordered = sorted(replacements, key=lambda item: len(item[0]), reverse=True)
    for original, synthetic in ordered:
        if not original:
            continue
        pattern = re.compile(re.escape(original), flags=re.IGNORECASE)
        updated = pattern.sub(synthetic, updated)
    return updated


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/process", response_model=ProcessResponse)
def process(payload: ProcessRequest) -> ProcessResponse:
    try:
        return pipeline.run(payload.text, payload.locale)
    except LLMProcessingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/process-csv")
async def process_csv(
    file: UploadFile = File(...),
    text_column: str = Form("auto"),
    locale: str = Form("en-IN"),
) -> Response:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a valid .csv file.")

    raw_bytes = await file.read()
    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or missing a header row.")

    fieldnames = [name.strip() for name in reader.fieldnames if name]
    by_lower = {name.lower(): name for name in fieldnames}
    requested = (text_column or "auto").strip()
    requested_lower = requested.lower()

    resolved_text_column: str | None = None
    if requested_lower and requested_lower != "auto":
        resolved_text_column = by_lower.get(requested_lower)
        if not resolved_text_column:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Text column '{text_column}' not found. "
                    f"Available columns: {fieldnames}. "
                    "Set Text Column to 'auto' to infer a column."
                ),
            )
    else:
        preferred = [
            "text",
            "message",
            "issue",
            "content",
            "description",
            "note",
            "prompt",
            "comments",
        ]
        for candidate in preferred:
            if candidate in by_lower:
                resolved_text_column = by_lower[candidate]
                break

    rows_out: list[dict[str, str]] = []
    for idx, row in enumerate(reader, start=1):
        if requested_lower == "auto":
            # For structured CSV rows, process the full row text to catch PII spread across columns.
            original_text = _compose_row_text(row, fieldnames)
        elif resolved_text_column:
            original_text = (row.get(resolved_text_column) or "").strip()
        else:
            original_text = _compose_row_text(row, fieldnames)

        if not original_text:
            row["synthetic_text"] = ""
            row["context"] = ""
            row["status"] = "skipped_empty_text"
            row["error"] = ""
            rows_out.append(row)
            continue

        try:
            result = pipeline.run(original_text, locale)
            row["synthetic_text"] = result.agent2.transformed_text
            row["context"] = result.agent1.context
            row["status"] = "ok"
            row["error"] = ""

            replacements = [(item.original, item.synthetic) for item in result.agent2.replacements]
            for col in fieldnames:
                original_value = str(row.get(col, ""))
                row[f"{col}_synthetic"] = _apply_replacements(original_value, replacements)
        except LLMProcessingError as exc:
            row["synthetic_text"] = ""
            row["context"] = ""
            row["status"] = "error"
            row["error"] = str(exc)
            for col in fieldnames:
                row[f"{col}_synthetic"] = ""
        except Exception as exc:  # pragma: no cover
            row["synthetic_text"] = ""
            row["context"] = ""
            row["status"] = "error"
            row["error"] = f"Row {idx}: {exc}"
            for col in fieldnames:
                row[f"{col}_synthetic"] = ""
        rows_out.append(row)

    fieldnames = list(reader.fieldnames)
    for col in list(reader.fieldnames):
        synthetic_col = f"{col}_synthetic"
        if synthetic_col not in fieldnames:
            fieldnames.append(synthetic_col)
    for col in ["synthetic_text", "context", "status", "error"]:
        if col not in fieldnames:
            fieldnames.append(col)

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows_out)

    source_name = Path(file.filename).stem
    headers = {"Content-Disposition": f'attachment; filename="{source_name}_synthetic.csv"'}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)
