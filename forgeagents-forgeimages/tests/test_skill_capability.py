"""The skill sends the bridge capability only to a loopback bridge."""

import pytest

from skill.forgeimages_skill import CAPABILITY_ENV, CAPABILITY_HEADER, ForgeImagesSkill

TOKEN = "synthetic-capability-" + "c" * 48


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:8100", "http://localhost:8100", "http://[::1]:8100"]
)
def test_capability_goes_to_a_loopback_bridge(monkeypatch, url):
    monkeypatch.setenv(CAPABILITY_ENV, TOKEN)
    assert ForgeImagesSkill(bridge_url=url)._get_headers()[CAPABILITY_HEADER] == TOKEN


@pytest.mark.parametrize(
    "url",
    [
        "https://bridge.example.com",
        "http://192.168.1.20:8100",
        "http://127.0.0.1.attacker.example:8100",
        "http://user:pass@127.0.0.1:8100",
        "ftp://127.0.0.1:8100",
        "not a url",
    ],
)
def test_capability_never_goes_off_host(monkeypatch, url):
    monkeypatch.setenv(CAPABILITY_ENV, TOKEN)
    assert CAPABILITY_HEADER not in ForgeImagesSkill(bridge_url=url)._get_headers()


def test_no_capability_configured_sends_none(monkeypatch):
    monkeypatch.delenv(CAPABILITY_ENV, raising=False)
    assert CAPABILITY_HEADER not in ForgeImagesSkill()._get_headers()
