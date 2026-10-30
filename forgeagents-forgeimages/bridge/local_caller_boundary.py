"""Per-launch caller admission for the ForgeImages bridge.

A port of forge-cortex ``service/local_caller_boundary.py`` (forge-cortex #27,
#28, #30), which ports forge-neuronforge ``LocalCallerBoundary`` (#26) and adds a
peer-address check and a bounded refused-body drain. The admission contract:

- the peer address (ASGI ``scope["client"]``) is loopback. ``Host`` is a header
  the caller writes, so it proves nothing about where the caller is;
- exactly one ``Host`` header, naming a loopback host and the bound port;
- no ``Origin`` header at all, because no browser page may call the bridge;
- one per-launch capability header, compared in constant time;
- ``application/json`` on every POST, PUT or PATCH.

Only ``GET``/``HEAD /health`` is public. Every other route, ``/templates``
included, needs the capability. A refusal happens before any route runs, so no
CLI is started and nothing is decoded for a refused caller. Before the refusal is
sent, the request body is read and discarded, never parsed, for at most
``DRAIN_DEADLINE_SECONDS`` and about ``DRAIN_LIMIT_BYTES``. Without that, a client
that sent a complete body sees a TCP reset on Windows instead of the status.

A body that stalls, disconnects early, or runs past either limit is not read
further, and the refusal is sent at once with ``Connection: close``; that client
may then see a reset instead of the status. The byte limit is checked per ASGI
chunk, so it is approximate. The status is reliable for an ordinary complete body
within both limits, not for an attacker-controlled incomplete one.

The bridge holds no credential issuance authority. The AuthorForge shell mints
the capability per launch and passes it to the bridge and to its callers.

The admission checks (peer, ``Host``, ``Origin``, capability, content type) are
shared with the forge-cortex copy; ``tests/test_local_caller_boundary.py`` pins
them. The refused-body drain is shared with forge-cortex only.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import secrets
from urllib.parse import urlsplit

CAPABILITY_ENV = "FORGEIMAGES_BRIDGE_CAPABILITY"
CAPABILITY_HEADER = "X-AuthorForge-ForgeImages-Capability"
# Every write route needs JSON; the bridge has no route prefix.
JSON_WRITE_PREFIX = "/"

_CAPABILITY_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,512}")
# A refused body larger than this is not read further; the reply then closes
# the connection, and the client may see a reset instead of the status.
DRAIN_LIMIT_BYTES = 1 << 20
# A refused caller cannot delay its refusal past this by sending slowly or not
# at all (forge-cortex review F4 on #28).
DRAIN_DEADLINE_SECONDS = 2.0


class LocalCallerBoundary:
    """Reject browser and foreign-host callers before body parsing or file I/O."""

    def __init__(
        self,
        app,
        *,
        token_env: str = CAPABILITY_ENV,
        header: str = CAPABILITY_HEADER,
        json_write_prefix: str = JSON_WRITE_PREFIX,
    ):
        self.app = app
        self.token_env = token_env
        self.header = header.lower().encode("ascii")
        self.json_write_prefix = json_write_prefix

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        headers = scope.get("headers", [])
        hosts = [value for key, value in headers if key.lower() == b"host"]
        origins = [value for key, value in headers if key.lower() == b"origin"]
        if (
            not self._local_peer(scope)
            or origins
            or len(hosts) != 1
            or not self._local_host(hosts[0], scope)
        ):
            return await self._deny(scope, receive, send, 403, "invalid_local_caller")
        if (
            scope["type"] == "http"
            and scope.get("method") in {"GET", "HEAD"}
            and scope.get("path") == "/health"
        ):
            return await self.app(scope, receive, send)
        expected = os.environ.get(self.token_env, "").strip()
        if not _CAPABILITY_PATTERN.fullmatch(expected):
            return await self._deny(scope, receive, send, 503, "local_capability_unconfigured")
        supplied = [value for key, value in headers if key.lower() == self.header]
        if len(supplied) != 1 or not secrets.compare_digest(
            supplied[0], expected.encode("ascii")
        ):
            return await self._deny(scope, receive, send, 401, "local_capability_required")
        if (
            scope["type"] == "http"
            and scope.get("path", "").startswith(self.json_write_prefix)
            and scope.get("method") in {"POST", "PUT", "PATCH"}
        ):
            content_types = [
                value for key, value in headers if key.lower() == b"content-type"
            ]
            if (
                len(content_types) != 1
                or content_types[0].split(b";", 1)[0].strip().lower()
                != b"application/json"
            ):
                return await self._deny(scope, receive, send, 415, "application_json_required")
        return await self.app(scope, receive, send)

    @staticmethod
    def _local_peer(scope) -> bool:
        client = scope.get("client")
        if not client:
            return False
        try:
            return ipaddress.ip_address(client[0]).is_loopback
        except (ValueError, TypeError, IndexError):
            return False

    @staticmethod
    def _local_host(raw: bytes, scope) -> bool:
        try:
            authority = raw.decode("ascii")
            if not authority or any(char in authority for char in "@/\\%?# \t\r\n"):
                return False
            parsed = urlsplit("//" + authority)
            host = parsed.hostname
            if host is None or (
                host.lower() != "localhost" and not ipaddress.ip_address(host).is_loopback
            ):
                return False
            port = parsed.port
            if port is None:
                port = 443 if scope.get("scheme") in {"https", "wss"} else 80
            return port > 0 and port == scope["server"][1]
        except (ValueError, KeyError, TypeError, UnicodeError):
            return False

    @staticmethod
    async def _drain(receive) -> bool:
        """Read and discard the request body within both limits.

        True only when the whole body arrived in time and within the byte limit.
        False on a stall, an early disconnect, or a body over either limit.
        """

        async def read_all() -> bool:
            received = 0
            while received <= DRAIN_LIMIT_BYTES:
                message = await receive()
                if message["type"] != "http.request":
                    return False
                received += len(message.get("body", b""))
                if not message.get("more_body", False):
                    return received <= DRAIN_LIMIT_BYTES
            return False

        try:
            return await asyncio.wait_for(read_all(), timeout=DRAIN_DEADLINE_SECONDS)
        except asyncio.TimeoutError:
            return False

    @classmethod
    async def _deny(cls, scope, receive, send, status: int, reason: str):
        if scope["type"] == "websocket":
            return await send({"type": "websocket.close", "code": 1008})
        headers = [
            (b"content-type", b"application/json"),
            (b"cache-control", b"no-store"),
        ]
        if not await cls._drain(receive):
            headers.append((b"connection", b"close"))
        body = json.dumps({"error": reason}).encode("utf-8")
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})
