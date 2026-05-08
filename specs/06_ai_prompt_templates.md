# Candidate Intake Automation - AI Prompt Templates

## 1. Prompting Principles
- Force strict JSON output only.
- No markdown, no explanation, no additional keys.
- Use canonical schema exactly.
- If a value is not confidently available, return null.

## 2. Canonical JSON Schema
Expected output keys:
- name: string | null
- phoneNumber: string | null
- email: string | null
- gender: string | number | null
- dob: string | null
- tag: string | number | null
- currentAddress: string | null
- totalExperience: number | null
- jewelleryExperience: number | null
- expectedSalary: number | null
- currentOrganisation: string | null
- currentDesignation: string | null
- preferredLocation: string | null
- currentInhandSalary: number | null

## 3. Gemini Prompt Template (Primary)
System Prompt:
You are an information extraction engine. Extract candidate details from provided text and return ONLY valid JSON object with exact keys as specified. Do not include markdown, comments, or prose.

User Prompt Template:
Extract candidate profile fields from the following resume/content.
Rules:
1. Return JSON only.
2. Use exact keys listed below.
3. Missing values must be null.
4. Numeric fields must be numbers, not strings.
5. phoneNumber should keep digits only.
6. If multiple values exist, choose most recent/professionally relevant.

Keys:
name, phoneNumber, email, gender, dob, tag, currentAddress, totalExperience, jewelleryExperience, expectedSalary, currentOrganisation, currentDesignation, preferredLocation, currentInhandSalary

Input Text:
{{RAW_TEXT}}

## 4. Grok Prompt Template (Secondary)
System Prompt:
You extract structured candidate data from resume text. Output must be a strict JSON object using only required keys. No extra text.

User Prompt Template:
Convert the input into candidate JSON.
Constraints:
- Output only JSON.
- Use exact keys.
- Unknown field -> null.
- Convert experience and salary to numbers.
- Normalize phone to digits-only string.

Required keys:
name, phoneNumber, email, gender, dob, tag, currentAddress, totalExperience, jewelleryExperience, expectedSalary, currentOrganisation, currentDesignation, preferredLocation, currentInhandSalary

Input:
{{RAW_TEXT}}

## 5. Parser Output Validation Rules
A parser result is VALID only if:
- JSON parses successfully.
- All required keys exist in object.
- Required fields non-null and non-empty:
  - name
  - phoneNumber
  - email
- phoneNumber matches digit pattern and minimum length policy.
- email passes syntax validation.

If invalid:
- Return INVALID with list of validation errors.

If provider/runtime issue:
- Return ERROR with provider error code/category.

## 6. Regex Fallback Hints (Non-AI)
Suggested extraction patterns (best effort):
- Email: standard email regex
- Phone: India-focused + generic international digit capture
- Experience: patterns around "years", "yrs", "experience"
- Name: top-of-document heuristic + label-based fallback
- Current company/designation: lines around "Current", "Present", "Company", "Designation"

Regex parser rules:
- Prefer precision over aggressive guessing.
- Always provide missing required fields list.
- Do not fabricate values.

## 7. Orchestrator Pseudocode Contract
1. Try Gemini.
2. If VALID -> use output.
3. Else try Grok.
4. If VALID -> use output.
5. Else run Regex parser.
6. If required fields still missing -> return correction-needed response.
7. Else continue to mapping and API submit.

## 8. Token and Cost Controls
- Keep prompts short and stable.
- Set max output tokens to minimal safe value for JSON payload.
- Use one retry max per provider for transient failures.
- On 429, switch provider immediately.
