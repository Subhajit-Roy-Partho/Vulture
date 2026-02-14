from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from vulture.config import Settings, get_settings
from vulture.llm.prompts import (
    ANSWER_DRAFT_PROMPT,
    JOB_ANALYSIS_PROMPT,
    PATCH_SUGGESTION_PROMPT,
    TAILOR_DOCS_PROMPT,
)
from vulture.llm.providers import ProviderPool
from vulture.types import JobAnalysis, PatchOperation, ProfilePatchBundle, TailoredDocuments

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.pool = ProviderPool(self.settings)

    def analyze_job(self, *, job_url: str, job_text: str) -> JobAnalysis:
        prompt = JOB_ANALYSIS_PROMPT.format(job_url=job_url, job_text=job_text[:20000])

        data = self._call_json(task="extract", prompt=prompt, model=self.settings.openai_model_extractor)
        if not data:
            return heuristic_job_analysis(job_url=job_url, job_text=job_text)

        try:
            return JobAnalysis.model_validate(data)
        except Exception:
            logger.warning("Invalid structured job analysis output; falling back to heuristic")
            return heuristic_job_analysis(job_url=job_url, job_text=job_text)

    def tailor_documents(self, *, profile: Any, analysis: JobAnalysis) -> TailoredDocuments:
        profile_summary = json.dumps(safe_dict(profile), ensure_ascii=True, default=str)
        prompt = TAILOR_DOCS_PROMPT.format(
            profile_summary=profile_summary,
            job_analysis_json=analysis.model_dump_json(indent=2),
        )
        data = self._call_json(task="writer", prompt=prompt, model=self.settings.openai_model_writer)
        if not data:
            return heuristic_tailored_documents(profile=profile, analysis=analysis)

        try:
            return TailoredDocuments.model_validate(data)
        except Exception:
            logger.warning("Invalid tailored document payload; falling back to heuristic")
            return heuristic_tailored_documents(profile=profile, analysis=analysis)

    def suggest_profile_patch(self, *, profile: Any, analysis: JobAnalysis) -> ProfilePatchBundle:
        profile_json = json.dumps(safe_dict(profile), ensure_ascii=True, default=str)
        prompt = PATCH_SUGGESTION_PROMPT.format(
            profile_json=profile_json,
            job_analysis_json=analysis.model_dump_json(indent=2),
        )
        data = self._call_json(
            task="db_patch",
            prompt=prompt,
            model=self.settings.local_llm_model,
        )

        if not data:
            return ProfilePatchBundle(rationale="No patch suggestions", operations=[], confidence=0.0)

        operations: list[PatchOperation] = []
        for raw in data.get("operations", []):
            try:
                operations.append(PatchOperation.model_validate(raw))
            except Exception:
                continue

        confidence = data.get("confidence", 0.0)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0

        return ProfilePatchBundle(
            rationale=str(data.get("rationale", "")),
            operations=operations,
            confidence=max(0.0, min(1.0, confidence_value)),
        )

    def draft_answer(self, *, question: str, profile: Any, analysis: JobAnalysis) -> str:
        prompt = ANSWER_DRAFT_PROMPT.format(
            question=question,
            profile_json=json.dumps(safe_dict(profile), ensure_ascii=True, default=str),
            job_analysis_json=analysis.model_dump_json(indent=2),
        )

        text = self._call_text(task="writer", prompt=prompt, model=self.settings.openai_model_writer)
        answer = text.strip()
        return answer or "UNKNOWN"

    def _provider_for(self, task: str):
        provider_name = {
            "plan": self.settings.llm_router_plan_provider,
            "extract": self.settings.llm_router_extract_provider,
            "db_patch": self.settings.llm_router_db_patch_provider,
            "writer": self.settings.llm_router_writer_provider,
        }.get(task, self.settings.llm_router_default)

        if provider_name == "local":
            return self.pool.local(), self.pool.openai()
        return self.pool.openai(), self.pool.local()

    def _call_json(self, *, task: str, prompt: str, model: str) -> dict[str, Any]:
        primary, fallback = self._provider_for(task)

        for provider in [primary, fallback]:
            if provider is None:
                continue
            try:
                if provider.config.name == "openai" and not self.settings.openai_api_key:
                    continue
                if provider.config.name == "local" and not self.settings.local_llm_enabled:
                    continue
                return provider.complete_json(model=model, prompt=prompt)
            except Exception as exc:
                logger.warning("LLM JSON call failed provider=%s error=%s", provider.config.name, exc)
        return {}

    def _call_text(self, *, task: str, prompt: str, model: str) -> str:
        primary, fallback = self._provider_for(task)
        for provider in [primary, fallback]:
            if provider is None:
                continue
            try:
                if provider.config.name == "openai" and not self.settings.openai_api_key:
                    continue
                if provider.config.name == "local" and not self.settings.local_llm_enabled:
                    continue
                return provider.complete_text(model=model, prompt=prompt).content
            except Exception as exc:
                logger.warning("LLM text call failed provider=%s error=%s", provider.config.name, exc)
        return ""


def safe_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)

    payload = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        candidate = getattr(value, key)
        if callable(candidate):
            continue
        try:
            json.dumps(candidate, default=str)
            payload[key] = candidate
        except TypeError:
            payload[key] = str(candidate)
    return payload


def heuristic_job_analysis(*, job_url: str, job_text: str) -> JobAnalysis:
    lines = [line.strip() for line in job_text.splitlines() if line.strip()]
    title = lines[0] if lines else "Unknown Title"
    company = ""
    location = ""

    responsibilities = [line for line in lines if "responsib" in line.lower()][:8]
    requirements = [line for line in lines if "require" in line.lower() or "qualif" in line.lower()][:8]

    if not responsibilities:
        responsibilities = lines[1:5]
    if not requirements:
        requirements = lines[5:10]

    keywords = []
    for token in ["python", "sql", "aws", "javascript", "leadership", "communication"]:
        if token in job_text.lower():
            keywords.append(token)

    return JobAnalysis(
        title=title,
        company=company,
        location=location,
        responsibilities=responsibilities,
        requirements=requirements,
        compensation="",
        keywords=keywords,
    )


def heuristic_tailored_documents(*, profile: Any, analysis: JobAnalysis) -> TailoredDocuments:
    profile_data = safe_dict(profile)
    name = profile_data.get("name", "Candidate")
    family = profile_data.get("job_family", "Professional")

    resume_markdown = "\n".join(
        [
            f"# {name}",
            "",
            f"## Target Role: {analysis.title or family}",
            "",
            "## Summary",
            (
                f"Experienced {family.lower()} focused on {', '.join(analysis.keywords[:5])} "
                "with measurable delivery across cross-functional teams."
            ),
            "",
            "## Key Responsibilities Alignment",
            *[f"- {item}" for item in analysis.responsibilities[:6]],
            "",
            "## Key Requirements Alignment",
            *[f"- {item}" for item in analysis.requirements[:6]],
        ]
    )

    cover_letter_markdown = "\n".join(
        [
            f"Dear Hiring Team at {analysis.company or 'your company'},",
            "",
            f"I am applying for the {analysis.title or family} role.",
            "My background aligns with your requirements, and I can contribute immediately.",
            "",
            "Sincerely,",
            str(name),
        ]
    )

    return TailoredDocuments(
        resume_markdown=resume_markdown,
        cover_letter_markdown=cover_letter_markdown,
        metadata={"strategy": "heuristic_fallback"},
    )
