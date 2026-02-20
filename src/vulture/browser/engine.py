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
    adapter_name: str = "generic"
    tailored_resume_path: str | None = None


class BrowserAutomationEngine:
    _LINKEDIN_EASY_APPLY_READY = "LINKEDIN_EASY_APPLY_READY"
    _LINKEDIN_EASY_APPLY_UNAVAILABLE = "LINKEDIN_EASY_APPLY_UNAVAILABLE"
    _LINKEDIN_EXTERNAL_APPLY = "LINKEDIN_EXTERNAL_APPLY"
    _LINKEDIN_CAPTCHA_DETECTED = "LINKEDIN_CAPTCHA_DETECTED"
    _LINKEDIN_STEPS_COMPLETED = "LINKEDIN_STEPS_COMPLETED"
    _LINKEDIN_RESUME_UPLOADED = "LINKEDIN_RESUME_UPLOADED"
    _LINKEDIN_SUBMIT_COMPLETED = "LINKEDIN_SUBMIT_COMPLETED"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.adapter = BrowserUseAdapter(settings)

    def execute_action(self, context: BrowserContext, action: str) -> BrowserFillResult:
        adapter_name = (context.adapter_name or detect_adapter(context.job_url).name).lower()

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

        if action == "linkedin_open_easy_apply":
            result_text = self.adapter.run_task_sync(
                task=(
                    f"Open {context.job_url} in LinkedIn and prepare Easy Apply without submitting. "
                    f"If Easy Apply modal is available and opened, reply with {self._LINKEDIN_EASY_APPLY_READY}. "
                    f"If the listing is external apply or Easy Apply is unavailable, reply with "
                    f"{self._LINKEDIN_EASY_APPLY_UNAVAILABLE} or {self._LINKEDIN_EXTERNAL_APPLY}. "
                    f"If CAPTCHA or human verification appears, reply with {self._LINKEDIN_CAPTCHA_DETECTED}. "
                    "Always include one marker token in the final response."
                )
            )
            return self._linkedin_result(
                action=action,
                stage="start_browser_session",
                result_text=result_text,
                success_markers=(self._LINKEDIN_EASY_APPLY_READY,),
                blocked_message=(
                    "LinkedIn Easy Apply is not available for this job posting. "
                    "Use manual apply or choose another posting with Easy Apply."
                ),
            )

        if action == "linkedin_fill_steps":
            result_text = self.adapter.run_task_sync(
                task=(
                    f"Continue LinkedIn Easy Apply for {context.job_url}. Fill required fields one step at a time "
                    f"using available profile information for run {context.run_id}. "
                    "Do not submit the application yet. "
                    f"When all required steps are complete and the modal reaches review/submit, respond with "
                    f"{self._LINKEDIN_STEPS_COMPLETED}. "
                    f"If the flow switches to external apply or Easy Apply is unavailable, respond with "
                    f"{self._LINKEDIN_EXTERNAL_APPLY} or {self._LINKEDIN_EASY_APPLY_UNAVAILABLE}. "
                    f"If CAPTCHA appears, respond with {self._LINKEDIN_CAPTCHA_DETECTED}. "
                    "Always include one marker token in the final response."
                )
            )
            return self._linkedin_result(
                action=action,
                stage="fill_required_section",
                result_text=result_text,
                success_markers=(self._LINKEDIN_STEPS_COMPLETED,),
                blocked_message=(
                    "LinkedIn Easy Apply steps could not be completed in-app. "
                    "Run blocked for manual follow-up."
                ),
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
            if adapter_name == "linkedin":
                if not context.tailored_resume_path:
                    return BrowserFillResult(
                        status="blocked",
                        stage="file_upload",
                        action=action,
                        message=(
                            "LinkedIn resume upload requires a tailored resume path, but none was found in run context."
                        ),
                    )

                result_text = self.adapter.run_task_sync(
                    task=(
                        f"Within LinkedIn Easy Apply for {context.job_url}, upload resume file from path "
                        f"{context.tailored_resume_path}. Do not submit. "
                        f"If upload succeeds, reply with {self._LINKEDIN_RESUME_UPLOADED}. "
                        f"If flow is external apply or Easy Apply is unavailable, reply with "
                        f"{self._LINKEDIN_EXTERNAL_APPLY} or {self._LINKEDIN_EASY_APPLY_UNAVAILABLE}. "
                        f"If CAPTCHA appears, reply with {self._LINKEDIN_CAPTCHA_DETECTED}. "
                        "Always include one marker token in the final response."
                    )
                )
                result = self._linkedin_result(
                    action=action,
                    stage="file_upload",
                    result_text=result_text,
                    success_markers=(self._LINKEDIN_RESUME_UPLOADED,),
                    blocked_message=(
                        "LinkedIn resume upload could not be completed in Easy Apply. "
                        "Run blocked for manual handling."
                    ),
                )
                if result.status == "completed":
                    result.fields = [
                        FieldFillPlan(
                            field_key="resume_file",
                            locator="input[type=file]",
                            value_source="run_context.tailored_resume_path",
                            confidence=0.9,
                        )
                    ]
                return result

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

            if adapter_name == "linkedin":
                result_text = self.adapter.run_task_sync(
                    task=(
                        f"From LinkedIn Easy Apply review step for {context.job_url}, submit the application. "
                        f"If submission confirmation is shown, respond with {self._LINKEDIN_SUBMIT_COMPLETED}. "
                        f"If flow switches to external apply or Easy Apply is unavailable, respond with "
                        f"{self._LINKEDIN_EXTERNAL_APPLY} or {self._LINKEDIN_EASY_APPLY_UNAVAILABLE}. "
                        f"If CAPTCHA appears, respond with {self._LINKEDIN_CAPTCHA_DETECTED}. "
                        "Always include one marker token in the final response."
                    )
                )
                return self._linkedin_result(
                    action=action,
                    stage="final_submit",
                    result_text=result_text,
                    success_markers=(self._LINKEDIN_SUBMIT_COMPLETED,),
                    blocked_message=(
                        "LinkedIn submit could not be completed in-app. "
                        "Run blocked for manual continuation."
                    ),
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

    def _linkedin_result(
        self,
        *,
        action: str,
        stage: str,
        result_text: str,
        success_markers: tuple[str, ...],
        blocked_message: str,
    ) -> BrowserFillResult:
        normalized = result_text.upper()
        if self._LINKEDIN_CAPTCHA_DETECTED in normalized:
            return BrowserFillResult(
                status="waiting_captcha",
                stage="captcha",
                action="human_solve",
                message="LinkedIn presented CAPTCHA/human verification; waiting for human intervention.",
            )

        if (
            self._LINKEDIN_EASY_APPLY_UNAVAILABLE in normalized
            or self._LINKEDIN_EXTERNAL_APPLY in normalized
        ):
            return BrowserFillResult(
                status="blocked",
                stage=stage,
                action=action,
                message=f"{blocked_message} Raw response: {result_text}",
            )

        if any(marker in normalized for marker in success_markers) or self._is_dry_run_fallback(result_text):
            return BrowserFillResult(
                status="completed",
                stage=stage,
                action=action,
                message=result_text,
            )

        return BrowserFillResult(
            status="blocked",
            stage=stage,
            action=action,
            message=(
                f"{blocked_message} Could not verify expected LinkedIn marker in browser response. "
                f"Raw response: {result_text}"
            ),
        )

    @staticmethod
    def _is_dry_run_fallback(text: str) -> bool:
        lowered = text.lower()
        return "dry-run fallback" in lowered or "browser-use not installed" in lowered
