"""Tests for MessageProcessor pause/resume functionality."""

import time
from unittest.mock import MagicMock, AsyncMock

import pytest

from wingman.core.message_processor import MessageProcessor


class TestMessageProcessorPause:
    def setup_method(self):
        self.store = MagicMock()
        self.llm = MagicMock()
        self.contact_registry = MagicMock()
        self.group_registry = MagicMock()
        self.policy_evaluator = MagicMock()

        self.processor = MessageProcessor(
            store=self.store,
            llm=self.llm,
            contact_registry=self.contact_registry,
            group_registry=self.group_registry,
            policy_evaluator=self.policy_evaluator,
        )

    def test_pause_attribute_exists(self):
        assert hasattr(self.processor, "paused")
        assert hasattr(self.processor, "pause_until")

    def test_default_not_paused(self):
        assert self.processor.paused is False
        assert self.processor.pause_until is None

    def test_pause(self):
        self.processor.paused = True
        assert self.processor.paused is True

    def test_pause_with_duration(self):
        self.processor.paused = True
        self.processor.pause_until = time.time() + 60
        assert self.processor.paused is True
        assert self.processor.pause_until is not None

    def test_resume(self):
        self.processor.paused = True
        self.processor.pause_until = time.time() + 60
        self.processor.paused = False
        self.processor.pause_until = None
        assert self.processor.paused is False

    def test_safety_check_returns_paused(self):
        self.processor.paused = True
        # Quiet hours should not be active for this test
        self.processor.quiet_hours = MagicMock()
        self.processor.quiet_hours.is_quiet_time.return_value = False

        result = self.processor._check_safety_rules("chat123")
        assert result == "paused"

    def test_safety_check_auto_resumes(self):
        self.processor.paused = True
        self.processor.pause_until = time.time() - 1  # expired

        self.processor.quiet_hours = MagicMock()
        self.processor.quiet_hours.is_quiet_time.return_value = False
        self.processor.rate_limiter = MagicMock()
        self.processor.rate_limiter.can_reply.return_value = True
        self.processor.cooldown = MagicMock()
        self.processor.cooldown.is_on_cooldown.return_value = False
        self.store.was_last_message_from_self.return_value = False

        result = self.processor._check_safety_rules("chat123")
        assert result is None  # Not paused anymore
        assert self.processor.paused is False
