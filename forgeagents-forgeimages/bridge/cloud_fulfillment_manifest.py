"""Deterministic manifests for cloud image validation outcomes."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Literal

from pydantic import Field, model_validator

from .cloud_fulfillment_contracts import StrictContractModel


FORGEIMAGES_ASSET_MANIFEST_SCHEMA_V1 = "forgeimages_asset_manifest.v1"


def _manifest_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ForgeImagesAssetManifestV1(StrictContractModel):
    """Content-addressed record of one validation and compilation outcome."""

    schema_version: Literal["forgeimages_asset_manifest.v1"]
    validation_id: str = Field(..., min_length=1)
    source_job_id: str = Field(..., min_length=1)
    accepted_artifact_ids: list[str] = Field(default_factory=list)
    rejected_artifact_ids: list[str] = Field(default_factory=list)
    template_id: str | None = None
    validation_profile: str = Field(..., min_length=1)
    compiled_asset_ids: list[str] = Field(default_factory=list)
    export_variants: list[str] = Field(default_factory=list)
    manifest_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        validation_id: str,
        source_job_id: str,
        accepted_artifact_ids: list[str],
        rejected_artifact_ids: list[str],
        template_id: str | None,
        validation_profile: str,
        compiled_asset_ids: list[str] | None = None,
        export_variants: list[str] | None = None,
    ) -> "ForgeImagesAssetManifestV1":
        """Build a canonical manifest and bind its SHA-256 digest."""
        payload: dict[str, Any] = {
            "schema_version": FORGEIMAGES_ASSET_MANIFEST_SCHEMA_V1,
            "validation_id": validation_id,
            "source_job_id": source_job_id,
            "accepted_artifact_ids": sorted(accepted_artifact_ids),
            "rejected_artifact_ids": sorted(rejected_artifact_ids),
            "template_id": template_id,
            "validation_profile": validation_profile,
            "compiled_asset_ids": sorted(compiled_asset_ids or []),
            "export_variants": sorted(export_variants or []),
        }
        return cls(**payload, manifest_sha256=_manifest_digest(payload))

    @model_validator(mode="after")
    def verify_manifest_hash(self) -> "ForgeImagesAssetManifestV1":
        """Reject manifests whose content no longer matches their digest."""
        payload = self.model_dump(mode="json", exclude={"manifest_sha256"})
        expected = _manifest_digest(payload)
        if not hmac.compare_digest(self.manifest_sha256, expected):
            raise ValueError("manifest_sha256 does not match manifest content")
        return self
