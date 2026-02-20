from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_SECTION_PATTERN = re.compile(r"\\begin\{rSection\}\{([^}]+)\}(.*?)\\end\{rSection\}", re.DOTALL)
_ITEM_PATTERN = re.compile(r"\\item\s+(.*?)(?=(?:\\item\s+)|$)", re.DOTALL)
_HREF_PATTERN = re.compile(r"\\href\{([^}]+)\}\{([^}]*)\}")


@dataclass(slots=True)
class ParsedSection:
    name: str
    raw: str
    lines: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class ParsedCV:
    sections: dict[str, ParsedSection] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def parse_cv_text(raw_text: str, input_format: str = "latex") -> ParsedCV:
    if input_format not in {"latex", "text"}:
        raise ValueError("input_format must be 'latex' or 'text'")

    if input_format == "text":
        section = ParsedSection(
            name="general",
            raw=raw_text,
            lines=_extract_lines(raw_text),
            bullets=_extract_bullets(raw_text),
            links=_extract_links(raw_text),
        )
        return ParsedCV(sections={"general": section}, warnings=[])

    sections: dict[str, ParsedSection] = {}
    for match in _SECTION_PATTERN.finditer(raw_text):
        name = canonical_section_name(match.group(1))
        body = match.group(2)
        sections[name] = ParsedSection(
            name=name,
            raw=body,
            lines=_extract_lines(body),
            bullets=_extract_bullets(body),
            links=_extract_links(body),
        )

    warnings: list[str] = []
    if not sections:
        warnings.append("No rSection blocks found; parser fell back to generic parsing")
        sections["general"] = ParsedSection(
            name="general",
            raw=raw_text,
            lines=_extract_lines(raw_text),
            bullets=_extract_bullets(raw_text),
            links=_extract_links(raw_text),
        )

    metadata = {
        "all_links": _extract_links(raw_text),
        "all_lines": _extract_lines(raw_text),
    }
    return ParsedCV(sections=sections, warnings=warnings, metadata=metadata)


def canonical_section_name(name: str) -> str:
    value = normalize_latex(name).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    aliases = {
        "summary": "summary",
        "profile": "summary",
        "education": "education",
        "research_experience": "research_experience",
        "experience": "research_experience",
        "technical_skills": "technical_skills",
        "skills": "technical_skills",
        "publications_preprints": "publications",
        "publications": "publications",
        "awards_honors": "awards",
        "awards": "awards",
        "presentations_conferences": "conferences",
        "conferences": "conferences",
        "teaching_mentoring_experience": "teaching",
        "leadership_mentoring": "teaching",
        "service_outreach": "service",
        "additional_projects_during_bs_ms": "additional_projects",
        "additional_projects": "additional_projects",
        "core_competencies": "core_competencies",
        "robotics_multimodal_stack_ramping_up": "robotics_stack",
    }
    return aliases.get(value, value)


def normalize_latex(text: str) -> str:
    out = text
    out = out.replace("\\\n", "\n")
    out = out.replace("\\%", "%")
    out = re.sub(r"\\textbf\{([^}]*)\}", r"\1", out)
    out = re.sub(r"\\textit\{([^}]*)\}", r"\1", out)
    out = re.sub(r"\\fontfamily\{[^}]*\}\\selectfont", "", out)
    out = re.sub(r"\\href\{([^}]+)\}\{([^}]*)\}", r"\2 (\1)", out)
    out = re.sub(r"\\fa[A-Za-z]+", "", out)
    out = re.sub(r"\\eqmark", "", out)
    out = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", out)
    out = re.sub(r"[{}]", " ", out)
    out = out.replace("~", " ")
    out = out.replace("$", "")
    out = re.sub(r"\s+", " ", out)
    return out.strip()


def _extract_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        cleaned = normalize_latex(raw)
        if not cleaned:
            continue
        if cleaned in {"begin rSection", "end rSection"}:
            continue
        lines.append(cleaned)
    return lines


def _extract_bullets(text: str) -> list[str]:
    items: list[str] = []
    for match in _ITEM_PATTERN.finditer(text):
        cleaned = normalize_latex(match.group(1))
        if cleaned:
            items.append(cleaned)
    return items


def _extract_links(text: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for url, label in _HREF_PATTERN.findall(text):
        links.append({"url": url.strip(), "label": normalize_latex(label)})
    return links
