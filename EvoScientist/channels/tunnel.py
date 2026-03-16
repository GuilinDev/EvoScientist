"""Tunnel support for exposing local webhook servers to the public internet.

Provides CloudflareTunnel which uses `cloudflared tunnel --url` (Cloudflare
Quick Tunnels) to obtain a temporary public HTTPS URL — free, no account
required.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil

logger = logging.getLogger(__name__)

_TRYCLOUDFLARE_RE = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")


class TunnelError(Exception):
    """Raised when a tunnel cannot be started."""


class CloudflareTunnel:
    """Manage a ``cloudflared tunnel --url`` subprocess.

    Usage::

        tunnel = CloudflareTunnel()
        public_url = await tunnel.start(9000)
        # ... later ...
        await tunnel.stop()
    """

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._public_url: str | None = None

    @property
    def public_url(self) -> str | None:
        return self._public_url

    async def start(self, port: int) -> str:
        """Start cloudflared and return the public ``*.trycloudflare.com`` URL.

        Raises:
            TunnelError: If cloudflared is not installed or fails to start.
        """
        if shutil.which("cloudflared") is None:
            raise TunnelError(
                "cloudflared is not installed. "
                "Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ "
                "or via: brew install cloudflare/cloudflare/cloudflared (macOS) / "
                "sudo apt install cloudflared (Debian/Ubuntu)"
            )

        self._process = await asyncio.create_subprocess_exec(
            "cloudflared",
            "tunnel",
            "--url",
            f"http://localhost:{port}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # cloudflared prints the public URL to stderr
        url = await self._read_url_from_stderr(timeout=30)
        if not url:
            await self.stop()
            raise TunnelError(
                "Failed to obtain public URL from cloudflared. "
                "Check network connectivity and try again."
            )

        self._public_url = url
        logger.info(f"Cloudflare tunnel started: {url} -> localhost:{port}")
        return url

    async def _read_url_from_stderr(self, timeout: float) -> str | None:
        """Read stderr lines until a trycloudflare.com URL appears."""
        assert self._process is not None
        assert self._process.stderr is not None

        try:
            async with asyncio.timeout(timeout):
                while True:
                    line = await self._process.stderr.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    logger.debug(f"cloudflared: {text.rstrip()}")
                    match = _TRYCLOUDFLARE_RE.search(text)
                    if match:
                        return match.group(0)
        except TimeoutError:
            logger.error(
                f"Timed out waiting for cloudflared URL after {timeout}s"
            )
        return None

    async def stop(self) -> None:
        """Terminate the cloudflared subprocess."""
        if self._process is None:
            return

        try:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
        except ProcessLookupError:
            pass

        self._process = None
        self._public_url = None
        logger.info("Cloudflare tunnel stopped")


def create_tunnel(tunnel_type: str) -> CloudflareTunnel | None:
    """Factory: create a tunnel instance based on *tunnel_type*.

    Returns ``None`` if *tunnel_type* is empty or unrecognised.
    """
    if not tunnel_type:
        return None

    tunnel_type = tunnel_type.strip().lower()
    if tunnel_type == "cloudflared":
        return CloudflareTunnel()

    logger.warning(f"Unknown tunnel type: {tunnel_type!r} (supported: 'cloudflared')")
    return None
