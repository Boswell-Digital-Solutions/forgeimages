"""
ForgeImages FastAPI Bridge Service.

This bridge is the ONLY interface between ForgeAgents and ForgeImages.
It enforces:
- HTTP 422 on validation failure
- All requests are audit logged
- No file writes (all data returned as base64)
"""

import json
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .models import (
    AssetInput,
    CompileRequest,
    CompileResponse,
    ValidationResult,
    TemplateInfo,
)
from .audit import AuditLogger
from .settings import settings


app = FastAPI(
    title="ForgeImages Bridge",
    description="Bridge service for ForgeAgents to access ForgeImages",
    version="1.0.0",
)

audit = AuditLogger(settings.audit_log_path)


def call_cli(command: list[str], payload: Optional[str] = None) -> tuple[int, str]:
    """Call the Rust CLI and return (exit_code, stdout).

    A payload goes to the CLI on stdin (`--payload -`), never as an argument:
    a base64 raster master is megabytes, and the OS refuses an argument that
    large (Linux: 128 KiB per argument, "Argument list too long").
    """
    cli_path = settings.cli_path
    templates_dir = settings.templates_dir

    full_command = [
        str(cli_path),
        "--templates-dir", str(templates_dir),
        *command
    ]

    try:
        result = subprocess.run(
            full_command,
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="ForgeImages CLI not found. Build with: cargo build --release"
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="ForgeImages CLI timeout"
        )


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Limit request body size for security."""
    content_length = request.headers.get("content-length")
    if content_length:
        if int(content_length) > settings.max_request_size_mb * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large"}
            )
    return await call_next(request)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "forgeimages-bridge"}


@app.get("/templates", response_model=list[TemplateInfo])
async def list_templates():
    """List all available templates."""
    exit_code, output = call_cli(["templates"])

    if exit_code != 0:
        raise HTTPException(status_code=500, detail="Failed to list templates")

    try:
        templates = json.loads(output)
        return templates
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid CLI output")


@app.post("/validate/{template_id}", response_model=ValidationResult)
async def validate_asset(
    template_id: str,
    asset_input: AssetInput,
    request: Request,
):
    """
    Validate an asset against a template.

    Returns 200 with validation result (may include violations).
    Returns 422 if validation fails with blocking errors.
    """
    request_id = str(uuid.uuid4())
    user_id = request.headers.get("X-User-ID")

    # Build payload
    payload = asset_input.model_dump()

    # Call CLI
    exit_code, output = call_cli(
        ["validate", "--template", template_id, "--payload", "-"],
        payload=json.dumps(payload),
    )

    try:
        result = json.loads(output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid CLI output")

    # Compute job hash for audit
    job_hash = audit.compute_job_hash(
        template_id,
        result.get("template_version", "unknown"),
        payload,
        settings.engine_version,
    )

    # Log the request
    audit.log_validate(
        request_id=request_id,
        template_id=template_id,
        job_hash=job_hash,
        valid=result.get("valid", False),
        violations_count=len(result.get("violations", [])),
        user_id=user_id,
    )

    # Return 422 on validation failure
    if exit_code == 2:  # Validation failure
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Validation failed",
                "violations": result.get("violations", []),
                "template_id": template_id,
                "template_version": result.get("template_version"),
            }
        )

    if exit_code != 0:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown error")
        )

    return ValidationResult(**result)


@app.post("/compile/{template_id}", response_model=CompileResponse)
async def compile_asset(
    template_id: str,
    compile_request: CompileRequest,
    request: Request,
):
    """
    Compile an asset using a template.

    Returns 200 with compiled asset on success.
    Returns 422 if validation fails.
    """
    request_id = str(uuid.uuid4())
    user_id = request.headers.get("X-User-ID")

    # Ensure template_id matches
    if compile_request.template_id != template_id:
        raise HTTPException(
            status_code=400,
            detail="template_id in path must match request body"
        )

    # Build payload
    payload = compile_request.model_dump()

    # Call CLI
    exit_code, output = call_cli(
        ["compile", "--template", template_id, "--payload", "-"],
        payload=json.dumps(payload),
    )

    try:
        result = json.loads(output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid CLI output")

    # Get job hash from result or compute
    job_hash = result.get("asset", {}).get("job_hash", "")
    if not job_hash:
        job_hash = audit.compute_job_hash(
            template_id,
            "unknown",
            payload,
            settings.engine_version,
        )

    # Determine success
    success = result.get("success", False)
    error_message = result.get("error")

    # Log the request
    audit.log_compile(
        request_id=request_id,
        template_id=template_id,
        job_hash=job_hash,
        success=success,
        violations_count=len(result.get("asset", {}).get("validation", {}).get("violations", [])),
        error_message=error_message,
        user_id=user_id,
    )

    # Return 422 on validation failure
    if exit_code == 2:  # Validation/compilation failure
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Compilation failed",
                "error": error_message,
                "template_id": template_id,
            }
        )

    if exit_code != 0:
        raise HTTPException(
            status_code=500,
            detail=error_message or "Unknown error"
        )

    return CompileResponse(**result)


@app.get("/template/{template_id}")
async def get_template(template_id: str):
    """Get details for a specific template."""
    exit_code, output = call_cli(["templates"])

    if exit_code != 0:
        raise HTTPException(status_code=500, detail="Failed to list templates")

    try:
        templates = json.loads(output)
        for t in templates:
            if t.get("id") == template_id:
                return t
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid CLI output")
