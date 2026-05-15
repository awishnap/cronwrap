"""Tests for cronwrap.tracing."""
import time
import pytest

from cronwrap.tracing import TracingConfig, Span, Tracer


class TestTracingConfig:
    def test_defaults(self):
        cfg = TracingConfig()
        assert cfg.enabled is True
        assert cfg.service_name == "cronwrap"
        assert cfg.max_spans == 1000

    def test_custom_values(self):
        cfg = TracingConfig(enabled=False, service_name="my-svc", max_spans=50)
        assert cfg.enabled is False
        assert cfg.service_name == "my-svc"
        assert cfg.max_spans == 50

    def test_blank_service_name_raises(self):
        with pytest.raises(ValueError, match="service_name"):
            TracingConfig(service_name="   ")

    def test_zero_max_spans_raises(self):
        with pytest.raises(ValueError, match="max_spans"):
            TracingConfig(max_spans=0)

    def test_negative_max_spans_raises(self):
        with pytest.raises(ValueError, match="max_spans"):
            TracingConfig(max_spans=-1)

    def test_invalid_enabled_type_raises(self):
        with pytest.raises(TypeError, match="enabled"):
            TracingConfig(enabled="yes")  # type: ignore


class TestSpan:
    def _make_span(self, job_name="test-job"):
        return Span(
            trace_id="abc",
            span_id="def",
            job_name=job_name,
            start_time=time.monotonic(),
        )

    def test_not_finished_initially(self):
        span = self._make_span()
        assert not span.finished
        assert span.duration_seconds is None

    def test_finish_sets_end_time(self):
        span = self._make_span()
        span.finish()
        assert span.finished
        assert span.duration_seconds is not None
        assert span.duration_seconds >= 0

    def test_finish_with_error(self):
        span = self._make_span()
        span.finish(error="something went wrong")
        assert span.error == "something went wrong"

    def test_to_dict_keys(self):
        span = self._make_span()
        span.finish()
        d = span.to_dict()
        assert "trace_id" in d
        assert "span_id" in d
        assert "job_name" in d
        assert "duration_seconds" in d
        assert "error" in d


class TestTracer:
    def test_start_span_returns_span(self):
        tracer = Tracer()
        span = tracer.start_span("my-job")
        assert span is not None
        assert span.job_name == "my-job"

    def test_disabled_returns_none(self):
        tracer = Tracer(TracingConfig(enabled=False))
        assert tracer.start_span("my-job") is None

    def test_spans_accumulate(self):
        tracer = Tracer()
        tracer.start_span("job-a")
        tracer.start_span("job-b")
        assert len(tracer.spans()) == 2

    def test_max_spans_evicts_oldest(self):
        tracer = Tracer(TracingConfig(max_spans=2))
        tracer.start_span("job-1")
        tracer.start_span("job-2")
        tracer.start_span("job-3")
        spans = tracer.spans()
        assert len(spans) == 2
        assert spans[0].job_name == "job-2"

    def test_spans_for_job_filters(self):
        tracer = Tracer()
        tracer.start_span("alpha")
        tracer.start_span("beta")
        tracer.start_span("alpha")
        assert len(tracer.spans_for_job("alpha")) == 2
        assert len(tracer.spans_for_job("beta")) == 1

    def test_clear_removes_all(self):
        tracer = Tracer()
        tracer.start_span("job")
        tracer.clear()
        assert tracer.spans() == []

    def test_tags_stored_on_span(self):
        tracer = Tracer()
        span = tracer.start_span("job", tags={"env": "prod"})
        assert span is not None
        assert span.tags["env"] == "prod"

    def test_unique_ids_per_span(self):
        tracer = Tracer()
        s1 = tracer.start_span("job")
        s2 = tracer.start_span("job")
        assert s1 is not None and s2 is not None
        assert s1.trace_id != s2.trace_id
        assert s1.span_id != s2.span_id
