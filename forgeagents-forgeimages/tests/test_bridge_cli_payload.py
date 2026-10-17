"""
Bridge -> CLI payload transport.

A base64 raster master is megabytes. Passing it as a CLI argument fails with
"Argument list too long" (Linux refuses an argument over 128 KiB), which made
every real diffusion compile a 500. The bridge must send it on stdin.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from bridge import forgeimages_bridge


def _recording_run(calls, stdout):
    """Record the CLI call. Only the call is under test, not the response."""

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=2, stdout=json.dumps(stdout))

    return run


def _client():
    return TestClient(forgeimages_bridge.app, raise_server_exceptions=False)


def test_compile_sends_the_payload_on_stdin_not_argv():
    master = "A" * (4 * 1024 * 1024)
    calls = []
    run = _recording_run(calls, {"success": False, "error": "recorded"})
    with patch.object(forgeimages_bridge.subprocess, "run", run), patch.object(
        forgeimages_bridge.audit, "log_compile"
    ):
        _client().post(
            "/compile/panel-square",
            json={
                "template_id": "panel-square",
                "asset_input": {"width": 1080, "height": 1080},
                "source_data": master,
            },
        )

    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd[-2:] == ["--payload", "-"]
    assert all(len(arg) < 1024 for arg in cmd)
    assert json.loads(kwargs["input"])["source_data"] == master


def test_validate_sends_the_payload_on_stdin():
    calls = []
    run = _recording_run(calls, {"valid": False, "error": "recorded"})
    with patch.object(forgeimages_bridge.subprocess, "run", run), patch.object(
        forgeimages_bridge.audit, "log_validate"
    ):
        _client().post("/validate/panel-square", json={"width": 1080, "height": 1080})

    cmd, kwargs = calls[0]
    assert cmd[-2:] == ["--payload", "-"]
    assert json.loads(kwargs["input"])["width"] == 1080
