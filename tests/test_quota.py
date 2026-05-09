"""Tests for cronwrap.quota."""
import pytest

from cronwrap.quota import (
    QuotaConfig,
    QuotaEnforcer,
    QuotaExceededError,
    ResourceUsage,
)


class TestQuotaConfig:
    def test_defaults(self):
        cfg = QuotaConfig()
        assert cfg.max_cpu_percent == 100.0
        assert cfg.max_memory_mb == 0.0
        assert cfg.max_disk_write_mb == 0.0
        assert cfg.enforce is True

    def test_custom_values(self):
        cfg = QuotaConfig(max_cpu_percent=50.0, max_memory_mb=512.0, max_disk_write_mb=100.0)
        assert cfg.max_cpu_percent == 50.0
        assert cfg.memory_limited is True
        assert cfg.disk_limited is True

    def test_zero_memory_is_unlimited(self):
        cfg = QuotaConfig(max_memory_mb=0.0)
        assert cfg.memory_limited is False

    def test_zero_disk_is_unlimited(self):
        cfg = QuotaConfig(max_disk_write_mb=0.0)
        assert cfg.disk_limited is False

    def test_invalid_cpu_zero_raises(self):
        with pytest.raises(ValueError, match="max_cpu_percent"):
            QuotaConfig(max_cpu_percent=0.0)

    def test_invalid_cpu_over_100_raises(self):
        with pytest.raises(ValueError, match="max_cpu_percent"):
            QuotaConfig(max_cpu_percent=101.0)

    def test_negative_memory_raises(self):
        with pytest.raises(ValueError, match="max_memory_mb"):
            QuotaConfig(max_memory_mb=-1.0)

    def test_negative_disk_raises(self):
        with pytest.raises(ValueError, match="max_disk_write_mb"):
            QuotaConfig(max_disk_write_mb=-5.0)


class TestQuotaEnforcer:
    def _enforcer(self, **kwargs) -> QuotaEnforcer:
        return QuotaEnforcer(QuotaConfig(**kwargs))

    def test_within_limits_does_not_raise(self):
        enforcer = self._enforcer(max_cpu_percent=80.0, max_memory_mb=256.0)
        usage = ResourceUsage(cpu_percent=50.0, memory_mb=128.0)
        enforcer.check(usage)  # should not raise

    def test_cpu_exceeded_raises(self):
        enforcer = self._enforcer(max_cpu_percent=50.0)
        usage = ResourceUsage(cpu_percent=75.0)
        with pytest.raises(QuotaExceededError) as exc_info:
            enforcer.check(usage)
        assert exc_info.value.resource == "cpu_percent"

    def test_memory_exceeded_raises(self):
        enforcer = self._enforcer(max_memory_mb=128.0)
        usage = ResourceUsage(memory_mb=200.0)
        with pytest.raises(QuotaExceededError) as exc_info:
            enforcer.check(usage)
        assert exc_info.value.resource == "memory_mb"

    def test_disk_exceeded_raises(self):
        enforcer = self._enforcer(max_disk_write_mb=50.0)
        usage = ResourceUsage(disk_write_mb=60.0)
        with pytest.raises(QuotaExceededError) as exc_info:
            enforcer.check(usage)
        assert exc_info.value.resource == "disk_write_mb"

    def test_enforce_false_skips_checks(self):
        enforcer = QuotaEnforcer(QuotaConfig(max_cpu_percent=10.0, enforce=False))
        usage = ResourceUsage(cpu_percent=99.0)
        enforcer.check(usage)  # should not raise

    def test_is_within_quota_true(self):
        enforcer = self._enforcer(max_cpu_percent=80.0)
        assert enforcer.is_within_quota(ResourceUsage(cpu_percent=40.0)) is True

    def test_is_within_quota_false(self):
        enforcer = self._enforcer(max_cpu_percent=30.0)
        assert enforcer.is_within_quota(ResourceUsage(cpu_percent=60.0)) is False

    def test_unlimited_memory_never_exceeds(self):
        enforcer = self._enforcer(max_memory_mb=0.0)
        usage = ResourceUsage(memory_mb=99999.0)
        enforcer.check(usage)  # should not raise
