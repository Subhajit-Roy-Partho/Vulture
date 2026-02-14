from vulture.core.modes import ModePolicy


def test_strict_requires_all_major_stage_approvals() -> None:
    policy = ModePolicy(mode="strict")
    assert policy.requires_approval("job_parsing_start")
    assert policy.requires_approval("cv_tailoring_output")
    assert policy.requires_approval("db_patch_apply")
    assert policy.requires_approval("start_browser_session")
    assert policy.requires_approval("fill_required_section")
    assert policy.requires_approval("file_upload")
    assert policy.requires_approval("final_submit")


def test_medium_requires_stage_level_approvals_only() -> None:
    policy = ModePolicy(mode="medium")
    assert not policy.requires_approval("job_parsing_start")
    assert policy.requires_approval("cv_tailoring_output")
    assert policy.requires_approval("db_patch_apply")
    assert not policy.requires_approval("start_browser_session")


def test_yolo_requires_only_captcha() -> None:
    policy = ModePolicy(mode="yolo")
    assert not policy.requires_approval("final_submit")
    assert policy.requires_approval("captcha")
