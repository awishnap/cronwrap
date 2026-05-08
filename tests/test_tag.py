"""Tests for cronwrap.tag module."""
import pytest
from cronwrap.tag import TagConfig, TagManager, TagValidationError


class TestTagConfig:
    def test_defaults(self):
        cfg = TagConfig()
        assert cfg.tags == []
        assert cfg.required_tags == []

    def test_custom_values(self):
        cfg = TagConfig(tags=["nightly", "ETL"], required_tags=["critical"])
        assert "nightly" in cfg.tags
        assert "etl" in cfg.tags  # lowercased
        assert "critical" in cfg.required_tags

    def test_tags_lowercased(self):
        cfg = TagConfig(tags=["PROD", "Staging"])
        assert cfg.tags == ["prod", "staging"]

    def test_blank_tag_raises(self):
        with pytest.raises(TagValidationError):
            TagConfig(tags=["  "])

    def test_tag_with_space_raises(self):
        with pytest.raises(TagValidationError):
            TagConfig(tags=["bad tag"])

    def test_blank_required_tag_raises(self):
        with pytest.raises(TagValidationError):
            TagConfig(required_tags=[""])


class TestTagManager:
    def _manager_with_jobs(self):
        mgr = TagManager()
        mgr.register("backup", TagConfig(tags=["nightly", "storage"]))
        mgr.register("report", TagConfig(tags=["nightly", "analytics"]))
        mgr.register("cleanup", TagConfig(tags=["weekly", "storage"]))
        return mgr

    def test_register_and_get_tags(self):
        mgr = self._manager_with_jobs()
        assert "nightly" in mgr.get_tags("backup")
        assert "storage" in mgr.get_tags("backup")

    def test_get_tags_unknown_job(self):
        mgr = TagManager()
        assert mgr.get_tags("ghost") == set()

    def test_filter_by_tag(self):
        mgr = self._manager_with_jobs()
        nightly_jobs = mgr.filter_jobs("nightly")
        assert "backup" in nightly_jobs
        assert "report" in nightly_jobs
        assert "cleanup" not in nightly_jobs

    def test_filter_by_tag_case_insensitive(self):
        mgr = self._manager_with_jobs()
        assert "backup" in mgr.filter_jobs("STORAGE")

    def test_filter_no_matches(self):
        mgr = self._manager_with_jobs()
        assert mgr.filter_jobs("nonexistent") == []

    def test_has_tag_true(self):
        mgr = self._manager_with_jobs()
        assert mgr.has_tag("cleanup", "weekly") is True

    def test_has_tag_false(self):
        mgr = self._manager_with_jobs()
        assert mgr.has_tag("cleanup", "nightly") is False

    def test_all_jobs(self):
        mgr = self._manager_with_jobs()
        jobs = mgr.all_jobs()
        assert set(jobs) == {"backup", "report", "cleanup"}

    def test_register_blank_name_raises(self):
        mgr = TagManager()
        with pytest.raises(TagValidationError):
            mgr.register("", TagConfig(tags=["x"]))

    def test_overwrite_registration(self):
        mgr = TagManager()
        mgr.register("job", TagConfig(tags=["old"]))
        mgr.register("job", TagConfig(tags=["new"]))
        assert "new" in mgr.get_tags("job")
        assert "old" not in mgr.get_tags("job")
