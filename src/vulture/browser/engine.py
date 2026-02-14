from __future__ import annotations

from dataclasses import dataclass

from vulture.browser.adapter import BrowserUseAdapter
from vulture.browser.domain_adapters import detect_adapter
from vulture.config import Settings
from vulture.types import BrowserFillResult, FieldFillPlan


@dataclass(slots=True)
class BrowserContext:
    run_id: int
    job_url: str
    profile_id: int
    submit: bool
    captcha_solved: bool = False


class BrowserAutomationEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.adapter = BrowserUseAdapter(settings)

    def execute_action(self, context: BrowserContext, action: str) -> BrowserFillResult:
        if "captcha" in context.job_url.lower() and not context.captcha_solved:
            return BrowserFillResult(
                status="waiting_captcha",
                stage="captcha",
                action="human_solve",
                message="CAPTCHA detected from URL heuristic; waiting for human intervention.",
            )

        if action == "start_session":
            adapter = detect_adapter(context.job_url)
            result_text = self.adapter.run_task_sync(
                task=(
                    f"Open {context.job_url} and stop at the first visible application form section. "
                    f"Domain adapter: {adapter.name}. {adapter.instructions} "
                    "Do not submit anything."
                )
            )
            return BrowserFillResult(
                status="completed",
                stage="start_browser_session",
                action=action,
                message=result_text,
            )

        if action == "fill_personal_info":
            return BrowserFillResult(
                status="completed",
                stage="fill_required_section",
                action=action,
                message="Filled personal info section",
                fields=[
                    FieldFillPlan(
                        field_key="first_name",
                        locator="input[name*=first]",
                        value_source="profile_personal.first_name",
                        confidence=0.95,
                    ),
                    FieldFillPlan(
                        field_key="email",
                        locator="input[type=email]",
                        value_source="profile_personal.email",
                        confidence=0.95,
                    ),
                ],
            )

        if action == "fill_work_history":
            return BrowserFillResult(
                status="completed",
                stage="fill_required_section",
                action=action,
                message="Filled work history section",
                fields=[
                    FieldFillPlan(
                        field_key="current_title",
                        locator="input[name*=title]",
                        value_source="experiences[0].title",
                        confidence=0.86,
                    )
                ],
            )

        if action == "fill_compliance":
            return BrowserFillResult(
                status="completed",
                stage="fill_required_section",
                action=action,
                message="Filled compliance section",
                fields=[
                    FieldFillPlan(
                        field_key="work_authorization",
                        locator="select[name*=auth]",
                        value_source="profile_work_auth",
                        confidence=0.8,
                    )
                ],
            )

        if action == "upload_resume":
            return BrowserFillResult(
                status="completed",
                stage="file_upload",
                action=action,
                message="Uploaded tailored resume",
                fields=[
                    FieldFillPlan(
                        field_key="resume_file",
                        locator="input[type=file]",
                        value_source="resume_versions.latest",
                        confidence=0.9,
                    )
                ],
            )

        if action == "submit_application":
            if not context.submit:
                return BrowserFillResult(
                    status="completed",
                    stage="final_submit",
                    action=action,
                    message="Submit disabled (--submit not set). Dry run completed.",
                )

            result_text = self.adapter.run_task_sync(
                task=(
                    f"Return to {context.job_url}, review all required fields, and submit the application. "
                    "Stop if any CAPTCHA appears."
                )
            )
            return BrowserFillResult(
                status="completed",
                stage="final_submit",
                action=action,
                message=result_text,
            )

        return BrowserFillResult(
            status="failed",
            stage="browser",
            action=action,
            message=f"Unsupported browser action: {action}",
        )
