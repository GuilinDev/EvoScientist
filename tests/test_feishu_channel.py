"""Tests for Feishu channel implementation."""

import asyncio
import json

import pytest

from EvoScientist.channels.feishu.channel import (
    FeishuChannel,
    FeishuConfig,
    _markdown_to_feishu_post,
    _parse_inline_text,
)
from EvoScientist.channels.base import ChannelError


def _run(coro):
    """Run an async coroutine safely, creating a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestFeishuConfig:
    def test_default_values(self):
        config = FeishuConfig()
        assert config.app_id == ""
        assert config.app_secret == ""
        assert config.verification_token == ""
        assert config.encrypt_key == ""
        assert config.webhook_port == 9000
        assert config.text_chunk_limit == 4096
        assert config.feishu_domain == "https://open.feishu.cn"
        assert config.allowed_senders is None

    def test_custom_values(self):
        config = FeishuConfig(
            app_id="test-id",
            app_secret="test-secret",
            verification_token="token123",
            encrypt_key="key123",
            webhook_port=8080,
            allowed_senders={"user1"},
            feishu_domain="https://open.larksuite.com",
        )
        assert config.app_id == "test-id"
        assert config.app_secret == "test-secret"
        assert config.verification_token == "token123"
        assert config.encrypt_key == "key123"
        assert config.webhook_port == 8080
        assert config.allowed_senders == {"user1"}
        assert config.feishu_domain == "https://open.larksuite.com"


class TestFeishuChannel:
    def test_init(self):
        config = FeishuConfig(app_id="test-id", app_secret="test-secret")
        channel = FeishuChannel(config)
        assert channel.config is config
        assert channel._running is False
        assert channel.name == "feishu"

    def test_start_raises_without_app_id(self):
        config = FeishuConfig(app_id="", app_secret="test-secret")
        channel = FeishuChannel(config)
        with pytest.raises(ChannelError, match="app_id"):
            _run(channel.start())

    def test_start_raises_without_app_secret(self):
        config = FeishuConfig(app_id="test-id", app_secret="")
        channel = FeishuChannel(config)
        with pytest.raises(ChannelError, match="app_secret"):
            _run(channel.start())

    def test_stop_when_not_running(self):
        config = FeishuConfig(app_id="test-id", app_secret="test-secret")
        channel = FeishuChannel(config)
        _run(channel.stop())

    def test_send_returns_false_without_client(self):
        from EvoScientist.channels.base import OutboundMessage

        config = FeishuConfig(app_id="test-id", app_secret="test-secret")
        channel = FeishuChannel(config)
        msg = OutboundMessage(
            channel="feishu",
            chat_id="oc_test",
            content="hello",
            metadata={"chat_id": "oc_test"},
        )
        result = _run(channel.send(msg))
        assert result is False

    def test_capabilities(self):
        from EvoScientist.channels.capabilities import FEISHU
        config = FeishuConfig()
        channel = FeishuChannel(config)
        assert channel.capabilities is FEISHU
        assert channel.capabilities.format_type == "markdown"
        assert channel.capabilities.groups is True
        assert channel.capabilities.mentions is True
        assert channel.capabilities.media_send is True
        assert channel.capabilities.media_receive is True
        assert channel.capabilities.reactions is True
        assert channel.capabilities.voice is True
        assert channel.capabilities.stickers is True

    def test_extract_post_text(self):
        content = {
            "zh_cn": {
                "title": "Test Title",
                "content": [
                    [{"tag": "text", "text": "Hello "}, {"tag": "a", "text": "world", "href": "http://example.com"}],
                    [{"tag": "text", "text": "Second line"}],
                ],
            }
        }
        result = FeishuChannel._extract_post_text(content)
        assert "Test Title" in result
        assert "Hello world" in result
        assert "Second line" in result

    def test_extract_post_text_empty(self):
        result = FeishuChannel._extract_post_text({})
        assert result == ""

    def test_strip_mention(self):
        config = FeishuConfig()
        channel = FeishuChannel(config)
        channel._mention_names = ["@_user_1"]
        result = channel._strip_mention("@_user_1 hello world")
        assert result == "hello world"


class TestFeishuMarkdownConversion:
    def test_empty_text(self):
        assert _markdown_to_feishu_post("") is None
        assert _markdown_to_feishu_post("   ") is None

    def test_plain_text(self):
        result = _markdown_to_feishu_post("Hello world")
        assert result is not None
        assert "zh_cn" in result
        content = result["zh_cn"]["content"]
        assert len(content) >= 1

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        result = _markdown_to_feishu_post(md)
        assert result is not None
        content = result["zh_cn"]["content"]
        # Should have a code_block element
        found = False
        for para in content:
            for elem in para:
                if elem.get("tag") == "code_block":
                    found = True
                    assert elem["language"] == "python"
                    assert "print" in elem["text"]
        assert found

    def test_bold_text(self):
        elements = _parse_inline_text("**bold text**")
        assert any(
            e.get("style") == ["bold"] and e["text"] == "bold text"
            for e in elements
        )

    def test_inline_code(self):
        elements = _parse_inline_text("`code`")
        assert any(
            "code_block" in (e.get("style") or []) and e["text"] == "code"
            for e in elements
        )

    def test_link(self):
        elements = _parse_inline_text("[click](http://example.com)")
        assert any(
            e.get("tag") == "a" and e["text"] == "click"
            for e in elements
        )


class TestFeishuChannelRegistration:
    def test_feishu_registered(self):
        from EvoScientist.channels.channel_manager import available_channels
        channels = available_channels()
        assert "feishu" in channels


class TestFeishuProbe:
    def test_missing_app_id(self):
        from EvoScientist.channels.feishu.probe import validate_feishu_credentials
        ok, msg = _run(validate_feishu_credentials("", "secret"))
        assert ok is False
        assert "app_id" in msg

    def test_missing_app_secret(self):
        from EvoScientist.channels.feishu.probe import validate_feishu_credentials
        ok, msg = _run(validate_feishu_credentials("id", ""))
        assert ok is False
        assert "app_secret" in msg
