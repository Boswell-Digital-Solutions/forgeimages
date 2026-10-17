"""Qualify the frozen forgeimages-bridge binary on this platform.

Usage: python packaging/qualify_frozen.py packaging/dist

It checks, in order:
  1. ``--runtime-info`` exits 0, reports ``frozen``, CPython 3.12, every required
     module, and the templates the bundled CLI lists.
  2. An unknown argument exits 2. A start without FORGEIMAGES_AUDIT_LOG_PATH exits 2.
  3. The service starts on a free loopback port and ``/health`` answers 200.
  4. ``/templates`` lists the raster templates NeuronForge Local's image lane uses.
  5. A compile of a 1080x1080 noise master (several MiB of base64, far over the
     128 KiB argument limit) answers 200 and returns the master as the PNG export.
  6. The compile wrote one audit line.
  7. Teardown stops the whole process tree and frees the port.

It needs no network. Stdlib only.
"""

from __future__ import annotations

import base64
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zlib

WINDOWS = os.name == "nt"
EXE = ".exe" if WINDOWS else ""
FAILURES: list[str] = []
LANE_TEMPLATES = {"panel-square", "panel-fullhd", "panel-4k"}


def check(condition: bool, message: str) -> None:
    print(("PASS " if condition else "FAIL ") + message, flush=True)
    if not condition:
        FAILURES.append(message)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(url: str, body: dict | None = None, timeout: float = 5) -> tuple[int | None, str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        error.close()
        return error.code, text
    except OSError as error:
        return None, type(error).__name__


def noise_png(width: int, height: int) -> bytes:
    """An RGB PNG of random pixels, stored uncompressed: as large as a real master gets."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    rows = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 0)) + chunk(b"IEND", b"")


def start(binary: str, env_extra: dict[str, str], home: str) -> subprocess.Popen:
    env = {k: v for k, v in os.environ.items() if not k.startswith("FORGEIMAGES_")}
    env.update(env_extra)
    log = open(os.path.join(home, "sidecar.log"), "w")
    if WINDOWS:
        return subprocess.Popen(
            [binary], env=env, cwd=home, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        [binary], env=env, cwd=home, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )


def stop(process: subprocess.Popen) -> None:
    # A onefile binary is a bootloader parent plus the Python child: stop the tree.
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(15)
    except subprocess.TimeoutExpired:
        if not WINDOWS:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(15)


def port_free(port: int) -> bool:
    for _ in range(20):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.25)
    return False


def runtime_info(binary: str) -> None:
    done = subprocess.run([binary, "--runtime-info"], capture_output=True, text=True, timeout=120)
    check(done.returncode == 0, f"--runtime-info exits 0 (got {done.returncode}; stderr {done.stderr[-300:]!r})")
    try:
        info = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        check(False, f"--runtime-info prints JSON (got {done.stdout[-300:]!r})")
        return
    print(json.dumps(info, indent=1, sort_keys=True))
    check(info.get("ok") is True, "runtime reports ok")
    check(info.get("frozen") is True, "a frozen build")
    check(str(info.get("python", "")).startswith("3.12."), "runs CPython 3.12")
    listed = set(info.get("engine", {}).get("templates", []))
    check(LANE_TEMPLATES <= listed, f"bundled CLI lists the image-lane templates (got {sorted(listed)})")

    bogus = subprocess.run([binary, "--no-such-flag"], capture_output=True, text=True, timeout=60)
    check(bogus.returncode == 2, f"refuses an unknown argument with exit 2 (got {bogus.returncode})")
    env = {k: v for k, v in os.environ.items() if not k.startswith("FORGEIMAGES_")}
    no_audit = subprocess.run([binary], capture_output=True, text=True, timeout=60, env=env)
    check(
        no_audit.returncode == 2 and "FORGEIMAGES_AUDIT_LOG_PATH" in no_audit.stderr,
        f"refuses to start without an audit log path (got {no_audit.returncode}: {no_audit.stderr[-200:]!r})",
    )


def service(binary: str) -> None:
    port = free_port()
    home = tempfile.mkdtemp(prefix="qualify-forgeimages-bridge-")
    audit = os.path.join(home, "audit", "forgeimages.jsonl")
    process = start(
        binary,
        {"FORGEIMAGES_BRIDGE_PORT": str(port), "FORGEIMAGES_AUDIT_LOG_PATH": audit},
        home,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        started = time.monotonic()
        while time.monotonic() - started < 90 and request(f"{base}/health")[0] != 200:
            time.sleep(0.25)
        healthy = request(f"{base}/health")[0] == 200
        check(healthy, f"/health answers 200 (after {round(time.monotonic() - started, 2)}s)")
        if not healthy:
            print(open(os.path.join(home, "sidecar.log"), errors="replace").read()[-3000:])
            return

        code, body = request(f"{base}/templates")
        ids = {t.get("id") for t in json.loads(body)} if code == 200 else set()
        check(LANE_TEMPLATES <= ids, f"/templates lists the image-lane templates (got {code}, {sorted(ids)})")

        master = base64.b64encode(noise_png(1080, 1080)).decode()
        check(len(master) > 1024 * 1024, f"compile fixture is over 1 MiB of base64 ({len(master)} bytes)")
        code, body = request(
            f"{base}/compile/panel-square",
            {
                "template_id": "panel-square",
                "asset_input": {"width": 1080, "height": 1080},
                "source_data": master,
                "seed": 1,
            },
            timeout=60,
        )
        check(code == 200, f"compile of a real-size master answers 200 (got {code}: {body[:300]!r})")
        if code == 200:
            exports = json.loads(body).get("asset", {}).get("exports", [])
            png = next((e for e in exports if e.get("format") == "png"), {})
            check(png.get("size") == [1080, 1080], f"PNG export is 1080x1080 (got {png.get('size')})")
            check(png.get("data_base64") == master, "PNG export is the supplied master, not a placeholder")
        lines = open(audit).read().splitlines() if os.path.exists(audit) else []
        check(len(lines) == 1 and json.loads(lines[0]).get("action") == "compile", f"one compile audit line (got {len(lines)})")
    finally:
        stop(process)
    check(port_free(port), f"teardown frees port {port}")


def main() -> int:
    dist = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "packaging/dist")
    binary = os.path.join(dist, f"forgeimages-bridge{EXE}")
    runtime_info(binary)
    service(binary)
    print(f"\n{len(FAILURES)} failure(s)")
    for failure in FAILURES:
        print(f"  - {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
