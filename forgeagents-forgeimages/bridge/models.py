"""
Pydantic models for the ForgeImages bridge.

These models define the contract between Python and Rust.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class AssetInput(BaseModel):
    """Input for asset validation/compilation."""

    width: int = Field(..., ge=1, le=10000)
    height: int = Field(..., ge=1, le=10000)
    color_count: Optional[int] = Field(None, ge=1, le=256)
    format: Optional[str] = None


class CompileRequest(BaseModel):
    """Request to compile an asset."""

    template_id: str = Field(..., min_length=1, max_length=64)
    asset_input: AssetInput
    source_data: Optional[str] = None  # Base64
    seed: Optional[int] = Field(None, ge=0)
    prompt: Optional[str] = Field(None, max_length=2000)

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, v: str) -> str:
        # Only allow safe template IDs
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", v):
            raise ValueError("Invalid template_id format")
        return v


class ValidationViolation(BaseModel):
    """A single validation violation."""

    rule: str
    severity: str
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    remediation: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of validation."""

    valid: bool
    violations: list[ValidationViolation] = Field(default_factory=list)
    template_id: str
    template_version: str

    @property
    def has_errors(self) -> bool:
        """Return whether any violation is a blocking error."""
        return any(violation.severity == "error" for violation in self.violations)

    @property
    def has_warnings(self) -> bool:
        """Return whether any violation is an advisory warning."""
        return any(violation.severity == "warning" for violation in self.violations)


class ExportedFile(BaseModel):
    """An exported file from compilation."""

    id: str
    filename: str
    format: str
    size: list[int]
    data_base64: str
    hash: str


class CompiledAsset(BaseModel):
    """A compiled asset with all exports."""

    id: str
    template_id: str
    template_version: str
    engine_version: str
    created_at: datetime
    manifest_hash: str
    job_hash: str
    validation: ValidationResult
    exports: list[ExportedFile]


class CompileResponse(BaseModel):
    """Response from compile endpoint."""

    success: bool
    asset: Optional[CompiledAsset] = None
    error: Optional[str] = None


class TemplateInfo(BaseModel):
    """Template summary info."""

    id: str
    name: str
    version: str
    asset_class: str
    deprecated: bool = False
