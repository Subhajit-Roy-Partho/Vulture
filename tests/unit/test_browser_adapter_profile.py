from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from vulture.browser.adapter import BrowserUseAdapter
from vulture.config import Settings


class FakeBrowserProfile:
    latest_kwargs: dict | None = None

    def __init__(self, **kwargs):
        FakeBrowserProfile.latest_kwargs = kwargs


class FakeBrowserSession:
    latest_browser_profile = None

    def __init__(self, browser_profile=None, **kwargs):
        FakeBrowserSession.latest_browser_profile = browser_profile


class FakeAgent:
    latest_task: str | None = None
    latest_browser_session = None

    def __init__(self, *, task: str, browser_session=None, **kwargs):
        FakeAgent.latest_task = task
        FakeAgent.latest_browser_session = browser_session

    async def run(self, *, max_steps: int):
        return f"ok:{max_steps}"


def test_run_task_uses_persistent_profile(monkeypatch, tmp_path: Path) -> None:
    fake_browser_use = SimpleNamespace(
        Agent=FakeAgent,
        BrowserProfile=FakeBrowserProfile,
        BrowserSession=FakeBrowserSession,
    )
    monkeypatch.setitem(sys.modules, "browser_use", fake_browser_use)

    settings = Settings(
        browser_use_user_data_dir=tmp_path / "browser_profile",
        browser_use_headless=False,
        browser_use_keep_browser_open=True,
        browser_use_allowed_domains="linkedin.com,example.com",
        browser_use_blocked_domains="bad.example",
        browser_use_channel="chrome",
        browser_use_executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        browser_use_profile_directory="Default",
        browser_use_max_steps=7,
    )
    adapter = BrowserUseAdapter(settings)

    result = asyncio.run(adapter.run_task("test task"))

    assert result == "ok:7"
    assert FakeAgent.latest_task == "test task"
    assert FakeAgent.latest_browser_session is not None
    assert FakeBrowserSession.latest_browser_profile is not None
    assert FakeBrowserProfile.latest_kwargs is not None
    assert FakeBrowserProfile.latest_kwargs["user_data_dir"] == str((tmp_path / "browser_profile").resolve())
    assert FakeBrowserProfile.latest_kwargs["headless"] is False
    assert FakeBrowserProfile.latest_kwargs["keep_alive"] is True
    assert FakeBrowserProfile.latest_kwargs["allowed_domains"] == ["linkedin.com", "example.com"]
    assert FakeBrowserProfile.latest_kwargs["prohibited_domains"] == ["bad.example"]
    assert FakeBrowserProfile.latest_kwargs["channel"] == "chrome"
    assert (
        FakeBrowserProfile.latest_kwargs["executable_path"]
        == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    assert FakeBrowserProfile.latest_kwargs["profile_directory"] == "Default"
