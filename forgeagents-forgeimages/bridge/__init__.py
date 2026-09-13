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
    # App
    "app",
    # Audit
    "AuditLogger",
    "AuditEntry",
    # Settings
    "settings",
    "Settings",
]
