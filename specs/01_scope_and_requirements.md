# Candidate Intake Automation - Scope and Requirements

## 1. Objective
Build an automation system that adds candidates to the company portal without manual copy-paste entry from resumes.

The system must:
- Authenticate with the existing admin API.
- Accept candidate input in two ways: direct text paste or resume upload.
- Convert unstructured candidate information into portal-compatible payload fields.
- Submit data to the existing candidate create API.
- Use low-cost/free AI-first extraction with deterministic fallback.

## 2. Problem Statement
Current process is manual and repetitive:
- Recruiter reads resume.
- Recruiter copies each field one by one into a web form.
- Time is lost and errors increase with repetition.

The target solution removes manual field-by-field typing while preserving data quality and compatibility with the existing backend.

## 3. Stakeholders
- Primary user: recruiter / operations staff adding candidates.
- Product owner: automation operator (you).
- Beneficiary organization: friend company using the portal.

## 4. Success Criteria
- Support at least 10 candidate submissions per day within free AI quota constraints.
- Reduce manual entry effort by >= 80%.
- Structured payload generation success rate >= 95% for supported resumes.
- API submission success rate >= 98% for valid inputs.

## 5. In Scope
- API authentication token generation and reuse.
- Candidate data ingestion:
  - Mode A: plain text paste.
  - Mode B: resume upload (PDF/DOC/DOCX).
- Resume text extraction (non-OCR only).
- Field normalization and transformation to portal payload format.
- 3-level extraction strategy:
  1. Gemini
  2. Grok
  3. Regex/non-AI parser
- Candidate create request to existing API endpoint.
- Validation and user-facing error reporting before submission.

## 6. Out of Scope
- OCR for scanned PDFs/images.
- Portal UI redesign.
- Candidate update/edit lifecycle beyond create flow.
- Multi-tenant architecture.
- Fully autonomous decision-making without operator visibility.

## 7. Key Constraints
- Must work with existing backend endpoints and payload contract.
- Must be optimized for free-tier AI usage (Gemini/Grok).
- Must provide deterministic fallback when AI fails or quota/rate-limit is reached.
- Must avoid storing plaintext credentials in source-controlled files.

## 8. Assumptions
- Authentication credentials are valid and authorized.
- Existing API endpoint behavior remains stable.
- Uploaded resumes are text-based files (not scanned documents).
- Candidate creation endpoint accepts multipart/form-data with optional resume file.

## 9. High-Level User Journey
1. User authenticates or system fetches valid token.
2. User chooses input method:
   - Paste all candidate details text.
   - Upload resume file.
3. System extracts and structures data.
4. System validates required fields.
5. System submits multipart request to candidate API.
6. System returns success/failure with reason and trace.

## 10. Non-Functional Requirements
- Reliability: retry transient failures with safe limits.
- Security: credentials/tokens in environment secrets only.
- Observability: log extraction source (Gemini/Grok/Regex), confidence, and submission status.
- Performance: average processing time <= 25 seconds per candidate under normal conditions.

## 11. Risks and Mitigations
- AI quota exceeded -> automatic fallback to next provider and then regex parser.
- Model hallucination/wrong mapping -> strict schema validation and type checks.
- API contract drift -> versioned field mapping and contract test fixtures.
- Exposed credentials -> immediate credential rotation and secret vault usage.
