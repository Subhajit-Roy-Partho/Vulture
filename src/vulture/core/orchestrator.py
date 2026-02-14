from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from vulture.browser.engine import BrowserAutomationEngine, BrowserContext
from vulture.config import Settings, get_settings
from vulture.core.events import EventBus
from vulture.core.job_fetcher import fetch_job_text
from vulture.core.modes import ModePolicy
from vulture.core.runtime import get_event_bus
from vulture.db.repositories import Repository
from vulture.llm.router import LLMRouter
from vulture.types import JobAnalysis, PatchOperation, ProfilePatchBundle

logger = logging.getLogger(__name__)


class RunOrchestrator:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        event_bus: EventBus | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.repo = Repository(session)
        self.llm = LLMRouter(self.settings)
        self.browser = BrowserAutomationEngine(self.settings)
        self.event_bus = event_bus or get_event_bus()

    def start_application(self, *, url: str, profile_id: int, mode: str, submit: bool) -> dict[str, Any]:
        profile = self.repo.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"profile {profile_id} does not exist")

        job = self.repo.create_job(url)
        run = self.repo.create_run(
            job_id=job.id,
            profile_id=profile_id,
            mode=mode,
            status="running",
            current_stage="job_parse",
            context_json={
                "submit": submit,
                "browser_action_index": 0,
                "patch_generated": False,
            },
        )
        self.repo.append_run_event(
            run_id=run.id,
            stage="run",
            action="created",
            payload_json={"job_id": job.id, "url": url, "mode": mode, "submit": submit},
        )
        self._emit_db_events(run.id)
        final = self.advance_run(run.id)
        return self.serialize_run(final.id)

    def advance_run(self, run_id: int) -> Any:
        while True:
            run = self.repo.get_run(run_id)
            if run is None:
                raise ValueError(f"run {run_id} not found")

            if run.status in {"waiting_approval", "waiting_captcha", "blocked", "failed", "completed"}:
                return run

            try:
                changed = self._advance_once(run)
                if not changed:
                    return self.repo.get_run(run_id)
            except Exception as exc:
                logger.exception("Run failed run_id=%s", run_id)
                self.repo.append_run_event(
                    run_id=run_id,
                    stage="run",
                    action="error",
                    payload_json={"error": str(exc)},
                )
                self.repo.update_run(
                    run_id,
                    status="failed",
                    error=str(exc),
                    current_stage="failed",
                    completed=True,
                )
                self._emit_db_events(run_id)
                return self.repo.get_run(run_id)

    def approve_event(self, *, run_id: int, event_id: int) -> dict[str, Any]:
        run = self.repo.get_run(run_id)
        if not run:
            raise ValueError(f"run {run_id} not found")

        event = self.repo.get_run_event(event_id)
        if not event or event.run_id != run_id:
            raise ValueError(f"event {event_id} does not belong to run {run_id}")

        if event.stage == "captcha":
            context = dict(run.context_json or {})
            context["captcha_solved"] = True
            self.repo.update_run(run_id, context_json=context)

        self.repo.set_event_approval(event_id, "approved")
        self.repo.append_run_event(
            run_id=run_id,
            stage=event.stage,
            action=f"approval_granted:{event.action}",
            payload_json={"event_id": event_id},
        )
        self.repo.update_run(run_id, status="running")
        self._emit_db_events(run_id)
        run = self.advance_run(run_id)
        return self.serialize_run(run.id)

    def reject_event(self, *, run_id: int, event_id: int) -> dict[str, Any]:
        run = self.repo.get_run(run_id)
        if not run:
            raise ValueError(f"run {run_id} not found")

        event = self.repo.get_run_event(event_id)
        if not event or event.run_id != run_id:
            raise ValueError(f"event {event_id} does not belong to run {run_id}")

        self.repo.set_event_approval(event_id, "rejected")
        self.repo.append_run_event(
            run_id=run_id,
            stage=event.stage,
            action=f"approval_rejected:{event.action}",
            payload_json={"event_id": event_id},
        )
        self.repo.update_run(run_id, status="blocked", current_stage="blocked", completed=True)
        self._emit_db_events(run_id)
        return self.serialize_run(run_id)

    def serialize_run(self, run_id: int) -> dict[str, Any]:
        run = self.repo.get_run(run_id)
        if not run:
            raise ValueError(f"run {run_id} not found")

        return {
            "id": run.id,
            "job_id": run.job_id,
            "profile_id": run.profile_id,
            "mode": run.mode,
            "status": run.status,
            "current_stage": run.current_stage,
            "context": run.context_json,
            "submission_url": run.submission_url,
            "error": run.error,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }

    def _advance_once(self, run) -> bool:
        policy = ModePolicy(mode=run.mode)
        context = dict(run.context_json or {})
        job = self.repo.get_job(run.job_id)
        profile = self.repo.get_profile(run.profile_id)
        if not job or not profile:
            raise ValueError("run references missing job/profile")

        if run.current_stage == "job_parse":
            if not self._approval_gate(
                run_id=run.id,
                policy=policy,
                stage="job_parsing_start",
                action="begin_job_parse",
                payload={"job_url": job.url},
            ):
                return False

            raw_text = fetch_job_text(job.url, timeout_sec=self.settings.browser_use_nav_timeout_sec)
            analysis = self.llm.analyze_job(job_url=job.url, job_text=raw_text)
            self.repo.update_job_analysis(job.id, analysis, jd_text=raw_text)
            context["job_analysis"] = analysis.model_dump()

            self.repo.update_run(run.id, current_stage="cv_tailor", context_json=context, status="running")
            self.repo.append_run_event(
                run_id=run.id,
                stage="job_parse",
                action="completed",
                payload_json=analysis.model_dump(),
            )
            self._emit_db_events(run.id)
            return True

        if run.current_stage == "cv_tailor":
            analysis = JobAnalysis.model_validate(context.get("job_analysis", {}))
            if "tailored_resume_path" not in context:
                docs = self.llm.tailor_documents(profile=profile, analysis=analysis)
                resume_path, cover_path = self._write_tailored_docs(run.id, docs.resume_markdown, docs.cover_letter_markdown)

                self.repo.save_resume_version(
                    profile_id=profile.id,
                    job_id=job.id,
                    file_path=str(resume_path),
                    markdown_snapshot=docs.resume_markdown,
                    llm_metadata_json=docs.metadata,
                )
                self.repo.save_cover_letter_version(
                    profile_id=profile.id,
                    job_id=job.id,
                    file_path=str(cover_path),
                    markdown_snapshot=docs.cover_letter_markdown,
                    llm_metadata_json=docs.metadata,
                )
                context["tailored_resume_path"] = str(resume_path)
                context["tailored_cover_letter_path"] = str(cover_path)
                self.repo.update_run(run.id, context_json=context)
                self.repo.append_run_event(
                    run_id=run.id,
                    stage="cv_tailor",
                    action="documents_generated",
                    payload_json={"resume_path": str(resume_path), "cover_letter_path": str(cover_path)},
                )
                self._emit_db_events(run.id)

            if not self._approval_gate(
                run_id=run.id,
                policy=policy,
                stage="cv_tailoring_output",
                action="approve_tailored_docs",
                payload={
                    "resume_path": context.get("tailored_resume_path"),
                    "cover_letter_path": context.get("tailored_cover_letter_path"),
                },
            ):
                return False

            self.repo.update_run(run.id, current_stage="profile_patch", context_json=context, status="running")
            self.repo.append_run_event(
                run_id=run.id,
                stage="cv_tailor",
                action="approved_or_auto",
                payload_json={},
            )
            self._emit_db_events(run.id)
            return True

        if run.current_stage == "profile_patch":
            analysis = JobAnalysis.model_validate(context.get("job_analysis", {}))

            bundle = ProfilePatchBundle.model_validate(context.get("patch_bundle", {}))
            if not context.get("patch_generated", False):
                bundle = self.llm.suggest_profile_patch(profile=profile, analysis=analysis)
                self.repo.create_ai_patch_suggestion(
                    run_id=run.id,
                    provider="local",
                    rationale=bundle.rationale,
                    patch_json=bundle.model_dump(),
                    confidence=bundle.confidence,
                    status="suggested",
                )
                context["patch_bundle"] = bundle.model_dump()
                context["patch_generated"] = True
                context.setdefault("patch_applied_indexes", [])
                self.repo.update_run(run.id, context_json=context)
                self.repo.append_run_event(
                    run_id=run.id,
                    stage="profile_patch",
                    action="patch_suggested",
                    payload_json={
                        "operation_count": len(bundle.operations),
                        "confidence": bundle.confidence,
                    },
                )
                self._emit_db_events(run.id)

            bundle = ProfilePatchBundle.model_validate(context.get("patch_bundle", {}))
            self._apply_patch_stage(run_id=run.id, policy=policy, bundle=bundle, context=context)
            run_after = self.repo.get_run(run.id)
            if run_after and run_after.status == "waiting_approval":
                return False

            self.repo.update_run(run.id, current_stage="browser_flow", context_json=context, status="running")
            self.repo.append_run_event(
                run_id=run.id,
                stage="profile_patch",
                action="applied",
                payload_json={"applied_count": len(context.get("patch_applied_indexes", []))},
            )
            self._emit_db_events(run.id)
            return True

        if run.current_stage == "browser_flow":
            actions = [
                "start_session",
                "fill_personal_info",
                "fill_work_history",
                "fill_compliance",
                "upload_resume",
                "submit_application",
            ]
            idx = int(context.get("browser_action_index", 0))

            while idx < len(actions):
                action = actions[idx]
                stage = self._stage_for_browser_action(action)
                if not self._approval_gate(
                    run_id=run.id,
                    policy=policy,
                    stage=stage,
                    action=f"approve:{action}",
                    payload={"action": action},
                ):
                    return False

                result = self.browser.execute_action(
                    BrowserContext(
                        run_id=run.id,
                        job_url=job.url,
                        profile_id=profile.id,
                        submit=bool(context.get("submit", False)),
                        captcha_solved=bool(context.get("captcha_solved", False)),
                    ),
                    action,
                )

                if result.status == "waiting_captcha":
                    self.repo.append_run_event(
                        run_id=run.id,
                        stage="captcha",
                        action="human_solve",
                        payload_json={"message": result.message},
                        requires_approval=True,
                        approval_state="pending",
                    )
                    self.repo.update_run(run.id, status="waiting_captcha", context_json=context)
                    self._emit_db_events(run.id)
                    return False

                if result.status == "failed":
                    self.repo.append_run_event(
                        run_id=run.id,
                        stage=stage,
                        action=f"failed:{action}",
                        payload_json={"message": result.message},
                    )
                    self.repo.update_run(
                        run.id,
                        status="failed",
                        current_stage="failed",
                        error=result.message,
                        completed=True,
                    )
                    self._emit_db_events(run.id)
                    return False

                self.repo.append_run_event(
                    run_id=run.id,
                    stage=stage,
                    action=f"completed:{action}",
                    payload_json={"message": result.message},
                )
                for field in result.fields:
                    self.repo.record_field_fill(
                        run_id=run.id,
                        page_url=job.url,
                        field=field,
                        fill_status="filled",
                    )

                idx += 1
                context["browser_action_index"] = idx
                self.repo.update_run(run.id, context_json=context)
                self._emit_db_events(run.id)

            confirmation_ref = f"RUN-{run.id}-{int(datetime.now(UTC).timestamp())}"
            self.repo.create_submission(
                run_id=run.id,
                confirmation_text="Application flow completed",
                confirmation_ref=confirmation_ref,
                screenshot_path="",
            )
            self.repo.update_run(
                run.id,
                status="completed",
                current_stage="completed",
                completed=True,
                submission_url=job.url,
            )
            self.repo.append_run_event(
                run_id=run.id,
                stage="run",
                action="completed",
                payload_json={"confirmation_ref": confirmation_ref},
            )
            self._emit_db_events(run.id)
            return True

        return False

    def _apply_patch_stage(
        self,
        *,
        run_id: int,
        policy: ModePolicy,
        bundle: ProfilePatchBundle,
        context: dict[str, Any],
    ) -> None:
        run = self.repo.get_run(run_id)
        if not run:
            raise ValueError(f"run {run_id} not found")

        applied = set(int(v) for v in context.get("patch_applied_indexes", []))

        if run.mode == "strict":
            for idx, operation in enumerate(bundle.operations):
                if idx in applied:
                    continue

                if not self._approval_gate(
                    run_id=run_id,
                    policy=policy,
                    stage="db_patch_apply",
                    action=f"patch_op:{idx}",
                    payload=operation.model_dump(),
                ):
                    return

                self.repo.apply_patch_operation(run.profile_id, operation)
                applied.add(idx)
                self.repo.append_run_event(
                    run_id=run_id,
                    stage="db_patch_apply",
                    action=f"applied_patch_op:{idx}",
                    payload_json=operation.model_dump(),
                )
                context["patch_applied_indexes"] = sorted(applied)
                self.repo.update_run(run_id, context_json=context)
                self._emit_db_events(run_id)
            return

        if run.mode == "medium":
            if context.get("patch_batch_applied"):
                return
            if not self._approval_gate(
                run_id=run_id,
                policy=policy,
                stage="db_patch_apply",
                action="patch_batch",
                payload={"operation_count": len(bundle.operations)},
            ):
                return

            for idx, operation in enumerate(bundle.operations):
                self.repo.apply_patch_operation(run.profile_id, operation)
                applied.add(idx)
            context["patch_applied_indexes"] = sorted(applied)
            context["patch_batch_applied"] = True
            self.repo.update_run(run_id, context_json=context)
            self._emit_db_events(run_id)
            return

        for idx, operation in enumerate(bundle.operations):
            if idx in applied:
                continue
            self.repo.apply_patch_operation(run.profile_id, operation)
            applied.add(idx)
        context["patch_applied_indexes"] = sorted(applied)
        context["patch_batch_applied"] = True
        self.repo.update_run(run_id, context_json=context)
        self._emit_db_events(run_id)

    def _approval_gate(
        self,
        *,
        run_id: int,
        policy: ModePolicy,
        stage: str,
        action: str,
        payload: dict[str, Any],
    ) -> bool:
        if not policy.requires_approval(stage):
            return True

        rejected = self.repo.get_approval_event(run_id, stage, action, "rejected")
        if rejected:
            self.repo.update_run(run_id, status="blocked", current_stage="blocked", completed=True)
            self._emit_db_events(run_id)
            return False

        approved = self.repo.get_approval_event(run_id, stage, action, "approved")
        if approved:
            return True

        pending = self.repo.get_approval_event(run_id, stage, action, "pending")
        if pending:
            self.repo.update_run(run_id, status="waiting_approval")
            self._emit_db_events(run_id)
            return False

        self.repo.append_run_event(
            run_id=run_id,
            stage=stage,
            action=action,
            payload_json=payload,
            requires_approval=True,
            approval_state="pending",
        )
        self.repo.update_run(run_id, status="waiting_approval")
        self._emit_db_events(run_id)
        return False

    def _emit_db_events(self, run_id: int) -> None:
        events = self.repo.list_run_events(run_id)
        if not events:
            return
        latest = events[-1]
        payload = {
            "event_id": latest.id,
            "run_id": latest.run_id,
            "stage": latest.stage,
            "action": latest.action,
            "payload": latest.payload_json,
            "requires_approval": latest.requires_approval,
            "approval_state": latest.approval_state,
            "created_at": latest.created_at.isoformat() if latest.created_at else None,
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.event_bus.publish(run_id, payload))
        else:
            loop.create_task(self.event_bus.publish(run_id, payload))

    def _stage_for_browser_action(self, action: str) -> str:
        if action == "start_session":
            return "start_browser_session"
        if action.startswith("fill_"):
            return "fill_required_section"
        if action == "upload_resume":
            return "file_upload"
        if action == "submit_application":
            return "final_submit"
        return "browser"

    def _write_tailored_docs(self, run_id: int, resume_md: str, cover_md: str) -> tuple[Path, Path]:
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        resume_path = self.settings.resume_dir / f"run_{run_id}_{ts}.md"
        cover_path = self.settings.cover_letter_dir / f"run_{run_id}_{ts}.md"
        resume_path.parent.mkdir(parents=True, exist_ok=True)
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        resume_path.write_text(resume_md, encoding="utf-8")
        cover_path.write_text(cover_md, encoding="utf-8")
        return resume_path, cover_path
