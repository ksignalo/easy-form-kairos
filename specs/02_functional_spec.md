# Candidate Intake Automation - Functional Specification

## 1. End-to-End Workflow

### Step 1: Authentication
- System sends POST login request to auth endpoint.
- On success, system captures access token.
- Token is cached with expiry awareness.
- If token is invalid/expired, re-authenticate and retry once.

### Step 2: Input Acquisition
Two supported paths:

1. Direct Paste Mode
- User pastes full candidate information text in one input.
- System trims and sanitizes text.
- System forwards text to extraction pipeline.

2. Resume Upload Mode
- User uploads PDF/DOC/DOCX.
- System validates file type and size.
- System extracts text:
  - PDF: text-layer extraction only.
  - DOC/DOCX: standard text extraction.
- If PDF has no extractable text (scanned), reject with explicit error:
  "Scanned PDF is not supported. Please upload a text-based PDF/DOC/DOCX or paste details manually."

### Step 3: Data Structuring and Fallback Orchestration
- System uses a 2-stage extraction pipeline:
  1. Configured AI parser (one of: Gemini, Grok, Ollama — set via `AI_PROVIDER` env var)
  2. Regex/non-AI deterministic parser (always active as final fallback)
- Active AI provider is selected at startup from environment config, not at runtime.
- Only one AI provider runs per candidate intake; no cascading between AI providers.
- Each stage must output canonical candidate JSON format.
- If AI parser output fails schema validation or errors, regex fallback runs.
- Stop pipeline immediately when first valid structured output is obtained.

### Step 3.5: Human Review and Confirmation (NEW)
- After extraction, system presents all extracted fields to the user in an editable form.
- All 15 candidate fields are shown with pre-filled extracted values.
- Required fields (name, phoneNumber, email) are visually highlighted.
- User can edit any field before confirming.
- User must explicitly click "Confirm & Submit" to trigger the API call.
- No API submission happens without user confirmation.
- User can click "Start Over" to discard and return to the input form.

### Step 4: Validation and Mapping
- Validate required fields and formats (after user confirms).
- Convert canonical JSON to API field contract.
- Normalize values (phone, email, numeric experience/salary, enums).
- Attach uploaded resume file (if present) to multipart payload.

### Step 5: Candidate Submission
- Submit POST multipart/form-data to add candidate API only after user confirmation.
- Include authorization token in headers.
- Handle responses:
  - Success: return candidate creation confirmation.
  - Validation/server error: return actionable message.

## 2. Canonical Candidate Schema (Internal)
Required:
- name
- phoneNumber
- email

Optional:
- gender
- dob
- tag
- currentAddress
- totalExperience
- jewelleryExperience
- expectedSalary
- currentOrganisation
- currentDesignation
- preferredLocation
- currentInhandSalary

## 3. Business Rules
- candidateId is always undefined/null for create flow.
- Empty optional fields are omitted or sent as empty string based on API contract requirement.
- totalExperience and jewelleryExperience must be numeric (years).
- Salary fields must be numeric.
- Phone number must be digit-normalized before submission.
- Email must pass standard format validation.

## 4. Parser Strategy Requirements

### AI Provider Selection
- Exactly one AI provider is active per deployment, chosen via `AI_PROVIDER` env var.
- Valid values: `gemini`, `grok`, `ollama`. Default: `gemini`.
- Switching providers requires only a config change; no code change needed.

### Gemini
- Available when `AI_PROVIDER=gemini`.
- Prompt must enforce strict JSON output with no prose.
- Timeout and token limits configurable. Requires `GEMINI_API_KEY`.

### Grok
- Available when `AI_PROVIDER=grok`.
- Uses xAI OpenAI-compatible API. Requires `GROK_API_KEY`.
- Same canonical output schema and validation checks.

### Ollama
- Available when `AI_PROVIDER=ollama`.
- Uses local Ollama HTTP API (`/api/generate`). No API key needed.
- Default model: `qwen2.5:3b-instruct` (configurable via `OLLAMA_MODEL`).
- Requires Ollama server running at `OLLAMA_BASE_URL`.

### Regex/Deterministic Parser (Always Active Fallback)
- Triggered when the configured AI provider fails/returns invalid output.
- Uses pattern library for:
  - name
  - email
  - phone
  - years of experience
  - current company/designation (best effort)
- Produces partial output if needed, but must always mark missing required fields.

## 5. Error Handling
- Auth failure: show "Authentication failed. Check credentials or endpoint availability."
- Unsupported file: show allowed formats.
- Scanned PDF: explicit non-OCR message.
- Parsing failure at AI + regex level: show missing fields and ask for manual correction.
- API 4xx: show validation error details.
- API 5xx/network: retry with backoff, then fail with trace id/log reference.

## 6. Logging and Audit
Per candidate run, log:
- requestId
- timestamp
- input mode (paste/upload)
- configured AI provider (gemini/grok/ollama)
- parser actually used for successful extraction
- validation result
- submission status and response code
- safe error details (no secrets)

## 7. Acceptance Criteria
1. User can submit candidate using direct pasted text with no manual per-field form filling.
2. User can submit candidate using supported resume files.
3. Scanned PDF is rejected with explicit reason.
4. Active AI provider is controlled by `AI_PROVIDER` env var. Regex is always the final fallback.
5. After extraction, user is shown all extracted fields in an editable review form before submission.
6. API submission only happens after user clicks "Confirm & Submit".
7. System submits multipart payload compatible with existing endpoint.
8. At least 10 candidates/day can be processed under free-tier strategy.
