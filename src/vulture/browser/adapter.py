from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from vulture.config import Settings

logger = logging.getLogger(__name__)


class BrowserUseAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def run_task(self, task: str) -> str:
        try:
            from browser_use import Agent, BrowserProfile, BrowserSession
        except Exception as exc:
            logger.warning("browser-use unavailable: %s", exc)
            return "browser-use not installed or failed to import; using dry-run fallback"

        try:
            user_data_dir = Path(self.settings.browser_use_user_data_dir).expanduser().resolve()
            user_data_dir.mkdir(parents=True, exist_ok=True)

            profile_kwargs: dict[str, object] = {
                "user_data_dir": str(user_data_dir),
                "headless": self.settings.browser_use_headless,
                "keep_alive": self.settings.browser_use_keep_browser_open,
                "allowed_domains": self._split_domains(self.settings.browser_use_allowed_domains),
                "prohibited_domains": self._split_domains(self.settings.browser_use_blocked_domains),
            }
            if self.settings.browser_use_channel.strip():
                profile_kwargs["channel"] = self.settings.browser_use_channel.strip()
            if self.settings.browser_use_executable_path.strip():
                profile_kwargs["executable_path"] = self.settings.browser_use_executable_path.strip()
            if self.settings.browser_use_profile_directory.strip():
                profile_kwargs["profile_directory"] = self.settings.browser_use_profile_directory.strip()

            profile = BrowserProfile(**profile_kwargs)
            session = BrowserSession(browser_profile=profile)
            agent = Agent(task=task, browser_session=session)
            result = await agent.run(max_steps=self.settings.browser_use_max_steps)
            return str(result)
        except Exception as exc:
            logger.warning("browser-use task execution failed: %s", exc)
            return f"browser-use execution failed; dry-run fallback active ({exc})"

    def run_task_sync(self, task: str) -> str:
        return asyncio.run(self.run_task(task))

    @staticmethod
    def _split_domains(value: str) -> list[str] | None:
        domains = [item.strip() for item in value.split(",") if item.strip()]
        return domains or None
