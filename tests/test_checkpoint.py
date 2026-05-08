"""Tests for cronwrap.checkpoint."""
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from cronwrap.checkpoint import CheckpointConfig, Checkpoint, CheckpointManager


# ---------------------------------------------------------------------------
# CheckpointConfig
# ---------------------------------------------------------------------------
class TestCheckpointConfig:
    def test_defaults(self):
        cfg = CheckpointConfig()
        assert cfg.enabled is False
        assert cfg.ttl_seconds == 86400
        assert "/tmp" in cfg.directory

    def test_custom_values(self):
        cfg = CheckpointConfig(enabled=True, directory="/var/cp", ttl_seconds=3600)
        assert cfg.enabled is True
        assert cfg.directory == "/var/cp"
        assert cfg.ttl_seconds == 3600

    def test_zero_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl_seconds"):
            CheckpointConfig(ttl_seconds=0)

    def test_negative_ttl_raises(self):
        with pytest.raises(ValueError):
            CheckpointConfig(ttl_seconds=-1)


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------
class TestCheckpoint:
    def test_not_expired_when_fresh(self):
        cp = Checkpoint(job_name="job", data={"k": 1})
        assert not cp.is_expired(ttl_seconds=3600)

    def test_expired_when_old(self):
        old_time = time.time() - 7200
        cp = Checkpoint(job_name="job", data={}, saved_at=old_time)
        assert cp.is_expired(ttl_seconds=3600)

    def test_round_trip(self):
        cp = Checkpoint(job_name="myjob", data={"step": 3})
        restored = Checkpoint.from_dict(cp.to_dict())
        assert restored.job_name == "myjob"
        assert restored.data == {"step": 3}
        assert abs(restored.saved_at - cp.saved_at) < 1


# ---------------------------------------------------------------------------
# CheckpointManager
# ---------------------------------------------------------------------------
class TestCheckpointManager:
    def _manager(self, tmp_path, enabled=True, ttl=3600):
        cfg = CheckpointConfig(enabled=enabled, directory=str(tmp_path), ttl_seconds=ttl)
        return CheckpointManager(cfg)

    def test_save_and_load(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.save("backup_job", {"page": 5})
        cp = mgr.load("backup_job")
        assert cp is not None
        assert cp.data == {"page": 5}

    def test_load_returns_none_when_disabled(self, tmp_path):
        mgr = self._manager(tmp_path, enabled=False)
        mgr.save("job", {"x": 1})
        assert mgr.load("job") is None

    def test_load_returns_none_when_not_found(self, tmp_path):
        mgr = self._manager(tmp_path)
        assert mgr.load("nonexistent") is None

    def test_expired_checkpoint_cleared_on_load(self, tmp_path):
        mgr = self._manager(tmp_path, ttl=1)
        mgr.save("old_job", {"done": True})
        # Manually backdate the file
        import json
        p = mgr._path("old_job")
        data = json.loads(p.read_text())
        data["saved_at"] = time.time() - 7200
        p.write_text(json.dumps(data))
        assert mgr.load("old_job") is None
        assert not p.exists()

    def test_clear_removes_file(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.save("job", {})
        mgr.clear("job")
        assert not mgr._path("job").exists()

    def test_exists_true_after_save(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.save("job", {"n": 1})
        assert mgr.exists("job") is True

    def test_exists_false_before_save(self, tmp_path):
        mgr = self._manager(tmp_path)
        assert mgr.exists("missing") is False

    def test_save_noop_when_disabled(self, tmp_path):
        mgr = self._manager(tmp_path, enabled=False)
        mgr.save("job", {"x": 1})
        assert not mgr._path("job").exists()
