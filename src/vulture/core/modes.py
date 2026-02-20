from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RunMode = Literal["strict", "medium", "yolo"]


@dataclass(slots=True)
class ModePolicy:
    mode: RunMode

    def requires_approval(self, stage: str) -> bool:
        if stage == "captcha":
            return True

        if self.mode == "strict":
            return stage in {
                "job_parsing_start",
                "cv_tailoring_output",
                "db_patch_apply",
                "question_review_required",
                "start_browser_session",
                "fill_required_section",
                "file_upload",
                "final_submit",
            }

        if self.mode == "medium":
            return stage in {
                "cv_tailoring_output",
                "db_patch_apply",
                "question_review_required",
                "fill_required_section",
                "file_upload",
                "final_submit",
            }

        if self.mode == "yolo":
            return stage == "captcha"

        raise ValueError(f"unsupported run mode '{self.mode}'")
