from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class DomainAdapter:
    name: str
    instructions: str


def detect_adapter(url: str) -> DomainAdapter:
    host = urlparse(url).netloc.lower()

    if "greenhouse" in host:
        return DomainAdapter(
            name="greenhouse",
            instructions=(
                "Greenhouse forms usually include grouped sections for personal information, "
                "resume upload, EEOC voluntary self-identification, and custom questions. "
                "Watch for required fields marked with an asterisk."
            ),
        )

    if "lever" in host:
        return DomainAdapter(
            name="lever",
            instructions=(
                "Lever applications often render profile fields and resume upload in one page, "
                "then optional links and additional questions. Prefer stable input names over placeholders."
            ),
        )

    if "workable" in host:
        return DomainAdapter(
            name="workable",
            instructions=(
                "Workable forms are usually modular with optional screening questions. "
                "Handle radio and select controls carefully and preserve user-declared compliance answers."
            ),
        )

    if "smartrecruiters" in host:
        return DomainAdapter(
            name="smartrecruiters",
            instructions=(
                "SmartRecruiters flows may include account creation and multi-step forms. "
                "Proceed step-by-step and verify required fields before advancing."
            ),
        )

    if "linkedin.com" in host:
        return DomainAdapter(
            name="linkedin",
            instructions=(
                "LinkedIn flows should prioritize Easy Apply modal detection. "
                "If the posting routes to external apply instead of Easy Apply, stop and report it. "
                "Complete one step at a time, validate required fields before moving forward, "
                "and stop immediately if CAPTCHA or additional human verification appears."
            ),
        )

    return DomainAdapter(
        name="generic",
        instructions=(
            "Use robust fallback form detection with semantic labels and avoid assumptions about field order."
        ),
    )
