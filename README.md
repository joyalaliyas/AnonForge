# AnonForge

AnonForge is a privacy-preserving AI pipeline that detects sensitive entities in text and transforms them into synthetic-safe alternatives while preserving context and meaning.

It is designed for teams that need to use LLM workflows on sensitive records without exposing real personal or organizational data.

## Problem Statement

Organizations in HR, healthcare, legal services, and government hold high-value but highly sensitive data such as employee records, patient details, case notes, and therapy logs. This data is private by nature and tightly governed by compliance requirements.

At the same time, these organizations need AI to improve productivity, extract insights, and accelerate innovation. The core conflict is that sending raw confidential data to external AI services introduces major risk:

1. Privacy breaches and data leakage.
2. Regulatory non-compliance risk under frameworks such as GDPR and HIPAA.
3. Legal, operational, and reputational exposure.

This creates a harmful trade-off:

1. Avoid AI and lose competitive advantage.
2. Use AI on unprotected data and accept privacy/compliance risk.

A practical solution must preserve both privacy and utility: it should remove sensitive identifiers while retaining the contextual meaning needed for reliable downstream AI analysis.

## Solution Statement

### Core Concept: The Privacy-Preserving AI Data Forge

AnonForge is a two-stage AI agent system that forges sensitive organizational data into privacy-safe synthetic intelligence. It resolves the privacy-versus-utility conflict by replacing identifiable details while preserving analytical meaning and context.

### Stage 1: The Detector - Identification and Context Mapping

Input:

- Raw sensitive text, for example: Rahul from Kochi works at Infosys and feels stressed.

Functions:

1. Detect and classify sensitive entities such as people, locations, organizations, dates, and IDs.
2. Map the contextual blueprint of the text, for example employee stress scenario or clinical consultation.

Output:

- Structured entity inventory.
- Context label.
- Placeholder-oriented representation suitable for controlled transformation.

### Stage 2: The Forger - Context-Aware Synthetic Generation

Input:

- The structured blueprint from Stage 1.

Functions:

1. Generate synthetic replacements for each sensitive entity.
2. Ensure replacements are anonymous, context-consistent, and analytically faithful.

Output:

- Fully transformed, privacy-safe text and dataset rows ready for external AI use.

### What AnonForge Delivers

1. Safety from risk: sensitive identifiers are transformed before external AI interaction.
2. AI enablement: teams can apply LLM workflows on confidential domains without exposing raw PII.
3. Compliance by design: privacy controls are embedded directly in the data-processing path.
4. No forced compromise: organizations can pursue innovation without abandoning security obligations.

### Final Outcome

Organizations submit confidential raw data to AnonForge and receive context-rich synthetic intelligence that can be safely used for analytics, automation, and AI application development with significantly reduced privacy and compliance exposure.

## What the project does

1. Detects sensitive entities such as person names, locations, companies, emails, phones, and IDs.
2. Classifies scenario context (for example employee stress/support/health/general).
3. Generates synthetic replacements using AI models.
4. Produces transformed text for single input and CSV batch processing.
5. Provides a web interface and API endpoints.

## Architecture

### Agent 1: Detection + Understanding

- Uses AI to extract entities in strict JSON format.
- Resolves entity spans back to source text.
- Classifies context label using OpenAI.
- Returns highlighted text with labels.

### Agent 2: Safe Generation

- Uses AI to generate synthetic replacements for each detected entity.
- Applies replacements to produce transformed text.
- Runs output validation checks to reduce leakage risk.

### Pipeline Orchestrator

- Executes Agent 1 then Agent 2 in sequence.
- Returns unified output payload.

### API + UI

- FastAPI backend serving API endpoints and static web app.
- Browser UI for single text processing and CSV conversion.

## Project structure

```text
src/
  agent1/
    detector.py
    context_classifier.py
    highlighter.py
  agent2/
    generator.py
    validators.py
  pipeline/
    orchestrator.py
  contracts/
    schemas.py
  api/
    main.py
    static/
      index.html
      app.js
      styles.css
tests/
```

## Requirements

- Python 3.11+ (works with newer versions too)
- AI API key

## Local setup

1. Create virtual environment.
2. Install dependencies.
3. Configure environment variables.
4. Start the API.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```


### Single text flow

1. Enter text.
2. Click Run Pipeline.
3. Review original text, highlighted entities, synthetic output, and entity list.

### CSV flow

1. Upload CSV file.
2. Set `text_column` or use `auto`.
3. Click Convert CSV.
4. Download transformed CSV.

CSV output includes:

- Original columns
- Per-column synthetic fields (`<column>_synthetic`)
- `synthetic_text`
- `context`
- `status`
- `error`

## API reference

### GET /health

Health check endpoint.

### POST /process

Input:

```json
{
  "text": "Rahul from Kochi works at Infosys and feels stressed.",
  "locale": "en-IN"
}
```

Output (shape):

```json
{
  "original_text": "...",
  "locale": "en-IN",
  "agent1": {
    "entities": [],
    "context": "employee_stress_situation",
    "highlighted_text": "..."
  },
  "agent2": {
    "replacements": [],
    "transformed_text": "...",
    "used_fallback": false
  }
}
```

### POST /process-csv

Multipart form fields:

- `file`: CSV file
- `text_column`: explicit column name or `auto`
- `locale`: locale string

Returns downloadable CSV.

## Error handling

- LLM processing failures are returned as HTTP 503 with detailed `detail` messages.
- CSV rows are marked with row-level `status` and `error` to make failures auditable.

## Testing

Run test suite:

```bash
pytest -q
```

The tests mock  paths so CI remains deterministic and does not require live API calls.

