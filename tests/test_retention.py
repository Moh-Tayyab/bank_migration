import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.config import settings
from src.infrastructure.retention import CleanupReport, DataRetentionPolicy


class TestCleanupReport:
    def test_total_deleted(self):
        report = CleanupReport(uploads_deleted=5, output_deleted=3, audit_deleted=2, canonical_deleted=1)
        assert report.total_deleted == 11


class TestDataRetentionPolicy:
    def test_init_with_defaults(self):
        policy = DataRetentionPolicy()
        assert policy._upload_dir == settings.upload_dir
        assert policy._output_ttl == settings.output_ttl_hours

    def test_init_with_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = DataRetentionPolicy(
                upload_dir=Path(tmpdir) / "uploads",
                upload_ttl_hours=12,
                output_ttl_hours=24,
                dry_run=True,
            )
            assert policy._upload_ttl == 12
            assert policy._output_ttl == 24
            assert policy._dry_run is True

    def test_cleanup_dir_with_ttl_zero_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("data")
            policy = DataRetentionPolicy(output_dir=Path(tmpdir), output_ttl_hours=0)
            assert policy.cleanup_output() == 0
            assert test_file.exists()

    def test_cleanup_dir_by_age(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_file = Path(tmpdir) / "old.txt"
            old_file.write_text("old data")
            # Set modification time to 2 days ago
            two_days_ago = time.time() - (48 * 3600)
            os.utime(old_file, (two_days_ago, two_days_ago))

            new_file = Path(tmpdir) / "new.txt"
            new_file.write_text("new data")

            # Only delete files older than 24 hours
            policy = DataRetentionPolicy(output_dir=Path(tmpdir), output_ttl_hours=24)
            deleted = policy._cleanup_dir_by_age(Path(tmpdir), 24, "output")
            assert deleted == 1
            assert not old_file.exists()
            assert new_file.exists()

    def test_cleanup_dir_skips_dotfiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dotfile = Path(tmpdir) / ".secret"
            dotfile.write_text("secret key")
            normal_file = Path(tmpdir) / "normal.txt"
            normal_file.write_text("data")

            # Set both to old
            old_time = time.time() - (48 * 3600)
            os.utime(dotfile, (old_time, old_time))
            os.utime(normal_file, (old_time, old_time))

            policy = DataRetentionPolicy(output_dir=Path(tmpdir), output_ttl_hours=24)
            deleted = policy._cleanup_dir_by_age(Path(tmpdir), 24, "output")
            assert deleted == 1
            assert dotfile.exists()
            assert not normal_file.exists()

    def test_cleanup_dir_with_pattern(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = Path(tmpdir) / "audit_123.jsonl"
            audit_file.write_text("audit data")
            other_file = Path(tmpdir) / "other.txt"
            other_file.write_text("other")

            old_time = time.time() - (48 * 3600)
            os.utime(audit_file, (old_time, old_time))
            os.utime(other_file, (old_time, old_time))

            policy = DataRetentionPolicy(log_dir=Path(tmpdir), audit_ttl_hours=24)
            deleted = policy._cleanup_dir_by_age(Path(tmpdir), 24, "audit", pattern="audit_*.jsonl")
            assert deleted == 1
            assert not audit_file.exists()
            assert other_file.exists()

    def test_dry_run_does_not_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("data")

            old_time = time.time() - (48 * 3600)
            os.utime(test_file, (old_time, old_time))

            policy = DataRetentionPolicy(output_dir=Path(tmpdir), output_ttl_hours=24, dry_run=True)
            deleted = policy._cleanup_dir_by_age(Path(tmpdir), 24, "output")
            assert deleted == 1
            assert test_file.exists()

    def test_cleanup_nonexistent_dir(self):
        policy = DataRetentionPolicy(upload_dir=Path("/nonexistent/path"), upload_ttl_hours=24)
        assert policy.cleanup_uploads() == 0


class TestCanonicalStoreCleanup:
    def test_cleanup_with_ttl_zero_disabled(self):
        with patch("src.canonical_store.CanonicalStore"):
            policy = DataRetentionPolicy(canonical_ttl_hours=0)
            assert policy.cleanup_canonical_store() == 0

    def test_cleanup_with_db(self):
        with patch("src.canonical_store.CanonicalStore") as MockStore:
            mock_store = Mock()
            mock_store._db_available = True
            mock_store.db = Mock()
            mock_store.db.execute = Mock(
                return_value=[
                    {"record_id": "old1"},
                    {"record_id": "old2"},
                ]
            )
            mock_store.delete = Mock()
            MockStore.return_value = mock_store

            policy = DataRetentionPolicy(canonical_ttl_hours=72)
            deleted = policy._cleanup_canonical_store(mock_store)
            assert deleted == 2
            assert mock_store.delete.call_count == 2

    def test_cleanup_in_memory_store(self):
        with patch("src.canonical_store.CanonicalStore") as MockStore:
            mock_store = Mock()
            mock_memory = Mock()
            mock_memory._records = {"rec1": {}, "rec2": {}, "rec3": {}}
            mock_store._memory_store = mock_memory
            mock_store._db_available = False
            mock_store.list_records = Mock(return_value=["rec1", "rec2", "rec3"])
            mock_store.delete = Mock()
            MockStore.return_value = mock_store

            policy = DataRetentionPolicy(canonical_ttl_hours=72)
            deleted = policy._cleanup_canonical_store(mock_store)
            assert deleted == 3
            mock_store.delete.assert_any_call("rec1")
            mock_store.delete.assert_any_call("rec2")
            mock_store.delete.assert_any_call("rec3")

    def test_clear_in_memory_store_static_method(self):
        mock_store = Mock()
        mock_memory = Mock()
        mock_memory._records = {"rec1": {}, "rec2": {}}
        mock_store._memory_store = mock_memory

        count = DataRetentionPolicy.clear_in_memory_store(mock_store)
        assert count == 2
        assert len(mock_memory._records) == 0


class TestRunAll:
    def test_run_all_returns_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir).joinpath("old.txt").write_text("old")
            old_time = time.time() - (48 * 3600)
            os.utime(Path(tmpdir) / "old.txt", (old_time, old_time))

            policy = DataRetentionPolicy(
                output_dir=Path(tmpdir),
                output_ttl_hours=24,
                upload_ttl_hours=0,
                audit_ttl_hours=0,
                canonical_ttl_hours=0,
            )
            report = policy.run_all()
            assert report.output_deleted == 1
            assert report.uploads_deleted == 0
