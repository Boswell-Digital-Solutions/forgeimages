"""Deterministic metadata validation for cloud image candidate contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ConfigDict

from .cloud_fulfillment_contracts import (
    FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
    CandidateArtifactRefV1,
    ForgeImagesRejectedArtifactV1,
    ForgeImagesRejectionCode,
    ForgeImagesValidationRequestV1,
    ForgeImagesValidationResultV1,
    RejectionSeverity,
    StrictContractModel,
)
from .cloud_fulfillment_manifest import ForgeImagesAssetManifestV1
from .cloud_fulfillment_profiles import (
    DEFAULT_FORGEIMAGES_VALIDATION_PROFILES,
    ForgeImagesValidationProfile,
    ForgeImagesValidationProfileRegistry,
)


class CandidateValidationMetadata(StrictContractModel):
    """Controlled signals used by placeholder rules and deterministic tests."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=(), frozen=True)

    force_reject: bool = False
    force_rejection_code: ForgeImagesRejectionCode = (
        ForgeImagesRejectionCode.UNKNOWN_VALIDATION_FAILURE
    )
    force_rejection_severity: RejectionSeverity = RejectionSeverity.HARD_FAIL
    replacement_guidance: tuple[str, ...] = ()
    safe_zone_passed: bool | None = None
    crop_viable: bool | None = None


class CandidateTestMetadataForbidden(ValueError):
    """Raised when production-configured validation receives test hooks."""


@dataclass(frozen=True, slots=True)
class CloudAssetValidationOutput:
    """Offline Slice 02 result and its deterministic inline manifest."""

    result: ForgeImagesValidationResultV1
    manifest: ForgeImagesAssetManifestV1


