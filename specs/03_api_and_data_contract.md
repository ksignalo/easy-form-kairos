# Candidate Intake Automation - API and Data Contract

## 1. Source References
Raw observed traffic and payload notes:
- specs/raw/auth.md
- specs/raw/add_canddiate.md

## 2. Authentication Contract

### Endpoint
- Method: POST
- URL: https://api.jewelleryhiring.com/admin/login

### Request Body
- email: string
- password: string

### Success Output Requirement
- System must extract and store access token from login response/session object.
- Token must be supplied as Authorization header for protected API calls.

### Security Requirement
- Credentials must not be hardcoded in tracked files.
- Use environment secrets for:
  - ADMIN_EMAIL
  - ADMIN_PASSWORD
- If credentials were exposed during capture/testing, rotate immediately.

## 3. Candidate Create Contract

### Endpoint
- Method: POST
- URL: https://api.jewelleryhiring.com/admin/addEditCandidate
- Content-Type: multipart/form-data

### Observed Form Fields
- candidateId: undefined for create mode
- name: string
- phoneNumber: string
- email: string
- gender: number/string enum (observed: 1)
- dob: string — 4-digit birth year ONLY (e.g. "1995"). Full dates cause API cast failure. Mapper normalizes any AI-returned date to year only.
- tag: number/string enum (observed: 1)
- currentAddress: string
- totalExperience: number/string
- jewelleryExperience: number/string
- expectedSalary: number/string
- currentOrganisation: string
- currentDesignation: string
- preferredLocation: string
- currentInhandSalary: number/string
- file: optional resume binary (DOC/DOCX/PDF)

## 4. Internal-to-API Field Mapping
Internal canonical JSON keys should map 1:1 to multipart field names listed above.

Rules:
- Preserve field names exactly as API expects.
- candidateId fixed to undefined for create.
- Attach file only in upload mode.
- Omit or send empty string for optional missing values based on endpoint behavior discovered during integration testing.

## 5. Validation Contract Before Submission
Hard validation:
- name present
- phoneNumber present and normalized
- email present and syntactically valid

Soft validation:
- Numeric coercion for experience and salary fields
- enum normalization for gender/tag where mapping dictionary is available
- unknown values retained as raw string when safe

## 6. Fallback Orchestrator Contract
Execution pipeline is 2-stage:
1. Configured AI extractor (selected at startup via `AI_PROVIDER` env var: `gemini` | `grok` | `ollama`)
2. Regex extractor (always-on deterministic fallback)

Only one AI provider runs per request. No cascading between AI providers.

Each stage must return either:
- VALID: schema-compliant canonical JSON
- INVALID: list of schema/format errors
- ERROR: timeout/rate-limit/provider failure

Transition rule:
- Proceed to regex stage on INVALID or ERROR from AI provider.
- Stop on first VALID output.

## 7. Cost and Quota Control Contract
- Daily baseline target: >= 10 candidates/day.
- Token budget policy:
  - Use compact prompts and strict output format.
  - Minimize retries per provider.
  - Cache static prompt templates.
- Rate-limit policy:
  - On quota/auth error from configured AI provider -> fallback to Regex.

## 8. Suggested Config Surface
Environment/config keys:
- ADMIN_EMAIL
- ADMIN_PASSWORD
- API_BASE_URL
- GEMINI_API_KEY
- GROK_API_KEY
- OLLAMA_BASE_URL
- OLLAMA_MODEL
- AI_PROVIDER
- AI_TIMEOUT_MS
- MAX_RETRIES_AUTH
- MAX_RETRIES_SUBMIT
- DAILY_QUOTA_GUARD_ENABLED

## 9. Test Scenarios (Contract-Level)
1. Valid paste text -> configured AI provider valid -> successful submission.
2. Valid upload DOCX -> configured AI provider invalid -> Regex valid -> successful submission.
3. Valid upload PDF (text) -> AI provider fails -> Regex partial -> blocked for missing required fields.
4. Scanned PDF upload -> rejected before parser call.
5. Auth token expired -> re-auth -> submission retry succeeds.
6. API validation error -> clear field-level error surfaced.
7. Provider error/rate-limit -> regex fallback executes.
