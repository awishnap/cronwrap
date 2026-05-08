"""Tests for cronwrap.output_capture."""
import pytest

from cronwrap.output_capture import CapturedOutput, OutputCapture, OutputConfig


class TestOutputConfig:
    def test_defaults(self):
        cfg = OutputConfig()
        assert cfg.max_bytes == 65536
        assert cfg.capture_stdout is True
        assert cfg.capture_stderr is True
        assert cfg.encoding == "utf-8"

    def test_custom_values(self):
        cfg = OutputConfig(max_bytes=1024, capture_stderr=False, encoding="latin-1")
        assert cfg.max_bytes == 1024
        assert cfg.capture_stderr is False

    def test_negative_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes"):
            OutputConfig(max_bytes=-1)

    def test_zero_max_bytes_allowed(self):
        cfg = OutputConfig(max_bytes=0)
        assert cfg.max_bytes == 0

    def test_blank_encoding_raises(self):
        with pytest.raises(ValueError, match="encoding"):
            OutputConfig(encoding="")


class TestCapturedOutput:
    def test_combined_both_streams(self):
        out = CapturedOutput(stdout="hello", stderr="oops")
        combined = out.combined()
        assert "hello" in combined
        assert "oops" in combined
        assert "stderr" in combined

    def test_combined_stdout_only(self):
        out = CapturedOutput(stdout="only stdout", stderr="")
        assert out.combined() == "only stdout"

    def test_combined_stderr_only(self):
        out = CapturedOutput(stdout="", stderr="only stderr")
        assert out.combined() == "only stderr"

    def test_is_empty_true(self):
        assert CapturedOutput().is_empty() is True

    def test_is_empty_false(self):
        assert CapturedOutput(stdout="x").is_empty() is False

    def test_to_dict_keys(self):
        d = CapturedOutput(stdout="a", stderr="b", truncated=True).to_dict()
        assert set(d.keys()) == {"stdout", "stderr", "truncated"}
        assert d["truncated"] is True


class TestOutputCapture:
    def _capture(self, cfg=None):
        return OutputCapture(cfg)

    def test_basic_capture(self):
        cap = self._capture()
        result = cap.process(b"hello", b"world")
        assert result.stdout == "hello"
        assert result.stderr == "world"
        assert result.truncated is False

    def test_none_bytes_gives_empty_strings(self):
        cap = self._capture()
        result = cap.process(None, None)
        assert result.is_empty()

    def test_capture_stdout_disabled(self):
        cfg = OutputConfig(capture_stdout=False)
        result = OutputCapture(cfg).process(b"ignored", b"kept")
        assert result.stdout == ""
        assert result.stderr == "kept"

    def test_capture_stderr_disabled(self):
        cfg = OutputConfig(capture_stderr=False)
        result = OutputCapture(cfg).process(b"kept", b"ignored")
        assert result.stdout == "kept"
        assert result.stderr == ""

    def test_truncation_triggered(self):
        cfg = OutputConfig(max_bytes=10)
        long_out = b"A" * 20
        result = OutputCapture(cfg).process(long_out, b"")
        assert result.truncated is True
        assert len(result.stdout.encode("utf-8")) <= 10

    def test_no_truncation_within_limit(self):
        cfg = OutputConfig(max_bytes=100)
        result = OutputCapture(cfg).process(b"short", b"also short")
        assert result.truncated is False

    def test_default_config_used_when_none(self):
        cap = OutputCapture(None)
        result = cap.process(b"ok", b"err")
        assert result.stdout == "ok"
