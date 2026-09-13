"""
ForgeImages Bridge - HTTP interface between ForgeAgents and ForgeImages.

This module provides the FastAPI bridge service that enforces
the "Agents suggest, ForgeImages enforces" constraint.
"""

from .models import (
    AssetInput,
    CompileRequest,
    CompileResponse,
    ValidationResult,
    ValidationViolation,
    CompiledAsset,
    ExportedFile,
    TemplateInfo,
)
from .cloud_fulfillment_contracts import (
    FORGEIMAGES_VALIDATION_REQUEST_SCHEMA_V1,
    FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1,
    CandidateArtifactRefV1,
    CompiledAssetSummaryV1,
    ForgeImagesRejectedArtifactV1,
    ForgeImagesRejectionCode,
    ForgeImagesValidationRequestV1,
    ForgeImagesValidationResultV1,
    RejectionSeverity,
)
from .cloud_fulfillment_manifest import (
    FORGEIMAGES_ASSET_MANIFEST_SCHEMA_V1,
    ForgeImagesAssetManifestV1,
)
from .cloud_fulfillment_profiles import (
    DEFAULT_FORGEIMAGES_VALIDATION_PROFILES,
    ForgeImagesValidationProfile,
    ForgeImagesValidationProfileRegistry,
    UnknownForgeImagesValidationProfile,
)
from .cloud_fulfillment_validation import (
    CandidateTestMetadataForbidden,
    CandidateValidationMetadata,
    CloudAssetValidationOutput,
    DeterministicCloudAssetValidator,
)
from .forgeimages_bridge import app
from .audit import AuditLogger, AuditEntry
from .settings import settings, Settings

__all__ = [
    # Models
    "AssetInput",
    "CompileRequest",
    "CompileResponse",
    "ValidationResult",
    "ValidationViolation",
    "CompiledAsset",
    "ExportedFile",
    "TemplateInfo",
    # Cloud fulfillment contracts
    "FORGEIMAGES_VALIDATION_REQUEST_SCHEMA_V1",
    "FORGEIMAGES_VALIDATION_RESULT_SCHEMA_V1",
    "CandidateArtifactRefV1",
    "CompiledAssetSummaryV1",
    "ForgeImagesRejectedArtifactV1",
    "ForgeImagesRejectionCode",
    "ForgeImagesValidationRequestV1",
    "ForgeImagesValidationResultV1",
    "RejectionSeverity",
    "FORGEIMAGES_ASSET_MANIFEST_SCHEMA_V1",
    "ForgeImagesAssetManifestV1",
    "DEFAULT_FORGEIMAGES_VALIDATION_PROFILES",
    "ForgeImagesValidationProfile",
    "ForgeImagesValidationProfileRegistry",
    "UnknownForgeImagesValidationProfile",
    "CandidateTestMetadataForbidden",
    "CandidateValidationMetadata",
    "CloudAssetValidationOutput",
    "DeterministicCloudAssetValidator",
    # App
    "app",
    # Audit
    "AuditLogger",
    "AuditEntry",
    # Settings
    "settings",
    "Settings",
]
