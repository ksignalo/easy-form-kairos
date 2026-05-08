# Candidate Intake Automation - Execution Backlog

## 1. Epic Breakdown

### Epic A: Authentication and Session Management
User Story:
As a system, I need to authenticate with admin credentials so protected APIs can be called.

Tasks:
- Implement auth API client for login endpoint.
- Parse and store access token securely in runtime memory/cache.
- Add token expiry handling and one-time re-auth retry.
- Add auth error classification (invalid credentials, network, server).

Acceptance:
- Protected call succeeds after login.
- Expired/invalid token triggers re-auth once.

### Epic B: Input Intake
User Story:
As a recruiter, I want to provide candidate details either by paste or file upload.

Tasks:
- Build paste-mode input handler.
- Build upload-mode validator for PDF/DOC/DOCX.
- Add size guard and type validation messages.
- Build text extraction adapters:
  - DOC/DOCX extractor
  - PDF text-layer extractor
- Reject scanned/non-extractable PDF with explicit non-OCR message.

Acceptance:
- Both modes produce normalized raw text.
- Scanned PDF is blocked with clear guidance.

### Epic C: Structured Extraction with Fallback
User Story:
As a system, I need reliable extraction even if one AI provider fails.

Tasks:
- Define canonical candidate schema.
- Implement Gemini extractor with strict JSON contract.
- Implement Grok extractor with same schema contract.
- Implement Ollama extractor for local/offline use.
- Implement regex fallback parser for key fields.
- Implement 2-stage orchestrator: [AI_PROVIDER] -> Regex.
- Support `AI_PROVIDER` env var to select exactly one AI extractor.
- Add schema validation and transition rules.

Acceptance:
- Selected AI provider runs; regex takes over on failure.
- Switching providers requires only .env change.
- No two AI providers run for the same candidate.

### Epic D: Human Review, Mapping, Validation, and API Submission
User Story:
As a recruiter, I want to review and edit extracted candidate data before it is sent to the API.

Tasks:
- Build mapping from canonical JSON to addEditCandidate form fields.
- Enforce required fields: name, phoneNumber, email.
- Add numeric coercion for salary/experience fields.
- Attach file in multipart only for upload mode.
- Implement submit retry/backoff for transient failures.
- Split intake flow into two stages:
  - `/extract`: parse input, run extraction pipeline, return review form pre-filled with extracted data.
  - `/confirm`: accept user-edited fields, validate, POST to API.
- Show all 15 candidate fields in editable form with required fields marked.
- Validate on confirm; re-display review form with errors if invalid.
- Clean up temp resume file after confirm (success or failure).
- Security: validate temp file path is inside system temp dir before use.

Acceptance:
- Candidate create API receives valid multipart payload only after user confirmation.
- Required-field failures are surfaced in review form, not silently.
- User can edit any extracted field before submitting.
- Uploaded resume temp file is deleted after confirm.
- No API call is made if user clicks "Start Over".

### Epic E: Observability and Cost Governance
User Story:
As an operator, I want visibility into parser usage and failures to control quality and cost.

Tasks:
- Add per-run requestId and structured logs.
- Log parser source and fallback sequence.
- Log API status and safe error details.
- Add rate-limit handling and provider fallback.
- Track daily candidate volume and fallback rates.

Acceptance:
- Every run emits traceable logs.
- 429 and provider errors trigger expected fallback path.

## 2. Priority Queue
1. Auth + submit base (critical path)
2. Input intake + file extraction
3. Fallback extraction chain
4. Validation + mapping polish
5. Observability + quota governance

## 3. Test Backlog
- Contract test: login and token extraction.
- Contract test: multipart payload field names.
- Unit tests: schema validator.
- Unit tests: phone/email/number normalization.
- Integration tests: fallback sequence.
- Negative tests: scanned PDF, missing required fields, provider timeout.

## 4. Release Checklist
- Secrets configured in deployment environment.
- Sample payloads validated against live/staging API.
- Parser prompt templates versioned.
- Known limitations documented:
  - No OCR support
  - Quality depends on resume text clarity
