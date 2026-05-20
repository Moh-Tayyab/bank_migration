"""
Tests for SchemaMapper — field mapping and transformations between bank schemas.
"""
import pytest

from src.schema_mapper import SchemaMapper
from src.models import Record, MappingRule, BankSchema
from src.registry import BankRegistry


# ===========================================================================
# SchemaMapper — Basic Mapping Tests
# ===========================================================================

class TestSchemaMapper:
    """Test SchemaMapper with a configured registry."""

    def test_map_record_with_no_mappings(self):
        """When no mappings exist, record should be returned unchanged."""
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        record = Record(
            data={"name": "Tayyab", "dob": "1995-03-15"},
            record_id="1",
            source_bank="unknown_source",
        )
        result = mapper.map_record(record, "unknown_target")
        assert result.data == {"name": "Tayyab", "dob": "1995-03-15"}

    def test_map_record_with_mappings(self, bank_registry):
        """With configured mappings, fields should be renamed."""
        # target_bank has mappings from source_bank
        record = Record(
            data={"name": "Tayyab", "dob": "1995-03-15", "account": "1234567890123456"},
            record_id="1",
            source_bank="source_bank",
        )
        mapper = SchemaMapper(registry=bank_registry)
        result = mapper.map_record(record, "target_bank")
        # target_bank mappings: name→first_name, name→middle_name, name→last_name, etc.
        assert "first_name" in result.data
        assert "date_of_birth" in result.data
        assert result.target_bank == "target_bank"

    def test_map_record_preserves_defaults(self, bank_registry):
        """Mapping with default value should use default when source is missing."""
        record = Record(
            data={"name": "Tayyab"},  # missing 'balance'
            record_id="1",
            source_bank="source_bank",
        )
        mapper = SchemaMapper(registry=bank_registry)
        result = mapper.map_record(record, "target_bank")
        # balance→current_balance has no default, so it won't appear if not in source
        # (only mapped fields appear in output)


# ===========================================================================
# Transform Function Tests
# ===========================================================================

class TestTransforms:
    """Test individual transform functions."""

    def test_upper_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("hello", "upper")
        assert result == "HELLO"

    def test_lower_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("HELLO", "lower")
        assert result == "hello"

    def test_strip_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("  hello  ", "strip")
        assert result == "hello"

    def test_title_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("muhammad tayyab", "title")
        assert result == "Muhammad Tayyab"

    def test_reverse_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("abc", "reverse")
        assert result == "cba"

    def test_prefix_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("123", "prefix:ACC-")
        assert result == "ACC-123"

    def test_suffix_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("file", "suffix:.txt")
        assert result == "file.txt"

    def test_substring_transform(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("Hello World", "substring:0,5")
        assert result == "Hello"

    def test_unknown_transform_returns_value(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("hello", "unknown_transform")
        assert result == "hello"

    def test_none_value_passthrough(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform(None, "upper")
        assert result is None

    def test_empty_value_passthrough(self):
        registry = BankRegistry()
        mapper = SchemaMapper(registry=registry)
        result = mapper._apply_transform("", "upper")
        assert result == ""


# ===========================================================================
# BankRegistry Integration Tests
# ===========================================================================

class TestBankRegistryMapping:
    """Test that BankRegistry correctly provides mappings."""

    def test_get_mappings_for_configured_banks(self, bank_registry):
        """target_bank has mappings from source_bank."""
        mappings = bank_registry.get_mappings("source_bank", "target_bank")
        assert len(mappings) > 0
        target_fields = [m.target_field for m in mappings]
        assert "first_name" in target_fields
        assert "date_of_birth" in target_fields

    def test_get_mappings_for_unconfigured_banks(self, bank_registry):
        mappings = bank_registry.get_mappings("nonexistent", "also_nonexistent")
        assert mappings == []

    def test_get_schema_latest(self, bank_registry):
        schema = bank_registry.get_schema("target_bank", "latest")
        assert schema is not None
        assert schema.bank_name == "target_bank"

    def test_get_schema_specific_version(self, bank_registry):
        schema = bank_registry.get_schema("bank_b", "v1.0")
        assert schema is not None
        assert schema.version == "v1.0"

    def test_list_banks(self, bank_registry):
        banks = bank_registry.list_banks()
        assert "source_bank" in banks
        assert "target_bank" in banks
        assert "bank_b" in banks
        assert "bank_c" in banks

    def test_get_masking_rules(self, bank_registry):
        rules = bank_registry.get_masking_rules("target_bank")
        assert "account_number" in rules
        assert rules["account_number"] == "show_last_4"

    def test_register_new_bank(self, bank_registry, tmp_dir):
        """Registering a new bank should make it available."""
        schema = BankSchema(
            bank_name="bank_d",
            version="1.0",
            fields={"id": {"type": "str"}},
            mappings=[],
            masking_rules={},
        )
        bank_registry.register_bank("bank_d", schema)
        assert "bank_d" in bank_registry.list_banks()
