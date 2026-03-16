"""Tests for EvoScientist.channels.tunnel module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from EvoScientist.channels.tunnel import (
    CloudflareTunnel,
    TunnelError,
    create_tunnel,
    _TRYCLOUDFLARE_RE,
)


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── create_tunnel factory ────────────────────────────────────────────


class TestCreateTunnel:
    def test_empty_string_returns_none(self):
        assert create_tunnel("") is None

    def test_whitespace_returns_none(self):
        assert create_tunnel("   ") is None

    def test_cloudflared_returns_instance(self):
        tunnel = create_tunnel("cloudflared")
        assert isinstance(tunnel, CloudflareTunnel)

    def test_cloudflared_case_insensitive(self):
        assert isinstance(create_tunnel("Cloudflared"), CloudflareTunnel)
        assert isinstance(create_tunnel("CLOUDFLARED"), CloudflareTunnel)

    def test_unknown_type_returns_none(self):
        assert create_tunnel("ngrok") is None
        assert create_tunnel("unknown") is None


# ── URL regex ────────────────────────────────────────────────────────


class TestTrycloudflareRegex:
    def test_matches_typical_url(self):
        line = "INF |  https://foo-bar-baz.trycloudflare.com"
        match = _TRYCLOUDFLARE_RE.search(line)
        assert match is not None
        assert match.group(0) == "https://foo-bar-baz.trycloudflare.com"

    def test_matches_url_with_trailing_text(self):
        line = "https://abc-123.trycloudflare.com/some/path"
        match = _TRYCLOUDFLARE_RE.search(line)
        assert match is not None
        assert match.group(0) == "https://abc-123.trycloudflare.com"

    def test_no_match_on_unrelated_text(self):
        assert _TRYCLOUDFLARE_RE.search("hello world") is None
        assert _TRYCLOUDFLARE_RE.search("http://localhost:9000") is None


# ── CloudflareTunnel ─────────────────────────────────────────────────


class TestCloudflareTunnel:
    @patch("EvoScientist.channels.tunnel.shutil.which", return_value=None)
    def test_start_raises_if_not_installed(self, mock_which):
        tunnel = CloudflareTunnel()
        with pytest.raises(TunnelError, match="cloudflared is not installed"):
            _run(tunnel.start(9000))

    @patch("EvoScientist.channels.tunnel.shutil.which", return_value="/usr/bin/cloudflared")
    def test_start_returns_url(self, mock_which):
        tunnel = CloudflareTunnel()

        # Mock stderr that yields the URL line
        mock_stderr = AsyncMock()
        url_line = b"INF |  https://test-tunnel-abc.trycloudflare.com\n"
        mock_stderr.readline = AsyncMock(side_effect=[url_line])

        mock_process = AsyncMock()
        mock_process.stderr = mock_stderr
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            url = _run(tunnel.start(9000))

        assert url == "https://test-tunnel-abc.trycloudflare.com"
        assert tunnel.public_url == url

    @patch("EvoScientist.channels.tunnel.shutil.which", return_value="/usr/bin/cloudflared")
    def test_start_raises_on_no_url(self, mock_which):
        tunnel = CloudflareTunnel()

        # Mock stderr that yields unrelated lines then EOF
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(
            side_effect=[b"some unrelated output\n", b""]
        )

        mock_process = AsyncMock()
        mock_process.stderr = mock_stderr
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            with pytest.raises(TunnelError, match="Failed to obtain public URL"):
                _run(tunnel.start(9000))

    def test_stop_no_process_is_noop(self):
        tunnel = CloudflareTunnel()
        _run(tunnel.stop())  # should not raise

    def test_stop_terminates_process(self):
        tunnel = CloudflareTunnel()

        mock_process = AsyncMock()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        tunnel._process = mock_process
        tunnel._public_url = "https://x.trycloudflare.com"

        _run(tunnel.stop())

        mock_process.terminate.assert_called_once()
        assert tunnel._process is None
        assert tunnel._public_url is None

    def test_stop_kills_if_terminate_hangs(self):
        tunnel = CloudflareTunnel()

        mock_process = AsyncMock()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        # First wait (after terminate) times out, second (after kill) succeeds
        mock_process.wait = AsyncMock(
            side_effect=[asyncio.TimeoutError(), None]
        )

        tunnel._process = mock_process

        _run(tunnel.stop())

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
