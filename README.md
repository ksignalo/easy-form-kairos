# Candidate Intake Automation

Automates adding candidates to the jewellery hiring portal — no manual copy-paste from resumes.

## How it works

1. Provide candidate details via **paste** or **file upload** (PDF / DOC / DOCX).
2. The system extracts structured data using a 2-stage pipeline:
   - **AI extractor** — one of Gemini, Grok, or Ollama (configured via `AI_PROVIDER`)
   - **Regex fallback** — deterministic parser, always runs if AI fails or is unconfigured
3. All extracted fields are shown in an **editable review form** before any API call.
4. After user confirms (with edits if needed), a multipart POST submits the candidate.

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd easy-form-kairos
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Description | Default |
|---|---|---|
| `ADMIN_EMAIL` | Portal admin login email | — |
| `ADMIN_PASSWORD` | Portal admin password | — |
| `API_BASE_URL` | Base URL of the portal API | — |
| `AI_PROVIDER` | Which AI to use: `gemini` \| `grok` \| `ollama` | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `GROK_API_KEY` | xAI Grok API key | — |
| `OLLAMA_BASE_URL` | Ollama server URL (local) | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Ollama model to use | `qwen2.5:3b-instruct` |
| `AI_TIMEOUT_MS` | Per-provider timeout in ms | `20000` |
| `MAX_RETRIES_AUTH` | Auth retry attempts | `1` |
| `MAX_RETRIES_SUBMIT` | Submit retry attempts | `2` |

> **Never commit `.env`** — it is listed in `.gitignore`.

### 3. Run

```bash
python main.py
```

Open `http://127.0.0.1:8000` in your browser.

## AI Provider selection

Only one AI provider runs per candidate. Switch by changing `AI_PROVIDER` in `.env`:

- `gemini` — Google Gemini (free tier: 15 req/min). Recommended for cloud deployments.
- `grok` — xAI Grok. Requires a paid API key.
- `ollama` — Local inference via Ollama. No API key needed; requires Ollama running locally.

If the configured provider fails or times out, the regex parser runs as fallback.

## Project structure

```
src/
  config.py           — environment variable loader
  logger.py           — structured per-run logger with requestId
  auth.py             — login, token cache, auto re-auth on expiry
  schema.py           — CandidateData dataclass, validation, normalization
  input_handler.py    — paste and file upload text extraction
  mapper.py           — canonical schema → API multipart fields
  submitter.py        — POST with retry/backoff
  extractors/
    gemini.py         — Gemini extractor
    grok.py           — Grok extractor
    ollama.py         — Ollama extractor (local)
    regex_parser.py   — deterministic regex fallback
    orchestrator.py   — 2-stage pipeline: AI → regex
web_app.py            — Flask app (/extract + /confirm endpoints)
templates/index.html  — 3-state web UI (input → review → result)
static/style.css      — UI styles
main.py               — server entry point
specs/                — functional and API specs
tests/                — 39 unit tests (all pass without network)
```

## Running tests

```bash
python -m pytest tests/ -v
```

All 39 tests pass without network access — AI providers are mocked.

## Limitations

- **No OCR support** — scanned PDFs are rejected with a clear message.
- AI extraction quality depends on resume text clarity.
- Ollama is for local use only; not suitable for cloud deployment (model size ~2 GB).


## Setup

### 1. Clone and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

| Variable | Description |
|---|---|
| `ADMIN_EMAIL` | Admin login email |
| `ADMIN_PASSWORD` | Admin login password |
| `API_BASE_URL` | Base URL of the portal API |
| `GEMINI_API_KEY` | Google Gemini API key (free tier supported) |
| `GROK_API_KEY` | xAI Grok API key |
| `AI_TIMEOUT_MS` | Per-provider timeout in ms (default: 20000) |
| `MAX_RETRIES_AUTH` | Auth retry attempts (default: 1) |
| `MAX_RETRIES_SUBMIT` | Submit retry attempts (default: 2) |

> **Never commit `.env` to source control.** It is listed in `.gitignore`.

## Usage

### Paste mode — type or paste candidate details interactively

```bash
python main.py paste
```

Paste the full candidate text, then press **Enter twice** to submit.

### Upload mode — provide a resume file

```bash
python main.py upload path/to/resume.pdf
python main.py upload path/to/cv.docx
```

Supported formats: `.pdf` (text-based), `.doc`, `.docx`. Scanned PDFs are not supported.

## Project structure

```
src/
  config.py           — environment variable loader
  logger.py           — structured per-run logger with requestId
  auth.py             — login, token cache, auto re-auth on expiry
  schema.py           — CandidateData dataclass, validation, normalization
  input_handler.py    — paste and file upload text extraction
  mapper.py           — canonical schema → API multipart fields
  submitter.py        — POST with retry/backoff
  extractors/
    gemini.py         — Gemini extractor
    grok.py           — Grok extractor
    regex_parser.py   — deterministic regex fallback
    orchestrator.py   — 3-stage fallback chain
main.py               — CLI entry point
tests/                — 31 unit tests
```

## Running tests

```bash
python -m pytest tests/ -v
```

All 31 tests should pass without network access (AI providers are mocked).

## Constraints and limitations

- **No OCR support** — scanned PDFs are rejected with a clear message.
- **AI extraction quality** depends on resume text clarity and structure.
- Designed for free-tier AI usage (~10 candidates/day baseline).
- On 429 rate-limits, the system automatically falls through to the next provider.
