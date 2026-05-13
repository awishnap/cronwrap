"""Tests for cronwrap.signal_handler."""

from __future__ import annotations

import signal
import pytest

from cronwrap.signal_handler import (
    SignalConfig,
    SignalHandler,
    ShutdownRequestedError,
)


# ---------------------------------------------------------------------------
# SignalConfig
# ---------------------------------------------------------------------------


class TestSignalConfig:
    def test_defaults(self):
        cfg = SignalConfig()
        assert cfg.handle_sigterm is True
        assert cfg.handle_sigint is True
        assert cfg.propagate_to_child is True

    def test_custom_values(self):
        cfg = SignalConfig(handle_sigterm=False, handle_sigint=False, propagate_to_child=False)
        assert cfg.handle_sigterm is False

    def test_invalid_handle_sigterm_raises(self):
        with pytest.raises(TypeError):
            SignalConfig(handle_sigterm="yes")  # type: ignore[arg-type]

    def test_invalid_handle_sigint_raises(self):
        with pytest.raises(TypeError):
            SignalConfig(handle_sigint=1)  # type: ignore[arg-type]

    def test_invalid_propagate_raises(self):
        with pytest.raises(TypeError):
            SignalConfig(propagate_to_child=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ShutdownRequestedError
# ---------------------------------------------------------------------------


class TestShutdownRequestedError:
    def test_stores_signal(self):
        err = ShutdownRequestedError(signal.SIGTERM)
        assert err.sig == signal.SIGTERM

    def test_message_contains_signal(self):
        err = ShutdownRequestedError(15)
        assert "15" in str(err)


# ---------------------------------------------------------------------------
# SignalHandler
# ---------------------------------------------------------------------------


class TestSignalHandler:
    def test_initial_state(self):
        handler = SignalHandler()
        assert handler.shutdown_requested is False
        assert handler.received_signal is None

    def test_register_and_restore(self):
        """Handlers install and uninstall without error."""
        handler = SignalHandler()
        handler.register()
        handler.restore()

    def test_context_manager(self):
        with SignalHandler() as h:
            assert isinstance(h, SignalHandler)

    def test_simulated_signal_sets_flag(self):
        handler = SignalHandler()
        handler._handle(signal.SIGTERM, None)
        assert handler.shutdown_requested is True
        assert handler.received_signal == signal.SIGTERM

    def test_raise_if_shutdown_raises_after_signal(self):
        handler = SignalHandler()
        handler._handle(signal.SIGTERM, None)
        with pytest.raises(ShutdownRequestedError) as exc_info:
            handler.raise_if_shutdown()
        assert exc_info.value.sig == signal.SIGTERM

    def test_raise_if_shutdown_silent_when_no_signal(self):
        handler = SignalHandler()
        handler.raise_if_shutdown()  # should not raise

    def test_callback_invoked_on_signal(self):
        received = []
        handler = SignalHandler()
        handler.add_callback(lambda sig: received.append(sig))
        handler._handle(signal.SIGINT, None)
        assert received == [signal.SIGINT]

    def test_multiple_callbacks(self):
        log = []
        handler = SignalHandler()
        handler.add_callback(lambda s: log.append(("a", s)))
        handler.add_callback(lambda s: log.append(("b", s)))
        handler._handle(signal.SIGTERM, None)
        assert log == [("a", signal.SIGTERM), ("b", signal.SIGTERM)]

    def test_no_sigint_handler_when_disabled(self):
        cfg = SignalConfig(handle_sigint=False)
        handler = SignalHandler(config=cfg)
        handler.register()
        assert signal.SIGINT not in handler._previous_handlers
        handler.restore()
