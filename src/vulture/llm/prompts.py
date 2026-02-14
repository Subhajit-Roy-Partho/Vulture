from __future__ import annotations

JOB_ANALYSIS_PROMPT = """
You are extracting structured job details.
Return strict JSON with keys:
- title: string
- company: string
- location: string
- responsibilities: string[]
- requirements: string[]
- compensation: string
- keywords: string[]

Job URL: {job_url}
Job text:
{job_text}
""".strip()

TAILOR_DOCS_PROMPT = """
You are tailoring candidate documents to a job.
Return strict JSON with keys:
- resume_markdown: string
- cover_letter_markdown: string
- metadata: object

Profile summary:
{profile_summary}

Job analysis JSON:
{job_analysis_json}
""".strip()

PATCH_SUGGESTION_PROMPT = """
You are proposing profile database enrichment patches.
Return strict JSON with keys:
- rationale: string
- confidence: number (0..1)
- operations: array of objects with keys:
  - table: one of [profile_personal, profile_preferences, profile_work_auth, skills]
  - operation: one of [insert, update, upsert]
  - key: object
  - values: object
  - source: string
  - confidence: number

Profile facts:
{profile_json}

Job analysis JSON:
{job_analysis_json}
""".strip()

ANSWER_DRAFT_PROMPT = """
You draft a concise, truthful application answer.
Use only given profile facts. If unknown, return exactly: UNKNOWN.

Question:
{question}

Profile facts:
{profile_json}

Job analysis:
{job_analysis_json}
""".strip()
