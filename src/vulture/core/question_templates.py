from __future__ import annotations

import re
from collections import OrderedDict

from vulture.core.cv_parser import ParsedCV
from vulture.types import QuestionTemplate


CRITICAL_TAGS = {"legal", "compliance", "attestation", "compensation"}


def generate_question_templates(parsed: ParsedCV, scope: str = "all") -> list[QuestionTemplate]:
    templates: list[QuestionTemplate] = []

    if scope not in {"all", "hiring_core", "research_core"}:
        scope = "all"

    _add_contact_questions(parsed, templates)
    _add_summary_questions(parsed, templates)
    _add_education_questions(parsed, templates)
    _add_research_questions(parsed, templates)
    _add_skills_questions(parsed, templates)
    _add_publication_questions(parsed, templates)
    _add_award_questions(parsed, templates)

    if scope in {"all", "research_core"}:
        _add_conference_questions(parsed, templates)
        _add_teaching_questions(parsed, templates)
        _add_service_questions(parsed, templates)
        _add_additional_project_questions(parsed, templates)

    _add_compliance_and_job_prefs(templates)
    _expand_domain_prompts(parsed, templates)
    templates = _dedupe_templates(templates)

    if len(templates) < 120:
        templates.extend(_fallback_question_templates(target=130 - len(templates)))
        templates = _dedupe_templates(templates)

    return templates[:160]


def is_critical_template(template: QuestionTemplate) -> bool:
    tags = {tag.lower() for tag in template.tags}
    return bool(tags & CRITICAL_TAGS)


def _add_contact_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    base_questions = [
        "What is your full legal name?",
        "What email address should employers use to contact you?",
        "What is your primary phone number in E.164 format?",
        "What is your current city and state?",
        "What is your full mailing address?",
        "What is your LinkedIn profile URL?",
        "What is your GitHub profile URL?",
        "What is your Google Scholar profile URL?",
        "What is your portfolio website URL?",
        "What is your preferred pronoun (optional)?",
        "What is your preferred first name for communication?",
        "Do you have an alternate contact email?",
    ]
    for question in base_questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="short_text" if "URL" not in question else "url",
                tags=["profile", "contact"],
                source_section="contact",
                importance="high",
            )
        )

    for link in parsed.metadata.get("all_links", []):
        label = str(link.get("label", "")).strip()
        url = str(link.get("url", "")).strip()
        if not label and not url:
            continue
        templates.append(
            QuestionTemplate(
                canonical_text=f"Confirm your {label or 'external'} link",
                question_type="url",
                tags=["profile", "contact", "link"],
                suggested_answer=url,
                source_section="contact",
                importance="medium",
            )
        )


def _add_summary_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    summary = parsed.sections.get("summary")
    if not summary:
        return

    focus_questions = [
        "Write a 2-3 sentence professional summary tailored for ML systems roles.",
        "What research domain best describes your work?",
        "What core problem area do you specialize in?",
        "What production systems have you built end-to-end?",
        "What scale of workloads have you supported?",
        "What are your top three strengths for this role?",
        "Which part of your background is most relevant to this position?",
        "What motivates you to apply for this role?",
        "What unique perspective do you bring to cross-disciplinary teams?",
        "Describe one measurable impact from your recent work.",
    ]
    for question in focus_questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="long_text",
                tags=["summary", "research"],
                source_section="summary",
                importance="medium",
            )
        )

    for line in summary.lines[:6]:
        templates.append(
            QuestionTemplate(
                canonical_text=f"Elaborate on this summary claim: {line[:160]}",
                question_type="research",
                tags=["summary", "claim"],
                source_section="summary",
                importance="low",
            )
        )


