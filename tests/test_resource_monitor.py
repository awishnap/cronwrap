"""Tests for cronwrap.resource_monitor."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from cronwrap.resource_monitor import ResourceMonitor, ResourceSnapshot, ResourceSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(cpu: float = 10.0, rss: int = 50 * 1024 * 1024, vms: int = 100 * 1024 * 1024) -> ResourceSnapshot:
    return ResourceSnapshot(timestamp=0.0, cpu_percent=cpu, memory_rss_bytes=rss, memory_vms_bytes=vms)


# ---------------------------------------------------------------------------
# ResourceSnapshot
# ---------------------------------------------------------------------------

class TestResourceSnapshot:
    def test_memory_rss_mb_conversion(self):
        snap = _make_snapshot(rss=10 * 1024 * 1024)
        assert snap.memory_rss_mb == pytest.approx(10.0)

    def test_zero_rss(self):
        snap = _make_snapshot(rss=0)
        assert snap.memory_rss_mb == 0.0


# ---------------------------------------------------------------------------
# ResourceSummary
# ---------------------------------------------------------------------------

class TestResourceSummary:
    def test_empty_summary_returns_zeros(self):
        summary = ResourceSummary(job_name="test")
        assert summary.peak_memory_rss_mb == 0.0
        assert summary.avg_cpu_percent == 0.0
        assert summary.peak_cpu_percent == 0.0

    def test_peak_memory_rss_mb(self):
        summary = ResourceSummary(
            job_name="test",
            snapshots=[_make_snapshot(rss=20 * 1024 * 1024), _make_snapshot(rss=50 * 1024 * 1024)],
        )
        assert summary.peak_memory_rss_mb == pytest.approx(50.0)

    def test_avg_cpu_percent(self):
        summary = ResourceSummary(
            job_name="test",
            snapshots=[_make_snapshot(cpu=10.0), _make_snapshot(cpu=30.0)],
        )
        assert summary.avg_cpu_percent == pytest.approx(20.0)

    def test_peak_cpu_percent(self):
        summary = ResourceSummary(
            job_name="test",
            snapshots=[_make_snapshot(cpu=5.0), _make_snapshot(cpu=80.0)],
        )
        assert summary.peak_cpu_percent == pytest.approx(80.0)

    def test_to_dict_keys(self):
        summary = ResourceSummary(job_name="myjob")
        d = summary.to_dict()
        assert d["job_name"] == "myjob"
        assert "peak_memory_rss_mb" in d
        assert "avg_cpu_percent" in d
        assert "peak_cpu_percent" in d
        assert d["sample_count"] == 0


# ---------------------------------------------------------------------------
# ResourceMonitor
# ---------------------------------------------------------------------------

class TestResourceMonitor:
    def test_invalid_interval_raises(self):
        with pytest.raises(ValueError, match="interval must be positive"):
            ResourceMonitor("job", interval=0)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError):
            ResourceMonitor("job", interval=-1.0)

    def test_poll_returns_snapshot_with_psutil(self):
        mem_mock = MagicMock(rss=30 * 1024 * 1024, vms=60 * 1024 * 1024)
        proc_mock = MagicMock()
        proc_mock.memory_info.return_value = mem_mock
        proc_mock.cpu_percent.return_value = 25.0

        with patch("cronwrap.resource_monitor.psutil") as psutil_mock:
            psutil_mock.Process.return_value = proc_mock
            monitor = ResourceMonitor("job", pid=1234)
            snap = monitor.poll()

        assert snap is not None
        assert snap.cpu_percent == 25.0
        assert snap.memory_rss_mb == pytest.approx(30.0)

    def test_poll_returns_none_on_error(self):
        with patch("cronwrap.resource_monitor.psutil") as psutil_mock:
            psutil_mock.Process.side_effect = Exception("no such process")
            monitor = ResourceMonitor("job", pid=9999)
            result = monitor.poll()
        assert result is None

    def test_summary_reflects_polls(self):
        mem_mock = MagicMock(rss=10 * 1024 * 1024, vms=20 * 1024 * 1024)
        proc_mock = MagicMock()
        proc_mock.memory_info.return_value = mem_mock
        proc_mock.cpu_percent.return_value = 5.0

        with patch("cronwrap.resource_monitor.psutil") as psutil_mock:
            psutil_mock.Process.return_value = proc_mock
            monitor = ResourceMonitor("job", pid=1)
            monitor.poll()
            monitor.poll()

        summary = monitor.summary()
        assert summary.job_name == "job"
        assert len(summary.snapshots) == 2

    def test_reset_clears_snapshots(self):
        monitor = ResourceMonitor("job")
        monitor._snapshots.append(_make_snapshot())
        monitor.reset()
        assert monitor.summary().snapshots == []
