from __future__ import annotations

import asyncio
import logging

from vulture.config import Settings

logger = logging.getLogger(__name__)


class BrowserUseAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def run_task(self, task: str) -> str:
        try:
            from browser_use import Agent
        except Exception as exc:
            logger.warning("browser-use unavailable: %s", exc)
            return "browser-use not installed or failed to import; using dry-run fallback"

        try:
            agent = Agent(task=task)
            result = await agent.run(max_steps=self.settings.browser_use_max_steps)
            return str(result)
        except Exception as exc:
            logger.warning("browser-use task execution failed: %s", exc)
            return f"browser-use execution failed; dry-run fallback active ({exc})"

    def run_task_sync(self, task: str) -> str:
        return asyncio.run(self.run_task(task))
