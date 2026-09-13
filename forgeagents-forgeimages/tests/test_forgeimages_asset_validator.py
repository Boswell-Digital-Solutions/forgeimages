"""Acceptance tests for deterministic cloud candidate validation."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bridge.cloud_fulfillment_contracts import (
    ForgeImagesRejectionCode,
    ForgeImagesValidationRequestV1,
    RejectionSeverity,
)
from bridge.cloud_fulfillment_validation import (
    CandidateTestMetadataForbidden,
    CandidateValidationMetadata,
    DeterministicCloudAssetValidator,
)


FIXED_TIME = datetime(2026, 9, 13, 7, 0, tzinfo=timezone.utc)


def candidate_payload(
    artifact_id: str = "artifact-001",
    *,
    candidate_id: str = "candidate-001",
    mime_type: str = "image/png",
    width: int = 1200,
    height: int = 1800,
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "candidate_id": candidate_id,
        "artifact_uri": f"nf-artifact://cloud-image/job-001/{artifact_id}",
        "mime_type": mime_type,
        "width": width,
        "height": height,
    }


def request_with_candidates(
    candidates: list[dict[str, object]],
) -> ForgeImagesValidationRequestV1:
    return ForgeImagesValidationRequestV1.model_validate(
        {
            "schema_version": "forgeimages_validation_request.v1",
            "correlation_id": "corr-validator-001",
            "idempotency_key": "idem-validator-001",
            "source_service": "neuroforge",
            "target_service": "forgeimages",
            "created_at": FIXED_TIME,
            "source_request_id": "request-001",
            "job_id": "job-001",
            "app_id": "authorforge",
            "use_case": "book_cover_concept",
            "validation_profile": "authorforge_cover_concept",
            "requested_final_count": len(candidates),
            "candidate_artifacts": candidates,
            "template_id": "book-cover-kdp",
            "constraints": {},
        }
    )


def validator(*, allow_test_metadata: bool = False) -> DeterministicCloudAssetValidator:
    return DeterministicCloudAssetValidator(
        clock=lambda: FIXED_TIME,
        allow_test_metadata=allow_test_metadata,
    )


def test_valid_artifacts_are_accepted() -> None:
    output = validator().validate(request_with_candidates([candidate_payload()]))

    assert output.result.accepted_count == 1
    assert output.result.rejected_count == 0
    assert output.result.accepted_artifacts[0].artifact_id == "artifact-001"
    assert not output.result.replacement_required
    assert output.result.manifest_uri is None


def test_bad_aspect_ratio_rejected() -> None:
    request = request_with_candidates([candidate_payload(width=1600, height=1600)])

    output = validator().validate(request)

    assert output.result.accepted_count == 0
    assert output.result.rejected_count == 1
    assert (
        output.result.rejected_artifacts[0].rejection_code
        is ForgeImagesRejectionCode.ASPECT_RATIO_INVALID
    )


def test_low_resolution_rejected() -> None:
    request = request_with_candidates([candidate_payload(width=800, height=1200)])

    output = validator().validate(request)

    assert (
        output.result.rejected_artifacts[0].rejection_code
        is ForgeImagesRejectionCode.RESOLUTION_TOO_LOW
    )


def test_unsupported_mime_type_rejected() -> None:
    request = request_with_candidates([candidate_payload(mime_type="image/webp")])

    output = validator().validate(request)

    assert (
        output.result.rejected_artifacts[0].rejection_code
        is ForgeImagesRejectionCode.UNSUPPORTED_FORMAT
    )


def test_force_reject_metadata_rejected() -> None:
    request = request_with_candidates([candidate_payload()])
    metadata = {
        "artifact-001": CandidateValidationMetadata(
            force_reject=True,
            force_rejection_code=ForgeImagesRejectionCode.BRAND_LAYOUT_FAILED,
            replacement_guidance=("Reserve the lower third for brand marks.",),
        )
    }

    output = validator(allow_test_metadata=True).validate(
        request, test_metadata=metadata
    )

    rejection = output.result.rejected_artifacts[0]
    assert rejection.rejection_code is ForgeImagesRejectionCode.BRAND_LAYOUT_FAILED
    assert rejection.replacement_guidance == [
        "Reserve the lower third for brand marks."
    ]


def test_production_validator_rejects_test_metadata() -> None:
    request = request_with_candidates([candidate_payload()])

    with pytest.raises(CandidateTestMetadataForbidden):
        validator().validate(
            request,
            test_metadata={
                "artifact-001": CandidateValidationMetadata(force_reject=True)
            },
        )


def test_replacement_count_equals_hard_fail_count() -> None:
    candidates = [
        candidate_payload(),
        candidate_payload("artifact-002", candidate_id="candidate-002"),
    ]
    metadata = {
        "artifact-001": CandidateValidationMetadata(
            force_reject=True,
            force_rejection_severity=RejectionSeverity.HARD_FAIL,
        ),
        "artifact-002": CandidateValidationMetadata(
            force_reject=True,
            force_rejection_severity=RejectionSeverity.SOFT_FAIL,
        ),
    }

    output = validator(allow_test_metadata=True).validate(
        request_with_candidates(candidates), test_metadata=metadata
    )

    assert output.result.rejected_count == 2
    assert output.result.replacement_count == 1
    assert output.result.replacement_required


@pytest.mark.parametrize(
    ("metadata", "expected_code"),
    [
        (
            CandidateValidationMetadata(safe_zone_passed=False),
            ForgeImagesRejectionCode.SAFE_ZONE_FAILED,
        ),
        (
            CandidateValidationMetadata(crop_viable=False),
            ForgeImagesRejectionCode.CROP_NOT_VIABLE,
        ),
    ],
)
def test_optional_placeholder_rules(
    metadata: CandidateValidationMetadata,
    expected_code: ForgeImagesRejectionCode,
) -> None:
    output = validator(allow_test_metadata=True).validate(
        request_with_candidates([candidate_payload()]),
        test_metadata={"artifact-001": metadata},
    )

    assert output.result.rejected_artifacts[0].rejection_code is expected_code


def test_forgeimages_has_no_cloud_provider_imports() -> None:
    bridge_dir = Path(__file__).parents[1] / "bridge"
    module_paths = [
        bridge_dir / "cloud_fulfillment_profiles.py",
        bridge_dir / "cloud_fulfillment_manifest.py",
        bridge_dir / "cloud_fulfillment_validation.py",
    ]
    imported_roots: set[str] = set()
    for module_path in module_paths:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported_roots.update(
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        imported_roots.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )

    forbidden_roots = {"open" + "ai", "google", "x" + "ai"}
    assert imported_roots.isdisjoint(forbidden_roots)
