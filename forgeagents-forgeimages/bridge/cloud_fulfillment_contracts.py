"""Versioned contracts for NeuroForge-to-ForgeImages asset validation.

Only the request and result are top-level cross-service payloads, so they carry
the required transport envelope. Candidate, rejection, and compiled-asset
records are nested values within those payloads and deliberately mirror the
NeuroForge v1 field names.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


FORGEIMAGES_VALIDATION_REQUEST_SCHEMA_V1 = "forgeimages_validation_request.v1"
FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1 = "forgeimages_validation_result.v1"


class StrictContractModel(BaseModel):
    """Reject ungoverned fields at the service boundary."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class CrossServiceContract(StrictContractModel):
    """Transport metadata required on every top-level service payload."""

    schema_version: str = Field(..., min_length=1, max_length=128)
    correlation_id: str = Field(..., min_length=1, max_length=256)
    idempotency_key: str = Field(..., min_length=1, max_length=256)
    source_service: str = Field(..., min_length=1, max_length=128)
    target_service: str = Field(..., min_length=1, max_length=128)
    created_at: datetime

    @field_validator(
        "schema_version",
        "correlation_id",
        "idempotency_key",
        "source_service",
        "target_service",
    )
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        """Normalize envelope identifiers and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject ambiguous timestamps and normalize accepted values to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value.astimezone(timezone.utc)


class ForgeImagesRejectionCode(str, Enum):
    """Stable, machine-readable production validation rejection codes."""

    SAFE_ZONE_FAILED = "safe_zone_failed"
    ASPECT_RATIO_INVALID = "aspect_ratio_invalid"
    RESOLUTION_TOO_LOW = "resolution_too_low"
    SUBJECT_CUTOFF = "subject_cutoff"
    SUBJECT_TOO_CLOSE_TO_EDGE = "subject_too_close_to_edge"
    TEMPLATE_SLOT_FAILED = "template_slot_failed"
    TEXT_AREA_BLOCKED = "text_area_blocked"
    UNWANTED_TEXT_PRESENT = "unwanted_text_present"
    CROP_NOT_VIABLE = "crop_not_viable"
    COMPOSITION_NOT_ASSET_READY = "composition_not_asset_ready"
    BRAND_LAYOUT_FAILED = "brand_layout_failed"
    FILE_DECODE_FAILED = "file_decode_failed"
    UNSUPPORTED_FORMAT = "unsupported_format"
    TRANSPARENCY_REQUIRED_MISSING = "transparency_required_missing"
    UNKNOWN_VALIDATION_FAILURE = "unknown_validation_failure"


class RejectionSeverity(str, Enum):
    """Whether a replacement may correct a rejected candidate."""

    SOFT_FAIL = "soft_fail"
    HARD_FAIL = "hard_fail"


class CandidateArtifactRefV1(StrictContractModel):
    """A NeuroForge-owned candidate artifact submitted for validation."""

    artifact_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    artifact_uri: str = Field(..., min_length=1)
    mime_type: str = Field(..., min_length=1)
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)


class CompiledAssetSummaryV1(StrictContractModel):
    """A service-owned production asset returned after compilation."""

    asset_id: str = Field(..., min_length=1)
    asset_uri: str = Field(..., min_length=1)
    thumbnail_uri: str | None = None


class ForgeImagesRejectedArtifactV1(StrictContractModel):
    """Structured rejection details suitable for a replacement request."""

    artifact_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    rejection_code: ForgeImagesRejectionCode
    severity: RejectionSeverity
    human_reason: str = Field(..., min_length=1)
    machine_reason: str = Field(..., min_length=1)
    replacement_guidance: list[str] = Field(default_factory=list)
    template_id: str | None = None
    validation_profile: str = Field(..., min_length=1)


class ForgeImagesValidationRequestV1(CrossServiceContract):
    """NeuroForge request for deterministic production validation."""

    schema_version: Literal["forgeimages_validation_request.v1"]
    source_service: Literal["neuroforge"]
    target_service: Literal["forgeimages"]
    source_request_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)
    app_id: str = Field(..., min_length=1)
    use_case: str = Field(..., min_length=1)
    validation_profile: str = Field(..., min_length=1)
    requested_final_count: int = Field(..., ge=1, le=12)
    candidate_artifacts: list[CandidateArtifactRefV1] = Field(..., min_length=1)
    template_id: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class ForgeImagesValidationResultV1(CrossServiceContract):
    """ForgeImages validation and compilation outcome returned to NeuroForge."""

    schema_version: Literal["forgeimages_validation_result.v1"]
    source_service: Literal["forgeimages"]
    target_service: Literal["neuroforge"]
    validation_id: str = Field(..., min_length=1)
    source_request_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)
    accepted_count: int = Field(..., ge=0)
    rejected_count: int = Field(..., ge=0)
    accepted_artifacts: list[CandidateArtifactRefV1] = Field(default_factory=list)
    rejected_artifacts: list[ForgeImagesRejectedArtifactV1] = Field(
        default_factory=list
    )
    replacement_required: bool
    replacement_count: int = Field(..., ge=0)
    compiled_assets: list[CompiledAssetSummaryV1] = Field(default_factory=list)
    manifest_uri: str | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> "ForgeImagesValidationResultV1":
        """Keep summary counts synchronized with their governed record lists."""
        if self.accepted_count != len(self.accepted_artifacts):
            raise ValueError("accepted_count must match accepted_artifacts")
        if self.rejected_count != len(self.rejected_artifacts):
            raise ValueError("rejected_count must match rejected_artifacts")
        if self.replacement_required != (self.replacement_count > 0):
            raise ValueError("replacement_required must match replacement_count")
        return self
