"""Tests for cronwrap.notifier module."""

import pytest
from unittest.mock import patch, MagicMock
from cronwrap.notifier import Notifier, NotificationConfig


class TestNotificationConfig:
    def test_valid_config(self):
        cfg = NotificationConfig(recipients=["ops@example.com"])
        assert cfg.recipients == ["ops@example.com"]
        assert cfg.smtp_host == "localhost"
        assert cfg.smtp_port == 25
        assert cfg.use_tls is False

    def test_multiple_recipients(self):
        cfg = NotificationConfig(recipients=["a@x.com", "b@x.com"])
        assert len(cfg.recipients) == 2

    def test_empty_recipients_raises(self):
        with pytest.raises(ValueError, match="At least one recipient"):
            NotificationConfig(recipients=[])

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError, match="valid email"):
            NotificationConfig(recipients=["not-an-email"])

    def test_custom_smtp_settings(self):
        cfg = NotificationConfig(
            recipients=["ops@example.com"],
            smtp_host="mail.example.com",
            smtp_port=587,
            use_tls=True,
        )
        assert cfg.smtp_host == "mail.example.com"
        assert cfg.smtp_port == 587
        assert cfg.use_tls is True


class TestNotifier:
    @pytest.fixture
    def config(self):
        return NotificationConfig(
            recipients=["ops@example.com"],
            sender="cronwrap@ci.example.com",
        )

    @pytest.fixture
    def notifier(self, config):
        return Notifier(config)

    @patch("cronwrap.notifier.smtplib.SMTP")
    def test_notify_success_sends_email(self, mock_smtp, notifier):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = notifier.notify_success("backup", 12.5, output="done")

        assert result is True
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        assert "cronwrap@ci.example.com" == call_args[0][0]
        assert "SUCCESS: backup" in call_args[0][2]

    @patch("cronwrap.notifier.smtplib.SMTP")
    def test_notify_failure_sends_email(self, mock_smtp, notifier):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = notifier.notify_failure("backup", exit_code=1,
                                         error_output="disk full", attempts=3)

        assert result is True
        call_args = mock_server.sendmail.call_args
        assert "FAILURE: backup" in call_args[0][2]
        assert "3 attempt" in call_args[0][2]
        assert "disk full" in call_args[0][2]

    @patch("cronwrap.notifier.smtplib.SMTP")
    def test_smtp_error_returns_false(self, mock_smtp, notifier):
        import smtplib
        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPException("conn refused")

        result = notifier.notify_success("backup", 1.0)

        assert result is False

    @patch("cronwrap.notifier.smtplib.SMTP")
    def test_tls_is_started_when_configured(self, mock_smtp):
        cfg = NotificationConfig(
            recipients=["ops@example.com"], use_tls=True
        )
        notifier = Notifier(cfg)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notifier.notify_success("job", 0.5)

        mock_server.starttls.assert_called_once()
