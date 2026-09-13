"""Acceptance tests for deterministic cloud validation manifests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bridge.cloud_fulfillment_contracts import ForgeImagesValidationRequestV1
from bridge.cloud_fulfillment_manifest import ForgeImagesAssetManifestV1
from bridge.cloud_fulfillment_validation import DeterministicCloudAssetValidator


FIXED_TIME = datetime(2026, 9, 13, 7, 0, tzinfo=timezone.utc)


def validation_request() -> ForgeImagesValidationRequestV1:
    return ForgeImagesValidationRequestV1.model_validate(
        {
            "schema_version": "forgeimages_validation_request.v1",
            "correlation_id": "corr-manifest-001",
            "idempotency_key": "idem-manifest-001",
            "source_service": "neuroforge",
            "target_service": "forgeimages",
            "created_at": FIXED_TIME,
            "source_request_id": "request-manifest-001",
            "job_id": "job-manifest-001",
            "app_id": "pressforge",
            "use_case": "social_image",
            "validation_profile": "pressforge_social_image",
            "requested_final_count": 2,
            "candidate_artifacts": [
                {
                    "artifact_id": "artifact-b",
                    "candidate_id": "candidate-b",
                    "artifact_uri": (
                        "nf-artifact://cloud-image/job-manifest-001/artifact-b"
                    ),
                    "mime_type": "image/png",
                    "width": 1080,
                    "height": 1080,
                },
                {
                    "artifact_id": "artifact-a",
                    "candidate_id": "candidate-a",
                    "artifact_uri": (
                        "nf-artifact://cloud-image/job-manifest-001/artifact-a"
                    ),
                    "mime_type": "image/jpeg",
                    "width": 1080,
                    "height": 1080,
                },
            ],
            "template_id": "panel-square",
            "constraints": {},
        }
    )


def test_manifest_hash_deterministic() -> None:
    service = DeterministicCloudAssetValidator(clock=lambda: FIXED_TIME)

    first = service.validate(validation_request())
    second = service.validate(validation_request())

    assert first.result.validation_id == second.result.validation_id
    assert first.manifest.manifest_sha256 == second.manifest.manifest_sha256
    assert first.manifest.accepted_artifact_ids == ["artifact-a", "artifact-b"]


def test_manifest_json_round_trip_verifies_hash() -> None:
    manifest = (
        DeterministicCloudAssetValidator(clock=lambda: FIXED_TIME)
        .validate(validation_request())
        .manifest
    )

    decoded = ForgeImagesAssetManifestV1.model_validate_json(manifest.model_dump_json())

    assert decoded == manifest
    assert len(decoded.manifest_sha256) == 64


def test_manifest_rejects_tampered_content() -> None:
    manifest = (
        DeterministicCloudAssetValidator(clock=lambda: FIXED_TIME)
        .validate(validation_request())
        .manifest
    )
    payload = manifest.model_dump(mode="json")
    payload["source_job_id"] = "job-tampered"

    with pytest.raises(ValidationError, match="manifest_sha256"):
        ForgeImagesAssetManifestV1.model_validate(payload)


def test_manifest_records_validation_lineage() -> None:
    output = DeterministicCloudAssetValidator(clock=lambda: FIXED_TIME).validate(
        validation_request()
    )

    assert output.manifest.validation_id == output.result.validation_id
    assert output.manifest.source_job_id == output.result.job_id
    assert output.manifest.validation_profile == "pressforge_social_image"
    assert output.manifest.template_id == "panel-square"
    assert output.manifest.rejected_artifact_ids == []
    assert output.manifest.compiled_asset_ids == []
    assert output.manifest.export_variants == []