def _add_education_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("education")
    if not section:
        return

    standard_questions = [
        "What is your highest completed degree?",
        "What institution awarded your highest degree?",
        "What is your current graduate program and department?",
        "Who is your primary advisor?",
        "What is your graduate GPA/CGPA?",
        "What is your undergraduate GPA/CGPA?",
        "What was your graduate research focus?",
        "What was your master's thesis title?",
        "What dates did you attend each degree program?",
        "What lab or research group are you currently part of?",
    ]
    for question in standard_questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="short_text",
                tags=["education"],
                source_section="education",
                importance="high",
            )
        )

    for line in section.lines:
        if any(token in line.lower() for token in ["phd", "ph.d", "b.s", "m.s", "integrated", "advisor", "gpa", "cgpa"]):
            templates.append(
                QuestionTemplate(
                    canonical_text=f"Confirm education detail: {line[:180]}",
                    question_type="short_text",
                    tags=["education", "verification"],
                    suggested_answer=line,
                    source_section="education",
                    importance="medium",
                )
            )


def _add_research_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("research_experience")
    if not section:
        return

    starter_questions = [
        "Describe your primary current research role and responsibilities.",
        "What ML systems have you developed for scientific workloads?",
        "What simulation frameworks have you actively developed or extended?",
        "What was your most impactful infrastructure contribution?",
        "What is the largest system scale you have run (e.g., particle count/workload size)?",
        "Describe one cross-functional collaboration with experimental scientists.",
        "What are your strongest tools for model evaluation and benchmarking?",
        "How do you ensure reproducibility in large research pipelines?",
        "Describe your approach to debugging large-scale simulation failures.",
        "What performance optimization techniques do you use on GPU/HPC systems?",
    ]
    for question in starter_questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="research",
                tags=["research", "ml", "hpc"],
                source_section="research_experience",
                importance="high",
            )
        )

    for idx, bullet in enumerate(section.bullets, start=1):
        templates.append(
            QuestionTemplate(
                canonical_text=f"Research bullet {idx}: provide STAR-form elaboration for '{bullet[:140]}'",
                question_type="long_text",
                tags=["research", "experience", "project"],
                suggested_answer=bullet,
                source_section="research_experience",
                importance="medium",
            )
        )
        templates.append(
            QuestionTemplate(
                canonical_text=f"What tools/tech stack were used in this outcome: '{bullet[:140]}'?",
                question_type="research",
                tags=["research", "tools"],
                source_section="research_experience",
                importance="low",
            )
        )


def _add_skills_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("technical_skills")
    if not section:
        return

    categories = [
        "Programming Languages",
        "Machine Learning",
        "Molecular Simulation",
        "Visualization Tools",
        "HPC & DevOps",
        "Experimental Methods",
        "Web Development",
        "Hardware/Embedded",
    ]
    for category in categories:
        templates.append(
            QuestionTemplate(
                canonical_text=f"List your strongest skills in category: {category}",
                question_type="short_text",
                tags=["skills", _slug(category)],
                source_section="technical_skills",
                importance="medium",
            )
        )
        templates.append(
            QuestionTemplate(
                canonical_text=f"Rate your proficiency for {category} skills (beginner/intermediate/advanced/expert).",
                question_type="single_select",
                tags=["skills", _slug(category)],
                source_section="technical_skills",
                importance="low",
            )
        )

    for line in section.lines:
        if ":" not in line:
            continue
        head, tail = [part.strip() for part in line.split(":", 1)]
        items = [item.strip() for item in re.split(r",|\|", tail) if item.strip()]
        for skill in items[:14]:
            templates.append(
                QuestionTemplate(
                    canonical_text=f"How many years of experience do you have with {skill}?",
                    question_type="number",
                    tags=["skills", _slug(head)],
                    source_section="technical_skills",
                    importance="low",
                )
            )


