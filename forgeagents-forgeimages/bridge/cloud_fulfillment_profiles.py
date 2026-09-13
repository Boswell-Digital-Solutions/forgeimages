"""Immutable production-validation profiles for cloud image candidates."""

from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType
from typing import Mapping

from pydantic import ConfigDict, Field, field_validator

from .cloud_fulfillment_contracts import StrictContractModel


class ForgeImagesValidationProfile(StrictContractModel):
    """Deterministic technical thresholds for one validation profile."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=(), frozen=True)

    profile_id: str = Field(..., min_length=1, max_length=128)
    supported_mime_types: frozenset[str] = Field(..., min_length=1)
    minimum_width: int = Field(..., ge=1)
    minimum_height: int = Field(..., ge=1)
    expected_aspect_ratio: tuple[int, int] | None = None
    aspect_ratio_tolerance: float = Field(default=0.02, ge=0.0, le=0.25)
    safe_zone_rule_enabled: bool = False
    crop_viability_rule_enabled: bool = False

    @field_validator("profile_id")
    @classmethod
    def normalize_profile_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("profile_id must not be blank")
        return normalized

    @field_validator("supported_mime_types")
    @classmethod
    def normalize_mime_types(cls, values: frozenset[str]) -> frozenset[str]:
        normalized = frozenset(
            value.strip().lower() for value in values if value.strip()
        )
        if not normalized:
            raise ValueError("supported_mime_types must not be empty")
        if any(not value.startswith("image/") for value in normalized):
            raise ValueError("supported_mime_types must contain image MIME types")
        return normalized

    @field_validator("expected_aspect_ratio")
    @classmethod
    def validate_aspect_ratio(
        cls, value: tuple[int, int] | None
    ) -> tuple[int, int] | None:
        if value is not None and (value[0] <= 0 or value[1] <= 0):
            raise ValueError("expected_aspect_ratio values must be positive")
        return value


class UnknownForgeImagesValidationProfile(LookupError):
    """Raised when a validation profile has no governed definition."""


class ForgeImagesValidationProfileRegistry:
    """Read-only validation profile registry with duplicate protection."""

    def __init__(self, profiles: Iterable[ForgeImagesValidationProfile]) -> None:
        registered: dict[str, ForgeImagesValidationProfile] = {}
        for profile in profiles:
            if profile.profile_id in registered:
                raise ValueError(
                    f"duplicate ForgeImages validation profile: {profile.profile_id}"
                )
            registered[profile.profile_id] = profile
        self._profiles: Mapping[str, ForgeImagesValidationProfile] = MappingProxyType(
            registered
        )

    def require(self, profile_id: str) -> ForgeImagesValidationProfile:
        normalized = profile_id.strip().lower()
        profile = self._profiles.get(normalized)
        if profile is None:
            raise UnknownForgeImagesValidationProfile(normalized)
        return profile


_CORE_SUPPORTED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/tiff"})

DEFAULT_FORGEIMAGES_VALIDATION_PROFILES = ForgeImagesValidationProfileRegistry(
    (
        ForgeImagesValidationProfile(
            profile_id="authorforge_cover_concept",
            supported_mime_types=_CORE_SUPPORTED_MIME_TYPES,
            minimum_width=1024,
            minimum_height=1536,
            expected_aspect_ratio=(2, 3),
            aspect_ratio_tolerance=0.02,
            safe_zone_rule_enabled=True,
            crop_viability_rule_enabled=True,
        ),
        ForgeImagesValidationProfile(
            profile_id="pressforge_social_image",
            supported_mime_types=_CORE_SUPPORTED_MIME_TYPES,
            minimum_width=1080,
            minimum_height=1080,
            expected_aspect_ratio=(1, 1),
            aspect_ratio_tolerance=0.02,
            safe_zone_rule_enabled=True,
            crop_viability_rule_enabled=True,
        ),
        ForgeImagesValidationProfile(
            profile_id="internal_smoke",
            supported_mime_types=_CORE_SUPPORTED_MIME_TYPES,
            minimum_width=1,
            minimum_height=1,
            expected_aspect_ratio=None,
            aspect_ratio_tolerance=0.05,
        ),
    )
)
