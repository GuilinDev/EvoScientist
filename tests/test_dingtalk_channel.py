"""Tests for DingTalk channel implementation."""

import asyncio

import pytest

from EvoScientist.channels.dingtalk.channel import DingTalkChannel, DingTalkConfig
from EvoScientist.channels.base import ChannelError


def _run(coro):
    """Run an async coroutine safely, creating a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestDingTalkConfig:
    def test_default_values(self):
        config = DingTalkConfig()
        assert config.client_id == ""
        assert config.client_secret == ""
        assert config.allowed_senders is None
        assert config.text_chunk_limit == 4096

    def test_custom_values(self):
        config = DingTalkConfig(
            client_id="test-id",
            client_secret="test-secret",
            allowed_senders={"user1"},
            text_chunk_limit=2000,
            proxy="http://proxy:8080",
        )
        assert config.client_id == "test-id"
        assert config.client_secret == "test-secret"
        assert config.allowed_senders == {"user1"}
        assert config.text_chunk_limit == 2000
        assert config.proxy == "http://proxy:8080"


class TestDingTalkChannel:
    def test_init(self):
        config = DingTalkConfig(client_id="test-id", client_secret="test-secret")
        channel = DingTalkChannel(config)
        assert channel.config is config
        assert channel._running is False
        assert channel.name == "dingtalk"

    def test_start_raises_without_credentials(self):
        config = DingTalkConfig(client_id="", client_secret="")
        channel = DingTalkChannel(config)
        with pytest.raises(ChannelError, match="client_id and client_secret"):
            _run(channel.start())

    def test_start_raises_without_client_id(self):
        config = DingTalkConfig(client_id="", client_secret="secret")
        channel = DingTalkChannel(config)
        with pytest.raises(ChannelError, match="client_id and client_secret"):
            _run(channel.start())

    def test_start_raises_without_client_secret(self):
        config = DingTalkConfig(client_id="id", client_secret="")
        channel = DingTalkChannel(config)
        with pytest.raises(ChannelError, match="client_id and client_secret"):
            _run(channel.start())

    def test_stop_when_not_running(self):
        config = DingTalkConfig(client_id="test-id", client_secret="test-secret")
        channel = DingTalkChannel(config)
        _run(channel.stop())

    def test_send_returns_false_without_client(self):
        from EvoScientist.channels.base import OutboundMessage

        config = DingTalkConfig(client_id="test-id", client_secret="test-secret")
        channel = DingTalkChannel(config)
        msg = OutboundMessage(
            channel="dingtalk",
            chat_id="user123",
            content="hello",
            metadata={"chat_id": "user123"},
        )
        result = _run(channel.send(msg))
        assert result is False

    def test_capabilities(self):
        from EvoScientist.channels.capabilities import DINGTALK
        config = DingTalkConfig()
        channel = DingTalkChannel(config)
        assert channel.capabilities is DINGTALK
        assert channel.capabilities.format_type == "markdown"
        assert channel.capabilities.groups is True
        assert channel.capabilities.mentions is True
        assert channel.capabilities.media_send is True
        assert channel.capabilities.media_receive is True


class TestDingTalkChannelRegistration:
    def test_dingtalk_registered(self):
        from EvoScientist.channels.channel_manager import available_channels
        channels = available_channels()
        assert "dingtalk" in channels


class TestDingTalkProbe:
    def test_missing_credentials(self):
        from EvoScientist.channels.dingtalk.probe import validate_dingtalk
        ok, msg = _run(validate_dingtalk("", ""))
        assert ok is False
        assert "required" in msg

    def test_missing_client_id(self):
        from EvoScientist.channels.dingtalk.probe import validate_dingtalk
        ok, msg = _run(validate_dingtalk("", "secret"))
        assert ok is False

    def test_missing_client_secret(self):
        from EvoScientist.channels.dingtalk.probe import validate_dingtalk
        ok, msg = _run(validate_dingtalk("id", ""))
        assert ok is False