def _add_publication_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("publications")
    if not section:
        return

    base_questions = [
        "How many peer-reviewed publications and preprints do you have?",
        "What is your most relevant publication for this role?",
        "Describe your contribution role in your top publication.",
        "Which publication best demonstrates ML/systems impact?",
        "Provide DOI or URL for your top three publications.",
        "Have any of your works been under review at Nature-family journals?",
        "Describe one publication where you were not first author but had major technical impact.",
        "List publication venues relevant to this application.",
    ]
    for question in base_questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="publication",
                tags=["publication", "research"],
                source_section="publications",
                importance="high",
            )
        )

    for idx, item in enumerate(section.bullets, start=1):
        templates.append(
            QuestionTemplate(
                canonical_text=f"Publication {idx}: summarize key contribution and outcome.",
                question_type="publication",
                tags=["publication", "contribution"],
                suggested_answer=item,
                source_section="publications",
                importance="medium",
            )
        )
        templates.append(
            QuestionTemplate(
                canonical_text=f"Publication {idx}: provide citation in plain text.",
                question_type="short_text",
                tags=["publication", "citation"],
                suggested_answer=item,
                source_section="publications",
                importance="low",
            )
        )


def _add_award_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("awards")
    if not section:
        return

    questions = [
        "What awards or honors are most relevant to this job?",
        "What national or competitive fellowships have you received?",
        "Describe one award and why it was granted.",
        "List conference travel awards you have received.",
        "Have you received teaching or research assistantships?",
    ]
    for question in questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="award",
                tags=["award", "achievement"],
                source_section="awards",
                importance="medium",
            )
        )

    for item in section.bullets:
        templates.append(
            QuestionTemplate(
                canonical_text=f"Confirm award detail: {item[:170]}",
                question_type="award",
                tags=["award", "verification"],
                suggested_answer=item,
                source_section="awards",
                importance="low",
            )
        )


def _add_conference_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("conferences")
    if not section:
        return

    questions = [
        "List conferences where you presented your work.",
        "What was your role at your most recent conference?",
        "Describe the main topic of your latest conference presentation.",
        "Which conference audiences did you engage with?",
        "Have you presented software tooling at conferences?",
    ]
    for question in questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="conference",
                tags=["conference", "presentation"],
                source_section="conferences",
                importance="medium",
            )
        )

    for item in section.bullets:
        templates.append(
            QuestionTemplate(
                canonical_text=f"Conference detail: {item[:170]}",
                question_type="conference",
                tags=["conference", "verification"],
                suggested_answer=item,
                source_section="conferences",
                importance="low",
            )
        )


def _add_teaching_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("teaching")
    if not section:
        return

    questions = [
        "Describe your teaching assistant experience.",
        "What courses or labs have you supported?",
        "How many students have you mentored?",
        "Describe your mentoring style for graduate students.",
        "Have you designed educational automation or grading tools?",
    ]
    for question in questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="teaching",
                tags=["teaching", "mentoring"],
                source_section="teaching",
                importance="medium",
            )
        )

    for item in section.bullets:
        templates.append(
            QuestionTemplate(
                canonical_text=f"Teaching/mentoring detail: {item[:170]}",
                question_type="teaching",
                tags=["teaching", "verification"],
                suggested_answer=item,
                source_section="teaching",
                importance="low",
            )
        )


def _add_service_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("service")
    if not section:
        return

    questions = [
        "Describe your science outreach or community engagement work.",
        "List professional societies or student chapters you have contributed to.",
        "Describe event organization responsibilities you handled.",
        "How have you represented your department in public events?",
    ]
    for question in questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="service",
                tags=["service", "outreach"],
                source_section="service",
                importance="medium",
            )
        )

    for item in section.bullets:
        templates.append(
            QuestionTemplate(
                canonical_text=f"Service/outreach detail: {item[:170]}",
                question_type="service",
                tags=["service", "verification"],
                suggested_answer=item,
                source_section="service",
                importance="low",
            )
        )


