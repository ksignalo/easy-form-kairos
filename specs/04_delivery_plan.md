# Candidate Intake Automation - Delivery Plan

## 1. Delivery Objective
Convert approved specs into an execution-ready delivery roadmap so implementation can begin with clear sequencing, ownership, and acceptance gates.

## 2. Phase Plan

### Phase 0: Setup and Guardrails (Day 1)
Goals:
- Finalize environment/config strategy.
- Lock API contract assumptions.
- Establish logging and error taxonomy.

Deliverables:
- Environment variable contract implemented in config layer.
- API client stubs for auth and add candidate endpoints.
- Standard response/error envelope defined.

Exit Criteria:
- Team can run auth flow in non-production safely.
- No secrets committed in repository.

### Phase 1: Auth and API Foundation (Day 1-2)
Goals:
- Build login flow with token lifecycle.
- Build multipart submit function for candidate create.

Deliverables:
- Auth service (login, token cache, auto-refresh/retry).
- Candidate submission service with retry/backoff.

Exit Criteria:
- Candidate API call succeeds with manually supplied sample payload.
- Expired token auto-recovers once via re-auth.

### Phase 2: Input Acquisition (Day 2-3)
Goals:
- Support paste mode and upload mode.
- Add text extraction for DOC/DOCX/PDF (text-layer only).

Deliverables:
- Input handler with mode detection.
- File validation (type/size).
- PDF non-OCR check and explicit rejection message.

Exit Criteria:
- Paste input and supported file upload both produce extracted raw text.
- Scanned PDF path is rejected correctly.

### Phase 3: Extraction Engine with Fallback (Day 3-5)
Goals:
- Implement strict fallback chain: Gemini -> Grok -> Regex.
- Add canonical schema validator.

Deliverables:
- Gemini extractor adapter.
- Grok extractor adapter.
- Regex deterministic extractor.
- Orchestrator + parser result contract (VALID/INVALID/ERROR).

Exit Criteria:
- Orchestrator stops on first schema-valid result.
- All failure modes fall through to next parser correctly.

### Phase 4: Mapping, Validation, and Submit Pipeline (Day 5-6)
Goals:
- Map canonical JSON to multipart API fields.
- Enforce required and soft validations before submit.

Deliverables:
- Validation layer.
- Mapping layer.
- End-to-end process function from input to API submission.

Exit Criteria:
- End-to-end creation works for both modes with known test resumes.

### Phase 5: Hardening, Cost Controls, and UAT (Day 6-7)
Goals:
- Stabilize retries/observability.
- Validate free-tier sustainability for 10 candidates/day.

Deliverables:
- Quota/rate-limit strategy and fallback behavior.
- Structured logging and run summary.
- UAT report and known limitations.

Exit Criteria:
- UAT sign-off against acceptance criteria from functional spec.

## 3. Milestones
1. M1: Auth + Submit Base Ready
2. M2: Input Acquisition Ready
3. M3: Fallback Extraction Engine Ready
4. M4: End-to-End Candidate Creation Ready
5. M5: UAT + Production Readiness

## 4. Roles and Ownership (Suggested)
- Backend engineer: API client, auth lifecycle, submit service.
- Parsing engineer: AI adapters, regex extractor, schema validator.
- QA engineer: contract tests, edge cases, fallback verification.
- Product owner: acceptance review and business fit.

## 5. Definition of Done (System)
- All acceptance criteria from functional spec are met.
- No critical/high severity defects open.
- Logs provide parser source and submission trace for each run.
- Security review completed for secrets handling.

## 6. Risk Burn-Down Priorities
1. Credential handling and secret management
2. API contract mismatch on multipart fields
3. AI invalid JSON or quota failures
4. Scanned PDF rejection false positives
5. Numeric coercion/data normalization bugs
