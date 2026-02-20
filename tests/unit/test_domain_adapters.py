from vulture.browser.domain_adapters import detect_adapter


def test_detect_adapter_linkedin() -> None:
    adapter = detect_adapter("https://www.linkedin.com/jobs/view/123456")
    assert adapter.name == "linkedin"
    assert "Easy Apply" in adapter.instructions


def test_detect_adapter_existing_domains_and_generic() -> None:
    assert detect_adapter("https://boards.greenhouse.io/acme/jobs/1").name == "greenhouse"
    assert detect_adapter("https://jobs.lever.co/acme/1").name == "lever"
    assert detect_adapter("https://example.com/jobs/1").name == "generic"