def _add_additional_project_questions(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    section = parsed.sections.get("additional_projects")
    if not section:
        return

    questions = [
        "Describe one additional technical project from your BS-MS period.",
        "Which non-core-domain project best showcases your systems thinking?",
        "What embedded or hardware projects have you completed?",
        "Describe one parallel-computing optimization project you implemented.",
        "What imaging/analysis projects did you execute in astronomy or related areas?",
    ]
    for question in questions:
        templates.append(
            QuestionTemplate(
                canonical_text=question,
                question_type="project_metric",
                tags=["project", "additional"],
                source_section="additional_projects",
                importance="low",
            )
        )

    for item in section.bullets:
        templates.append(
            QuestionTemplate(
                canonical_text=f"Additional project detail: {item[:170]}",
                question_type="project_metric",
                tags=["project", "verification"],
                suggested_answer=item,
                source_section="additional_projects",
                importance="low",
            )
        )


def _add_compliance_and_job_prefs(templates: list[QuestionTemplate]) -> None:
    questions = [
        ("Are you legally authorized to work in the United States?", "work_auth", ["legal", "compliance"], "high"),
        ("Will you now or in the future require visa sponsorship?", "work_auth", ["legal", "compliance"], "high"),
        ("What are your salary expectations?", "salary", ["compensation", "legal"], "high"),
        ("What is your earliest available start date?", "date", ["availability"], "medium"),
        ("Are you willing to relocate?", "boolean", ["preference"], "medium"),
        ("Are you willing to travel for work?", "boolean", ["preference"], "medium"),
        ("Do you identify as a protected veteran?", "veteran", ["compliance", "legal"], "high"),
        ("Would you like to self-identify disability status?", "disability", ["compliance", "legal"], "high"),
    ]
    for text, qtype, tags, importance in questions:
        templates.append(
            QuestionTemplate(
                canonical_text=text,
                question_type=qtype,
                tags=tags,
                source_section="compliance",
                importance=importance,
            )
        )


def _expand_domain_prompts(parsed: ParsedCV, templates: list[QuestionTemplate]) -> None:
    domain_terms = OrderedDict.fromkeys(
        [
            "PyTorch",
            "TensorFlow",
            "LangChain",
            "Transformers",
            "GCNN",
            "DBSCAN",
            "OpenCV",
            "CUDA",
            "SLURM",
            "Docker",
            "Kubernetes",
            "oxDNA",
            "oxView",
            "AMBER",
            "NAMD",
            "GROMACS",
            "OpenMM",
            "Babylon.js",
            "Three.js",
            "React",
            "Node.js",
            "ARM64",
            "x86-64",
            "PCR",
            "AFM",
            "DNA-PAINT",
            "OpenCL",
        ]
    )

    all_lines = " ".join(parsed.metadata.get("all_lines", []))
    for term in domain_terms:
        if term.lower() not in all_lines.lower():
            continue
        templates.append(
            QuestionTemplate(
                canonical_text=f"Describe your hands-on experience with {term}.",
                question_type="research",
                tags=["skills", "research", _slug(term)],
                source_section="technical_skills",
                importance="low",
            )
        )
        templates.append(
            QuestionTemplate(
                canonical_text=f"What is your strongest accomplishment using {term}?",
                question_type="project_metric",
                tags=["project", _slug(term)],
                source_section="research_experience",
                importance="low",
            )
        )


def _dedupe_templates(templates: list[QuestionTemplate]) -> list[QuestionTemplate]:
    seen: dict[str, QuestionTemplate] = {}
    for template in templates:
        key = " ".join(template.canonical_text.lower().split())
        if key not in seen:
            seen[key] = template
    return list(seen.values())


def _fallback_question_templates(target: int) -> list[QuestionTemplate]:
    prompts = [
        "Describe the problem context, your actions, and measurable outcome.",
        "How did you ensure reproducibility and validation for this work?",
        "What trade-offs did you make and why?",
        "Which tooling accelerated delivery the most?",
        "What would you improve if you repeated this project?",
    ]
    templates: list[QuestionTemplate] = []
    for idx in range(max(0, target)):
        prompt = prompts[idx % len(prompts)]
        templates.append(
            QuestionTemplate(
                canonical_text=f"Scenario {idx + 1}: {prompt}",
                question_type="long_text",
                tags=["fallback", "research"],
                source_section="general",
                importance="low",
            )
        )
    return templates


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