class DeterministicCloudAssetValidator:
    """Validate candidate metadata without network, file, or provider access."""

    def __init__(
        self,
        *,
        profiles: ForgeImagesValidationProfileRegistry = (
            DEFAULT_FORGEIMAGES_VALIDATION_PROFILES
        ),
        clock: Callable[[], datetime] | None = None,
        allow_test_metadata: bool = False,
    ) -> None:
        self._profiles = profiles
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._allow_test_metadata = allow_test_metadata

    def validate(
        self,
        request: ForgeImagesValidationRequestV1,
        *,
        test_metadata: Mapping[str, CandidateValidationMetadata] | None = None,
    ) -> CloudAssetValidationOutput:
        """Return deterministic accepted/rejected records and a manifest."""
        metadata = dict(test_metadata or {})
        if metadata and not self._allow_test_metadata:
            raise CandidateTestMetadataForbidden(
                "test metadata is disabled for this validator instance"
            )

        artifact_ids = [item.artifact_id for item in request.candidate_artifacts]
        candidate_ids = [item.candidate_id for item in request.candidate_artifacts]
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("candidate artifact_id values must be unique")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate_id values must be unique")
        unknown_metadata_ids = set(metadata).difference(artifact_ids)
        if unknown_metadata_ids:
            raise ValueError("test metadata references an unknown artifact_id")

        profile = self._profiles.require(request.validation_profile)
        accepted: list[CandidateArtifactRefV1] = []
        rejected: list[ForgeImagesRejectedArtifactV1] = []

        for artifact in request.candidate_artifacts:
            rejection = self._validate_artifact(
                artifact,
                profile,
                request,
                metadata.get(artifact.artifact_id),
            )
            if rejection is None:
                accepted.append(artifact)
            else:
                rejected.append(rejection)

        validation_id = self._validation_id(request)
        manifest = ForgeImagesAssetManifestV1.create(
            validation_id=validation_id,
            source_job_id=request.job_id,
            accepted_artifact_ids=[item.artifact_id for item in accepted],
            rejected_artifact_ids=[item.artifact_id for item in rejected],
            template_id=request.template_id,
            validation_profile=request.validation_profile,
        )
        replacement_count = sum(
            item.severity is RejectionSeverity.HARD_FAIL for item in rejected
        )
        created_at = self._clock()
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("validator clock must return a timezone-aware datetime")

        result = ForgeImagesValidationResultV1(
            schema_version=FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
            correlation_id=request.correlation_id,
            idempotency_key=self._result_idempotency_key(request.idempotency_key),
            source_service="forgeimages",
            target_service="neuroforge",
            created_at=created_at.astimezone(timezone.utc),
            validation_id=validation_id,
            source_request_id=request.source_request_id,
            job_id=request.job_id,
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            accepted_artifacts=accepted,
            rejected_artifacts=rejected,
            replacement_required=replacement_count > 0,
            replacement_count=replacement_count,
            compiled_assets=[],
            manifest_uri=None,
        )
        return CloudAssetValidationOutput(result=result, manifest=manifest)

    @staticmethod
    def _validation_id(request: ForgeImagesValidationRequestV1) -> str:
        identity = {
            "idempotency_key": request.idempotency_key,
            "job_id": request.job_id,
            "source_request_id": request.source_request_id,
            "artifact_ids": sorted(
                item.artifact_id for item in request.candidate_artifacts
            ),
        }
        canonical = json.dumps(identity, separators=(",", ":"), sort_keys=True)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"fi-validation-{digest[:32]}"

    @staticmethod
    def _result_idempotency_key(source_key: str) -> str:
        digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
        return f"fi-result-{digest}"

    def _validate_artifact(
        self,
        artifact: CandidateArtifactRefV1,
        profile: ForgeImagesValidationProfile,
        request: ForgeImagesValidationRequestV1,
        metadata: CandidateValidationMetadata | None,
    ) -> ForgeImagesRejectedArtifactV1 | None:
        mime_type = artifact.mime_type.strip().lower()
        if mime_type not in profile.supported_mime_types:
            return self._rejection(
                artifact,
                request,
                ForgeImagesRejectionCode.UNSUPPORTED_FORMAT,
                RejectionSeverity.HARD_FAIL,
                "The artifact format is not supported for production validation.",
                f"unsupported_mime_type:{mime_type}",
                ("Use PNG, JPEG, or TIFF for this validation profile.",),
            )

        if (
            artifact.width < profile.minimum_width
            or artifact.height < profile.minimum_height
        ):
            return self._rejection(
                artifact,
                request,
                ForgeImagesRejectionCode.RESOLUTION_TOO_LOW,
                RejectionSeverity.HARD_FAIL,
                "The artifact resolution is below the profile minimum.",
                (
                    f"minimum:{profile.minimum_width}x{profile.minimum_height};"
                    f"actual:{artifact.width}x{artifact.height}"
                ),
                (
                    "Generate the replacement at or above the required "
                    "production resolution.",
                ),
            )

        expected_ratio = profile.expected_aspect_ratio
        if expected_ratio is not None:
            expected = expected_ratio[0] / expected_ratio[1]
            actual = artifact.width / artifact.height
            if abs(expected - actual) > profile.aspect_ratio_tolerance:
                return self._rejection(
                    artifact,
                    request,
                    ForgeImagesRejectionCode.ASPECT_RATIO_INVALID,
                    RejectionSeverity.HARD_FAIL,
                    "The artifact aspect ratio is outside the profile tolerance.",
                    (
                        f"expected:{expected_ratio[0]}:{expected_ratio[1]};"
                        f"actual:{artifact.width}:{artifact.height};"
                        f"tolerance:{profile.aspect_ratio_tolerance}"
                    ),
                    (
                        "Compose the replacement at the requested aspect ratio "
                        "without stretching.",
                    ),
                )

        if metadata is not None and metadata.force_reject:
            guidance = metadata.replacement_guidance or (
                "Regenerate the candidate under the requested production profile.",
            )
            return self._rejection(
                artifact,
                request,
                metadata.force_rejection_code,
                metadata.force_rejection_severity,
                "The controlled test metadata forced deterministic rejection.",
                "test_metadata:force_reject",
                guidance,
            )

        if (
            profile.safe_zone_rule_enabled
            and metadata is not None
            and metadata.safe_zone_passed is False
        ):
            return self._rejection(
                artifact,
                request,
                ForgeImagesRejectionCode.SAFE_ZONE_FAILED,
                RejectionSeverity.HARD_FAIL,
                "The primary subject crosses the required safe zone.",
                "placeholder_signal:safe_zone_failed",
                ("Keep the primary subject clear of all designated margins.",),
            )

        if (
            profile.crop_viability_rule_enabled
            and metadata is not None
            and metadata.crop_viable is False
        ):
            return self._rejection(
                artifact,
                request,
                ForgeImagesRejectionCode.CROP_NOT_VIABLE,
                RejectionSeverity.HARD_FAIL,
                "The composition cannot support the required production crops.",
                "placeholder_signal:crop_not_viable",
                ("Leave flexible margins for portrait and thumbnail crops.",),
            )

        return None

    @staticmethod
    def _rejection(
        artifact: CandidateArtifactRefV1,
        request: ForgeImagesValidationRequestV1,
        code: ForgeImagesRejectionCode,
        severity: RejectionSeverity,
        human_reason: str,
        machine_reason: str,
        guidance: tuple[str, ...],
    ) -> ForgeImagesRejectedArtifactV1:
        return ForgeImagesRejectedArtifactV1(
            artifact_id=artifact.artifact_id,
            candidate_id=artifact.candidate_id,
            rejection_code=code,
            severity=severity,
            human_reason=human_reason,
            machine_reason=machine_reason,
            replacement_guidance=list(guidance),
            template_id=request.template_id,
            validation_profile=request.validation_profile,
        )
