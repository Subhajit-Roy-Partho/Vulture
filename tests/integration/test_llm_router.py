from vulture.config import Settings
from vulture.llm.router import LLMRouter


def test_llm_router_falls_back_to_heuristic_when_no_provider_available() -> None:
    settings = Settings(openai_api_key="", local_llm_enabled=False)
    router = LLMRouter(settings=settings)

    analysis = router.analyze_job(
        job_url="https://example.com/job",
        job_text=(
            "Software Engineer\n"
            "Responsibilities include building backend services.\n"
            "Requirements: Python, SQL, communication.\n"
        ),
    )

    assert analysis.title == "Software Engineer"
    assert isinstance(analysis.requirements, list)


def test_job_analysis_contract_shape() -> None:
    settings = Settings(openai_api_key="", local_llm_enabled=False)
    router = LLMRouter(settings=settings)

    analysis = router.analyze_job(
        job_url="https://example.com/job",
        job_text="Data Analyst\nRequirements: SQL\nResponsibilities: dashboards",
    )

    payload = analysis.model_dump()
    assert set(payload.keys()) == {
        "title",
        "company",
        "location",
        "responsibilities",
        "requirements",
        "compensation",
        "keywords",
    }
