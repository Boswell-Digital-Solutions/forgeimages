"""Caller admission for the ForgeImages bridge.

``BoundaryContractTests`` mirror forge-cortex
``tests/runtime/test_local_caller_boundary.py`` case for case, so the two copies
of the boundary keep the same contract. ``WiredAppTests`` drive the real bridge
app and prove that a refused call never starts the CLI. All traffic is synthetic
ASGI; no socket is opened.
"""

from __future__ import annotations

import asyncio
import json
import time
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from bridge.local_caller_boundary import (
    CAPABILITY_ENV,
    CAPABILITY_HEADER,
    DRAIN_LIMIT_BYTES,
    LocalCallerBoundary,
)

TOKEN = "synthetic-capability-" + "a" * 48
PORT = 8100


def _scope(method, path, headers, *, kind="http", client=("127.0.0.1", 50000)):
    return {
        "type": kind,
        "method": method,
        "path": path,
        "scheme": "ws" if kind == "websocket" else "http",
        "server": ("127.0.0.1", PORT),
        "client": client,
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers],
        "query_string": b"",
        "root_path": "",
        "http_version": "1.1",
    }


def _call(app, method, path, headers, body=b"{}", *, client=("127.0.0.1", 50000)):
    """Run one request through an ASGI app; return (status, json_body)."""
    messages = []
    sent = {"done": False}

    async def receive():
        if sent["done"]:
            return {"type": "http.disconnect"}
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(_scope(method, path, headers, client=client), receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    raw = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, (json.loads(raw) if raw else None)


class _Recorder:
    """An inner ASGI app that records each request it is handed."""

    def __init__(self):
        self.effects = []

    async def __call__(self, scope, receive, send):
        self.effects.append(scope["path"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok": true}'})


def _host(value=f"127.0.0.1:{PORT}"):
    return ("Host", value)


class BoundaryContractTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {CAPABILITY_ENV: TOKEN})
        self.env.start()
        self.inner = _Recorder()
        self.app = LocalCallerBoundary(self.inner)

    def tearDown(self):
        self.env.stop()

    def _post(self, headers, path="/compile/panel-square"):
        return _call(self.app, "POST", path, headers)

    def test_admission_precedes_side_effects(self):
        json_ct = ("Content-Type", "application/json")
        cases = [
            ([_host()], 401),
            ([_host(), (CAPABILITY_HEADER, "wrong")], 401),
            ([_host(), (CAPABILITY_HEADER, TOKEN), ("Origin", "https://untrusted.invalid")], 403),
            ([_host(f"untrusted.invalid:{PORT}"), (CAPABILITY_HEADER, TOKEN)], 403),
            ([_host("localhost:9999"), (CAPABILITY_HEADER, TOKEN)], 403),
            ([_host(), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "text/plain")], 415),
            ([_host(), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "multipart/form-data; boundary=b")], 415),
            ([_host(), (CAPABILITY_HEADER, TOKEN), json_ct], 200),
        ]
        for headers, status in cases:
            with self.subTest(headers=headers):
                before = len(self.inner.effects)
                got, _ = self._post(headers)
                self.assertEqual(got, status)
                self.assertEqual(len(self.inner.effects) - before, 1 if status == 200 else 0)

    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ, {CAPABILITY_ENV: ""}):
            status, body = self._post([_host(), (CAPABILITY_HEADER, TOKEN)])
        self.assertEqual((status, body), (503, {"error": "local_capability_unconfigured"}))
        self.assertEqual(self.inner.effects, [])

    def test_malformed_configuration_fails_closed(self):
        with patch.dict(os.environ, {CAPABILITY_ENV: "too-short"}):
            status, _ = self._post([_host(), (CAPABILITY_HEADER, "too-short")])
        self.assertEqual(status, 503)
        self.assertEqual(self.inner.effects, [])

    def test_health_stays_public(self):
        with patch.dict(os.environ, {CAPABILITY_ENV: ""}):
            for method in ("GET", "HEAD"):
                status, _ = _call(self.app, method, "/health", [_host()])
                self.assertEqual(status, 200)
        self.assertEqual(self.inner.effects, ["/health", "/health"])

    def test_health_still_refuses_a_browser(self):
        status, _ = _call(self.app, "GET", "/health", [_host(), ("Origin", "https://untrusted.invalid")])
        self.assertEqual(status, 403)
        self.assertEqual(self.inner.effects, [])

    def test_probe_needs_the_capability(self):
        path = "/templates"
        self.assertEqual(_call(self.app, "GET", path, [_host()])[0], 401)
        self.assertEqual(_call(self.app, "GET", path, [_host(), (CAPABILITY_HEADER, TOKEN)])[0], 200)
        self.assertEqual(self.inner.effects, [path])

    def test_loopback_hosts(self):
        for host in (f"127.0.0.1:{PORT}", f"localhost:{PORT}", f"[::1]:{PORT}"):
            with self.subTest(host=host):
                status, _ = self._post(
                    [_host(host), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "application/json")]
                )
                self.assertEqual(status, 200)

    def test_missing_or_duplicate_host_is_denied(self):
        for headers in ([(CAPABILITY_HEADER, TOKEN)], [_host(), _host(), (CAPABILITY_HEADER, TOKEN)]):
            with self.subTest(headers=headers):
                self.assertEqual(self._post(headers)[0], 403)
        self.assertEqual(self.inner.effects, [])

    def test_remote_peer_with_loopback_host_and_capability_is_denied(self):
        # Review F3 on #27: Host is caller-written. A remote peer that knows the
        # capability and sends Host: localhost must still be refused.
        headers = [_host(f"localhost:{PORT}"), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "application/json")]
        for client in (("203.0.113.10", 50000), ("192.168.1.20", 50000), ("::ffff:203.0.113.10", 50000)):
            with self.subTest(client=client):
                status, body = _call(
                    self.app, "POST", "/compile/panel-square", headers, client=client
                )
                self.assertEqual((status, body), (403, {"error": "invalid_local_caller"}))
        for path in ("/health",):
            self.assertEqual(_call(self.app, "GET", path, [_host()], client=("203.0.113.10", 1))[0], 403)
        self.assertEqual(self.inner.effects, [])

    def test_missing_or_unparseable_peer_is_denied(self):
        headers = [_host(), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "application/json")]
        for client in (None, ("testclient", 50000), ()):
            with self.subTest(client=client):
                status, _ = _call(
                    self.app, "POST", "/compile/panel-square", headers, client=client
                )
                self.assertEqual(status, 403)
        self.assertEqual(self.inner.effects, [])

    def test_loopback_peers(self):
        headers = [_host(), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "application/json")]
        for client in (("127.0.0.1", 1), ("127.0.0.2", 1), ("::1", 1)):
            with self.subTest(client=client):
                status, _ = _call(
                    self.app, "POST", "/compile/panel-square", headers, client=client
                )
                self.assertEqual(status, 200)

    def test_duplicate_capability_is_denied(self):
        status, _ = self._post(
            [_host(), (CAPABILITY_HEADER, TOKEN), (CAPABILITY_HEADER, TOKEN), ("Content-Type", "application/json")]
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.inner.effects, [])

    def _deny_with_chunks(self, chunks):
        """Refuse a request whose body arrives in ``chunks``; return what was read."""
        pending = list(chunks)
        reads, messages = [], []

        async def receive():
            if not pending:
                return {"type": "http.disconnect"}
            body, more = pending.pop(0)
            reads.append(len(body))
            return {"type": "http.request", "body": body, "more_body": more}

        async def send(message):
            messages.append(message)

        scope = _scope("POST", "/compile/panel-square", [_host()])
        asyncio.run(self.app(scope, receive, send))
        start = next(m for m in messages if m["type"] == "http.response.start")
        return reads, start, pending

    def test_refusal_reads_the_whole_small_body_before_replying(self):
        # Windows resets a socket closed with unread data, and the client then
        # sees WinError 10053 instead of the status. Draining prevents that.
        reads, start, pending = self._deny_with_chunks(
            [(b"a" * 1000, True), (b"b" * 1000, True), (b"c" * 10, False)]
        )
        self.assertEqual(start["status"], 401)
        self.assertEqual(reads, [1000, 1000, 10])
        self.assertEqual(pending, [])
        self.assertNotIn((b"connection", b"close"), start["headers"])
        self.assertEqual(self.inner.effects, [])

    def test_refusal_stops_reading_an_oversized_body_and_closes(self):
        chunk = b"x" * (256 * 1024)
        chunks = [(chunk, True)] * (DRAIN_LIMIT_BYTES // len(chunk) + 4)
        reads, start, pending = self._deny_with_chunks(chunks)
        self.assertEqual(start["status"], 401)
        self.assertLessEqual(sum(reads), DRAIN_LIMIT_BYTES + len(chunk))
        self.assertTrue(pending)
        self.assertIn((b"connection", b"close"), start["headers"])
        self.assertEqual(self.inner.effects, [])

    def _deny_with_receive(self, receive):
        messages = []

        async def send(message):
            messages.append(message)

        scope = _scope("POST", "/compile/panel-square", [_host()])
        started = time.monotonic()
        asyncio.run(asyncio.wait_for(self.app(scope, receive, send), timeout=10))
        elapsed = time.monotonic() - started
        start = next(m for m in messages if m["type"] == "http.response.start")
        return start, elapsed

    def test_a_stalled_body_cannot_hold_the_refusal_open(self):
        # Review F4 on #28: one partial chunk, then nothing, forever.
        sent = {"first": False}

        async def receive():
            if not sent["first"]:
                sent["first"] = True
                return {"type": "http.request", "body": b"x" * 100, "more_body": True}
            await asyncio.Event().wait()

        with patch("bridge.local_caller_boundary.DRAIN_DEADLINE_SECONDS", 0.2):
            start, elapsed = self._deny_with_receive(receive)
        self.assertEqual(start["status"], 401)
        self.assertIn((b"connection", b"close"), start["headers"])
        self.assertLess(elapsed, 2.0)
        self.assertEqual(self.inner.effects, [])

    def test_a_stream_that_never_starts_cannot_hold_the_refusal_open(self):
        async def receive():
            await asyncio.Event().wait()

        with patch("bridge.local_caller_boundary.DRAIN_DEADLINE_SECONDS", 0.2):
            start, elapsed = self._deny_with_receive(receive)
        self.assertEqual(start["status"], 401)
        self.assertIn((b"connection", b"close"), start["headers"])
        self.assertLess(elapsed, 2.0)
        self.assertEqual(self.inner.effects, [])

    def test_an_early_disconnect_is_refused_promptly(self):
        pending = [
            {"type": "http.request", "body": b"x" * 100, "more_body": True},
            {"type": "http.disconnect"},
        ]

        async def receive():
            return pending.pop(0)

        start, elapsed = self._deny_with_receive(receive)
        self.assertEqual(start["status"], 401)
        self.assertIn((b"connection", b"close"), start["headers"])
        self.assertLess(elapsed, 1.0)
        self.assertEqual(pending, [])
        self.assertEqual(self.inner.effects, [])

    def test_the_drain_deadline_is_short(self):
        from bridge import local_caller_boundary

        self.assertLessEqual(local_caller_boundary.DRAIN_DEADLINE_SECONDS, 5.0)

    def test_websocket_is_closed_before_dispatch(self):
        messages = []

        async def send(message):
            messages.append(message)

        asyncio.run(self.app(_scope("GET", "/ws", [_host()], kind="websocket"), None, send))
        self.assertEqual(messages, [{"type": "websocket.close", "code": 1008}])
        self.assertEqual(self.inner.effects, [])


class WiredAppTests(unittest.TestCase):
    """The real bridge app, with the boundary as installed."""

    def setUp(self):
        self.env = patch.dict(os.environ, {CAPABILITY_ENV: TOKEN})
        self.env.start()
        from bridge import forgeimages_bridge

        self.module = forgeimages_bridge
        self.app = forgeimages_bridge.app

    def tearDown(self):
        self.env.stop()

    def test_entrypoint_installs_the_boundary(self):
        source = Path(self.module.__file__).read_text(encoding="utf-8")
        self.assertIn("app.add_middleware(LocalCallerBoundary)", source)

    def test_frozen_entry_refuses_a_non_loopback_bind(self):
        import importlib.util

        entry = Path(__file__).resolve().parents[2] / "packaging" / "freeze_entry.py"
        spec = importlib.util.spec_from_file_location("forgeimages_freeze_entry", entry)
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        for host in ("0.0.0.0", "::", "192.168.1.20"):
            env = {"FORGEIMAGES_BRIDGE_HOST": host, "FORGEIMAGES_AUDIT_LOG_PATH": "/tmp/unused"}
            with self.subTest(host=host), patch.dict(os.environ, env):
                with patch("uvicorn.run") as run:
                    self.assertEqual(launcher.main(), 2)
                    run.assert_not_called()

    def test_refused_compile_never_starts_the_cli(self):
        body = json.dumps(
            {"template_id": "panel-square", "asset_input": {"width": 1080, "height": 1080}, "source_data": "aGVsbG8="}
        ).encode()
        refusals = [
            [_host(), ("Content-Type", "application/json")],
            [_host(), ("Content-Type", "text/plain"), (CAPABILITY_HEADER, TOKEN)],
            [_host(), ("Origin", "https://untrusted.invalid"), ("Content-Type", "application/json"), (CAPABILITY_HEADER, TOKEN)],
            [_host(f"rebound.invalid:{PORT}"), ("Content-Type", "application/json"), (CAPABILITY_HEADER, TOKEN)],
        ]
        with patch.object(self.module.subprocess, "run") as cli:
            for headers in refusals:
                with self.subTest(headers=headers):
                    status, _ = _call(self.app, "POST", "/compile/panel-square", headers, body)
                    self.assertIn(status, {401, 403, 415})
            cli.assert_not_called()

    def test_templates_need_the_capability(self):
        status, payload = _call(self.app, "GET", "/templates", [_host()], b"")
        self.assertEqual((status, payload), (401, {"error": "local_capability_required"}))

    def test_authorized_caller_reaches_the_route(self):
        with patch.object(self.module, "call_cli", return_value=(0, "[]")):
            status, payload = _call(
                self.app, "GET", "/templates", [_host(), (CAPABILITY_HEADER, TOKEN)], b""
            )
        self.assertEqual(status, 200)
        self.assertEqual(payload, [])

    def test_health_answers_without_the_capability(self):
        with patch.dict(os.environ, {CAPABILITY_ENV: ""}):
            status, payload = _call(self.app, "GET", "/health", [_host()], b"")
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, dict)


if __name__ == "__main__":
    unittest.main()
