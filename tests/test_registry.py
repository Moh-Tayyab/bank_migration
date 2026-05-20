"""
Tests for BankRegistry — bank schema registration and versioning.
"""
import os
import json
import pytest

from src.registry import BankRegistry
from src.models import BankSchema, MappingRule
from src.schema_version import SchemaVersionManager


# ===========================================================================
# BankRegistry Tests
# ===========================================================================

class TestBankRegistry:
    """Test BankRegistry with the configured bank schemas."""

    def test_list_banks(self, bank_registry):
        banks = bank_registry.list_banks()
        assert isinstance(banks, list)
        assert len(banks) >= 4  # source_bank, target_bank, bank_b, bank_c

    def test_get_schema_source_bank(self, bank_registry):
        schema = bank_registry.get_schema("source_bank")
        assert schema is not None
        assert schema.bank_name == "source_bank"
        assert "name" in schema.fields
        assert "dob" in schema.fields

    def test_get_schema_target_bank(self, bank_registry):
        schema = bank_registry.get_schema("target_bank")
        assert schema is not None
        assert schema.bank_name == "target_bank"
        assert "first_name" in schema.fields
        assert "date_of_birth" in schema.fields

    def test_get_schema_nonexistent_bank(self, bank_registry):
        schema = bank_registry.get_schema("nonexistent_bank")
        assert schema is None

    def test_get_schema_specific_version(self, bank_registry):
        schema = bank_registry.get_schema("bank_b", "v1.0")
        assert schema is not None
        assert schema.version == "v1.0"

    def test_get_schema_latest(self, bank_registry):
        """'latest' should return the last loaded version."""
        schema = bank_registry.get_schema("bank_b", "latest")
        assert schema is not None

    def test_get_mappings_source_to_target(self, bank_registry):
        mappings = bank_registry.get_mappings("source_bank", "target_bank")
        assert len(mappings) > 0
        source_fields = [m.source_field for m in mappings]
        target_fields = [m.target_field for m in mappings]
        assert "name" in source_fields
        assert "first_name" in target_fields

    def test_get_mappings_bank_b(self, bank_registry):
        mappings = bank_registry.get_mappings("source_bank", "bank_b")
        assert len(mappings) > 0

    def test_get_mappings_bank_c(self, bank_registry):
        mappings = bank_registry.get_mappings("source_bank", "bank_c")
        assert len(mappings) > 0
        # bank_c uses upper transform for email
        email_mapping = [m for m in mappings if m.source_field == "email"]
        assert len(email_mapping) > 0
        assert email_mapping[0].transform == "upper"

    def test_get_mappings_nonexistent(self, bank_registry):
        mappings = bank_registry.get_mappings("nonexistent", "also_nonexistent")
        assert mappings == []

    def test_get_masking_rules_target_bank(self, bank_registry):
        rules = bank_registry.get_masking_rules("target_bank")
        assert "account_number" in rules
        assert rules["account_number"] == "show_last_4"
        assert "email" in rules
        assert rules["email"] == "mask_email"

    def test_get_masking_rules_bank_c(self, bank_registry):
        rules = bank_registry.get_masking_rules("bank_c")
        assert "account_id" in rules
        assert rules["account_id"] == "show_last_6"

    def test_get_masking_rules_nonexistent(self, bank_registry):
        rules = bank_registry.get_masking_rules("nonexistent")
        assert rules == {}

    def test_register_new_bank(self, bank_registry, tmp_dir):
        schema = BankSchema(
            bank_name="test_bank",
            version="1.0",
            fields={"id": {"type": "str"}, "name": {"type": "str"}},
            mappings=[
                MappingRule(source_field="name", target_field="full_name"),
            ],
            masking_rules={"id": "show_last_4"},
        )
        path = bank_registry.register_bank("test_bank", schema)
        assert os.path.exists(path)
        assert "test_bank" in bank_registry.list_banks()

    def test_register_bank_persists_schema(self, bank_registry, tmp_dir):
        """Registered bank should be loadable from disk."""
        schema = BankSchema(
            bank_name="persistent_bank",
            version="2.0",
            fields={"field1": {"type": "str"}},
            mappings=[],
            masking_rules={},
        )
        bank_registry.register_bank("persistent_bank", schema)
        loaded = bank_registry.get_schema("persistent_bank", "2.0")
        assert loaded is not None
        assert loaded.bank_name == "persistent_bank"


# ===========================================================================
# SchemaVersionManager Tests
# ===========================================================================

class TestSchemaVersionManager:
    """Test schema versioning."""

    def test_save_and_load_schema(self, tmp_dir):
        manager = SchemaVersionManager(registry_path=tmp_dir)
        schema_data = {
            "fields": {"name": {"type": "str"}},
            "mappings": [],
            "masking_rules": {},
        }
        path = manager.save_schema("test_bank", "1.0", schema_data)
        assert os.path.exists(path)
        loaded = manager.load_schema("test_bank", "1.0")
        assert loaded == schema_data

    def test_load_nonexistent_schema(self, tmp_dir):
        manager = SchemaVersionManager(registry_path=tmp_dir)
        result = manager.load_schema("nonexistent", "1.0")
        assert result is None

    def test_list_versions(self, tmp_dir):
        manager = SchemaVersionManager(registry_path=tmp_dir)
        manager.save_schema("bank_x", "1.0", {"fields": {}})
        manager.save_schema("bank_x", "2.0", {"fields": {}})
        versions = manager.list_versions("bank_x")
        assert "1.0" in versions
        assert "2.0" in versions

    def test_list_versions_nonexistent_bank(self, tmp_dir):
        manager = SchemaVersionManager(registry_path=tmp_dir)
        versions = manager.list_versions("nonexistent")
        assert versions == []

    def test_migrate_schema(self, tmp_dir):
        manager = SchemaVersionManager(registry_path=tmp_dir)
        v1 = {
            "fields": {"name": {"type": "str"}},
        }
        v2 = {
            "fields": {"full_name": {"type": "str", "migrated_from": "name"}},
        }
        manager.save_schema("bank_m", "1.0", v1)
        manager.save_schema("bank_m", "2.0", v2)
        record = {"name": "Tayyab"}
        migrated = manager.migrate_schema("bank_m", "1.0", "2.0", record)
        assert "full_name" in migrated
        assert migrated["full_name"] == "Tayyab"

    def test_migrate_schema_missing_version_raises(self, tmp_dir):
        manager = SchemaVersionManager(registry_path=tmp_dir)
        with pytest.raises(ValueError, match="not found"):
            manager.migrate_schema("bank", "1.0", "2.0", {})
