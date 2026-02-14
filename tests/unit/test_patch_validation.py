import pytest
from pydantic import ValidationError

from vulture.types import PatchOperation, ProfilePatchBundle


def test_patch_operation_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        PatchOperation(
            table="skills",
            operation="upsert",
            key={},
            values={"name": "Python"},
            source="llm",
            confidence=1.1,
        )


def test_patch_bundle_accepts_valid_operations() -> None:
    operation = PatchOperation(
        table="profile_preferences",
        operation="upsert",
        key={},
        values={"remote_pref": "remote"},
        source="llm",
        confidence=0.8,
    )
    bundle = ProfilePatchBundle(rationale="match remote requirement", operations=[operation], confidence=0.8)
    assert len(bundle.operations) == 1
