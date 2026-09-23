"""
ForgeImages Skill for ForgeAgents.

This skill provides the agent-facing interface for image operations.
All operations are validated and enforced by the ForgeImages engine
via the bridge service.

CRITICAL: Agents suggest, ForgeImages enforces.
- Agents can request operations but cannot bypass validation
- All requests go through the HTTP bridge
- HTTP 422 = validation failure (agent must adjust request)
"""

from typing import Optional, Any
from dataclasses import dataclass
import httpx


class ForgeImagesError(Exception):
    """Error from ForgeImages operations."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        violations: Optional[list[dict]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.violations = violations or []

    def is_validation_error(self) -> bool:
        """Check if this is a validation error (HTTP 422)."""
        return self.status_code == 422

    def get_remediation_hints(self) -> list[str]:
        """Extract remediation hints from violations."""
        hints = []
        for v in self.violations:
            hints.extend(v.get("remediation", []))
        return hints


@dataclass
class ValidationResult:
    """Result of asset validation."""
    valid: bool
    violations: list[dict]
    template_id: str
    template_version: str

    @property
    def has_errors(self) -> bool:
        return any(v.get("severity") == "error" for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.get("severity") == "warning" for v in self.violations)


@dataclass
class CompiledAsset:
    """A compiled asset with all exports."""
    id: str
    template_id: str
    template_version: str
    engine_version: str
    manifest_hash: str
    job_hash: str
    exports: list[dict]

    def get_export(self, export_id: str) -> Optional[dict]:
        """Get a specific export by ID."""
        for export in self.exports:
            if export.get("id") == export_id:
                return export
        return None

    def get_export_data(self, export_id: str) -> Optional[bytes]:
        """Get decoded export data by ID."""
        import base64
        export = self.get_export(export_id)
        if export:
            return base64.b64decode(export.get("data_base64", ""))
        return None


class ForgeImagesSkill:
    """
    ForgeImages skill for agents.

    This skill provides a clean interface for agents to request
    image compilation operations. All operations are validated
    and enforced by the ForgeImages engine.

    Example usage:
        skill = ForgeImagesSkill("http://127.0.0.1:8100")

        # List available templates
        templates = await skill.list_templates()

        # Validate before compiling
        result = await skill.validate(
            template_id="pwa-icon",
            width=1024,
            height=1024,
        )

        if result.valid:
            # Compile the asset
            asset = await skill.compile(
                template_id="pwa-icon",
                width=1024,
                height=1024,
            )
            # Use asset.exports...
    """

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:8100",
        timeout: float = 30.0,
        user_id: Optional[str] = None,
    ):
        """
        Initialize the skill.

        Args:
            bridge_url: URL of the ForgeImages bridge service
            timeout: Request timeout in seconds
            user_id: Optional user ID for audit logging
        """
        self.bridge_url = bridge_url.rstrip("/")
        self.timeout = timeout
        self.user_id = user_id

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.user_id:
            headers["X-User-ID"] = self.user_id
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[dict] = None,
    ) -> dict:
        """Make a request to the bridge."""
        url = f"{self.bridge_url}{path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=self._get_headers(),
                )

                # Handle validation errors specially
                if response.status_code == 422:
                    detail = response.json().get("detail", {})
                    raise ForgeImagesError(
                        message=detail.get("message", "Validation failed"),
                        status_code=422,
                        violations=detail.get("violations", []),
                    )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                raise ForgeImagesError(
                    message=f"HTTP {e.response.status_code}: {detail}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise ForgeImagesError(f"Request failed: {e}")

    async def health(self) -> dict:
        """Check bridge health."""
        return await self._request("GET", "/health")

    async def list_templates(self) -> list[dict]:
        """
        List all available templates.

        Returns:
            List of template info dicts with id, name, version, etc.
        """
        return await self._request("GET", "/templates")

    async def get_template(self, template_id: str) -> dict:
        """
        Get details for a specific template.

        Args:
            template_id: The template ID to look up

        Returns:
            Template info dict
        """
        return await self._request("GET", f"/template/{template_id}")

    async def validate(
        self,
        template_id: str,
        width: int,
        height: int,
        color_count: Optional[int] = None,
        format: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate an asset against a template.

        This should be called before compile to check if the asset
        will pass validation. Use this to provide feedback to users
        before attempting compilation.

        Args:
            template_id: Template to validate against
            width: Asset width in pixels
            height: Asset height in pixels
            color_count: Optional color count for palette validation
            format: Optional format hint

        Returns:
            ValidationResult with valid flag and any violations

        Raises:
            ForgeImagesError: On HTTP 422 (blocking validation failure)
        """
        payload = {
            "width": width,
            "height": height,
        }
        if color_count is not None:
            payload["color_count"] = color_count
        if format is not None:
            payload["format"] = format

        try:
            result = await self._request(
                "POST",
                f"/validate/{template_id}",
                json_data=payload,
            )
            return ValidationResult(
                valid=result.get("valid", False),
                violations=result.get("violations", []),
                template_id=result.get("template_id", template_id),
                template_version=result.get("template_version", "unknown"),
            )
        except ForgeImagesError as e:
            if e.is_validation_error():
                # Return as a result, not an exception
                return ValidationResult(
                    valid=False,
                    violations=e.violations,
                    template_id=template_id,
                    template_version="unknown",
                )
            raise

    async def compile(
        self,
        template_id: str,
        width: int,
        height: int,
        color_count: Optional[int] = None,
        format: Optional[str] = None,
        source_data: Optional[str] = None,
        seed: Optional[int] = None,
        prompt: Optional[str] = None,
    ) -> CompiledAsset:
        """
        Compile an asset using a template.

        IMPORTANT: This will fail with ForgeImagesError (status_code=422)
        if validation fails. Use validate() first to check.

        Args:
            template_id: Template to compile with
            width: Asset width in pixels
            height: Asset height in pixels
            color_count: Optional color count for palette validation
            format: Optional format hint
            source_data: Optional base64-encoded source image
            seed: Optional seed for deterministic generation
            prompt: Optional prompt for AI-assisted generation

        Returns:
            CompiledAsset with all exports as base64

        Raises:
            ForgeImagesError: On validation failure (422) or other errors
        """
        asset_input = {
            "width": width,
            "height": height,
        }
        if color_count is not None:
            asset_input["color_count"] = color_count
        if format is not None:
            asset_input["format"] = format

        payload = {
            "template_id": template_id,
            "asset_input": asset_input,
        }
        if source_data is not None:
            payload["source_data"] = source_data
        if seed is not None:
            payload["seed"] = seed
        if prompt is not None:
            payload["prompt"] = prompt

        result = await self._request(
            "POST",
            f"/compile/{template_id}",
            json_data=payload,
        )

        if not result.get("success"):
            raise ForgeImagesError(
                message=result.get("error", "Compilation failed"),
            )

        asset = result.get("asset", {})
        return CompiledAsset(
            id=asset.get("id", ""),
            template_id=asset.get("template_id", template_id),
            template_version=asset.get("template_version", "unknown"),
            engine_version=asset.get("engine_version", "unknown"),
            manifest_hash=asset.get("manifest_hash", ""),
            job_hash=asset.get("job_hash", ""),
            exports=asset.get("exports", []),
        )

    async def validate_and_compile(
        self,
        template_id: str,
        width: int,
        height: int,
        **kwargs,
    ) -> tuple[ValidationResult, Optional[CompiledAsset]]:
        """
        Convenience method: validate then compile if valid.

        Returns:
            Tuple of (ValidationResult, CompiledAsset or None)
        """
        result = await self.validate(
            template_id=template_id,
            width=width,
            height=height,
            color_count=kwargs.get("color_count"),
            format=kwargs.get("format"),
        )

        if not result.valid:
            return result, None

        asset = await self.compile(
            template_id=template_id,
            width=width,
            height=height,
            **kwargs,
        )

        return result, asset
