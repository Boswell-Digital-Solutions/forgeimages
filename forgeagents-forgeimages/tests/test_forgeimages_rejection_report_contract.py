"""Acceptance tests for ForgeImages structured rejection reports."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from bridge.cloud_fulfillment_contracts import (
    FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
    ForgeImagesRejectedArtifactV1,
    ForgeImagesRejectionCode,
    ForgeImagesValidationResultV1,
    RejectionSeverity,
)


def rejected_artifact_payload() -> dict[str, object]:
    return {
        "artifact_id": "artifact-002",
        "candidate_id": "candidate-002",
        "rejection_code": "safe_zone_failed",
        "severity": "soft_fail",
        "human_reason": "The subject crosses the title safe zone.",
        "machine_reason": "subject_bounds_intersect:title_safe_zone",
        "replacement_guidance": ["Keep the upper third clear for title text."],
        "template_id": "book-cover-kdp",
        "validation_profile": "authorforge_cover_concept",
    }


def rejection_result_payload() -> dict[str, object]:
    return {
        "schema_version": FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
        "correlation_id": "corr-rejection-001",
        "idempotency_key": "idem-rejection-001",
        "source_service": "forgeimages",
        "target_service": "neuroforge",
        "created_at": datetime.now(timezone.utc),
        "validation_id": "validation-002",
        "source_request_id": "request-001",
        "job_id": "job-001",
        "accepted_count": 0,
        "rejected_count": 1,
        "accepted_artifacts": [],
        "rejected_artifacts": [rejected_artifact_payload()],
        "replacement_required": True,
        "replacement_count": 1,
        "compiled_assets": [],
        "manifest_uri": None,
    }


def test_rejected_artifact_requires_rejection_code() -> None:
    payload = rejected_artifact_payload()
    payload.pop("rejection_code")

    with pytest.raises(ValidationError):
        ForgeImagesRejectedArtifactV1.model_validate(payload)


def test_unknown_rejection_code_fail_closed() -> None:
    payload = rejected_artifact_payload()
    payload["rejection_code"] = "peer_added_without_contract_version"

    with pytest.raises(ValidationError):
        ForgeImagesRejectedArtifactV1.model_validate(payload)


def test_rejection_report_json_round_trip() -> None:
    result = ForgeImagesValidationResultV1.model_validate(rejection_result_payload())
    encoded = result.model_dump_json()

    decoded = ForgeImagesValidationResultV1.model_validate_json(encoded)

    assert decoded == result
    rejection = decoded.rejected_artifacts[0]
    assert rejection.rejection_code is ForgeImagesRejectionCode.SAFE_ZONE_FAILED
    assert rejection.severity is RejectionSeverity.SOFT_FAIL
    assert decoded.replacement_required
    assert decoded.replacement_count == 1


def test_all_governed_rejection_codes_are_stable() -> None:
    assert {code.value for code in ForgeImagesRejectionCode} == {
        "safe_zone_failed",
        "aspect_ratio_invalid",
        "resolution_too_low",
        "subject_cutoff",
        "subject_too_close_to_edge",
        "template_slot_failed",
        "text_area_blocked",
        "unwanted_text_present",
        "crop_not_viable",
        "composition_not_asset_ready",
        "brand_layout_failed",
        "file_decode_failed",
        "unsupported_format",
        "transparency_required_missing",
        "unknown_validation_failure",
    }


def test_contracts_import_without_cloud_provider_dependencies() -> None:
    module_path = (
        Path(__file__).parents[1] / "bridge" / "cloud_fulfillment_contracts.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    forbidden_roots = {"open" + "ai", "google", "x" + "ai"}

    assert imported_roots.isdisjoint(forbidden_roots)
