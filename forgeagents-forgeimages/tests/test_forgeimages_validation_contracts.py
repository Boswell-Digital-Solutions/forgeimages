"""Acceptance tests for ForgeImages cloud-fulfillment validation contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bridge.cloud_fulfillment_contracts import (
    FORGEIMAGES_VALIDATION_REQUEST_SCHEMA_V1,
    FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
    ForgeImagesValidationRequestV1,
    ForgeImagesValidationResultV1,
)


def candidate_payload() -> dict[str, object]:
    return {
        "artifact_id": "artifact-001",
        "candidate_id": "candidate-001",
        "artifact_uri": "nf-artifact://cloud-image/job-001/artifact-001",
        "mime_type": "image/png",
        "width": 1536,
        "height": 1024,
    }


def request_payload() -> dict[str, object]:
    return {
        "schema_version": FORGEIMAGES_VALIDATION_REQUEST_SCHEMA_V1,
        "correlation_id": "corr-001",
        "idempotency_key": "idem-validation-001",
        "source_service": "neuroforge",
        "target_service": "forgeimages",
        "created_at": datetime.now(timezone.utc),
        "source_request_id": "request-001",
        "job_id": "job-001",
        "app_id": "authorforge",
        "use_case": "book_cover_concept",
        "validation_profile": "authorforge_cover_concept",
        "requested_final_count": 1,
        "candidate_artifacts": [candidate_payload()],
        "template_id": "book-cover-kdp",
        "constraints": {"text_free": True},
    }


def result_payload() -> dict[str, object]:
    return {
        "schema_version": FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
        "correlation_id": "corr-001",
        "idempotency_key": "idem-validation-result-001",
        "source_service": "forgeimages",
        "target_service": "neuroforge",
        "created_at": datetime.now(timezone.utc),
        "validation_id": "validation-001",
        "source_request_id": "request-001",
        "job_id": "job-001",
        "accepted_count": 1,
        "rejected_count": 0,
        "accepted_artifacts": [candidate_payload()],
        "rejected_artifacts": [],
        "replacement_required": False,
        "replacement_count": 0,
        "compiled_assets": [
            {
                "asset_id": "asset-001",
                "asset_uri": "fi-asset://compiled/validation-001/asset-001",
                "thumbnail_uri": None,
            }
        ],
        "manifest_uri": "fi-asset://compiled/validation-001/manifest",
    }


def test_validation_request_requires_schema_version() -> None:
    payload = request_payload()
    payload.pop("schema_version")

    with pytest.raises(ValidationError):
        ForgeImagesValidationRequestV1.model_validate(payload)


def test_validation_result_requires_schema_version() -> None:
    payload = result_payload()
    payload.pop("schema_version")

    with pytest.raises(ValidationError):
        ForgeImagesValidationResultV1.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "correlation_id",
        "idempotency_key",
        "source_service",
        "target_service",
        "created_at",
    ],
)
def test_contract_schema_required_fields(field: str) -> None:
    payload = request_payload()
    payload.pop(field)

    with pytest.raises(ValidationError):
        ForgeImagesValidationRequestV1.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "payload", "invalid_version"),
    [
        (
            ForgeImagesValidationRequestV1,
            request_payload,
            "forgeimages_validation_request.v2",
        ),
        (
            ForgeImagesValidationResultV1,
            result_payload,
            "forgeimages_validation_result.v2",
        ),
    ],
)
def test_unknown_schema_version_fails_closed(model, payload, invalid_version) -> None:
    invalid_payload = payload()
    invalid_payload["schema_version"] = invalid_version

    with pytest.raises(ValidationError):
        model.model_validate(invalid_payload)


def test_cross_repo_contract_round_trip() -> None:
    request = ForgeImagesValidationRequestV1.model_validate(request_payload())
    encoded = request.model_dump_json()

    decoded = ForgeImagesValidationRequestV1.model_validate_json(encoded)

    assert decoded == request
    assert decoded.source_service == "neuroforge"
    assert decoded.target_service == "forgeimages"
    assert decoded.candidate_artifacts[0].artifact_uri.startswith("nf-artifact://")


def test_result_count_invariants_fail_closed() -> None:
    payload = result_payload()
    payload["accepted_count"] = 0

    with pytest.raises(ValidationError, match="accepted_count"):
        ForgeImagesValidationResultV1.model_validate(payload)


def test_contract_rejects_naive_timestamp() -> None:
    payload = request_payload()
    payload["created_at"] = datetime.now()

    with pytest.raises(ValidationError, match="timezone"):
        ForgeImagesValidationRequestV1.model_validate(payload)


def test_contract_rejects_unexpected_fields() -> None:
    payload = request_payload()
    payload["provider_id"] = "not-a-public-contract-field"

    with pytest.raises(ValidationError):
        ForgeImagesValidationRequestV1.model_validate(payload)
