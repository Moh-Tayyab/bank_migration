"""
Tests for RulesEngine — business rule application.
"""
import pytest

from src.rules_engine import Rule, RulesEngine, build_standard_rules
from src.models import Record


# ===========================================================================
# Rule Tests
# ===========================================================================

class TestRule:
    """Test individual Rule application."""

    def test_rule_matches(self):
        rule = Rule(
            name="test",
            condition=lambda d: "status" in d,
            action=lambda d: {**d, "processed": True},
        )
        result = rule.apply({"status": "active"})
        assert result is not None
        assert result["processed"] is True

    def test_rule_no_match(self):
        rule = Rule(
            name="test",
            condition=lambda d: "status" in d,
            action=lambda d: {**d, "processed": True},
        )
        result = rule.apply({"name": "Test"})
        assert result is None

    def test_rule_preserves_original_on_no_match(self):
        """When condition is false, apply() returns None (not the original data)."""
        rule = Rule(
            name="test",
            condition=lambda d: False,
            action=lambda d: d,
        )
        assert rule.apply({"key": "value"}) is None


# ===========================================================================
# RulesEngine Tests
# ===========================================================================

class TestRulesEngine:
    """Test the RulesEngine container and application."""

    def test_empty_engine_returns_unchanged_data(self):
        engine = RulesEngine()
        record = Record(data={"name": "Test"}, record_id="1", source_bank="bank_a")
        result = engine.apply(record)
        assert result == {"name": "Test"}

    def test_single_global_rule(self):
        engine = RulesEngine()
        engine.add_rule(Rule(
            name="add_flag",
            condition=lambda d: True,
            action=lambda d: {**d, "flagged": True},
        ))
        record = Record(data={"name": "Test"}, record_id="1", source_bank="bank_a")
        result = engine.apply(record)
        assert result["flagged"] is True

    def test_multiple_global_rules(self):
        engine = RulesEngine()
        engine.add_rule(Rule(
            name="rule1",
            condition=lambda d: True,
            action=lambda d: {**d, "r1": True},
        ))
        engine.add_rule(Rule(
            name="rule2",
            condition=lambda d: True,
            action=lambda d: {**d, "r2": True},
        ))
        record = Record(data={}, record_id="1", source_bank="bank_a")
        result = engine.apply(record)
        assert result["r1"] is True
        assert result["r2"] is True

    def test_bank_specific_rule(self):
        engine = RulesEngine()
        engine.add_rule(
            Rule(
                name="bank_rule",
                condition=lambda d: True,
                action=lambda d: {**d, "bank_processed": True},
            ),
            bank="target_bank",
        )
        # Record with matching target_bank
        record = Record(
            data={}, record_id="1", source_bank="source_bank", target_bank="target_bank"
        )
        result = engine.apply(record)
        assert result["bank_processed"] is True

    def test_bank_specific_rule_does_not_apply_to_other_banks(self):
        engine = RulesEngine()
        engine.add_rule(
            Rule(
                name="bank_rule",
                condition=lambda d: True,
                action=lambda d: {**d, "bank_processed": True},
            ),
            bank="target_bank",
        )
        record = Record(
            data={}, record_id="1", source_bank="source_bank", target_bank="other_bank"
        )
        result = engine.apply(record)
        assert "bank_processed" not in result

    def test_rule_chaining(self):
        """Rules should apply sequentially — output of one feeds into next."""
        engine = RulesEngine()
        engine.add_rule(Rule(
            name="step1",
            condition=lambda d: "value" in d,
            action=lambda d: {**d, "value": d["value"] + 1},
        ))
        engine.add_rule(Rule(
            name="step2",
            condition=lambda d: "value" in d,
            action=lambda d: {**d, "value": d["value"] * 2},
        ))
        record = Record(data={"value": 5}, record_id="1", source_bank="bank_a")
        result = engine.apply(record)
        # (5 + 1) * 2 = 12
        assert result["value"] == 12

    def test_conditional_rule_skipped(self):
        """Rule with false condition should not modify data."""
        engine = RulesEngine()
        engine.add_rule(Rule(
            name="conditional",
            condition=lambda d: d.get("status") == "active",
            action=lambda d: {**d, "approved": True},
        ))
        record = Record(data={"status": "inactive"}, record_id="1", source_bank="bank_a")
        result = engine.apply(record)
        assert "approved" not in result

    def test_engine_copy_constructor(self):
        """RulesEngine(engine) should copy rules."""
        original = RulesEngine()
        original.add_rule(Rule(
            name="rule1",
            condition=lambda d: True,
            action=lambda d: {**d, "r1": True},
        ))
        copy = RulesEngine(original)
        record = Record(data={}, record_id="1", source_bank="bank_a")
        result = copy.apply(record)
        assert result["r1"] is True


# ===========================================================================
# Standard Rules Tests
# ===========================================================================

class TestStandardRules:
    """Test the build_standard_rules() preset."""

    def test_empty_to_null(self):
        """Empty strings should be converted to None."""
        engine = build_standard_rules()
        record = Record(
            data={"name": "", "email": "test@test.com"},
            record_id="1",
            source_bank="bank_a",
        )
        result = engine.apply(record)
        assert result["name"] is None
        assert result["email"] == "test@test.com"

    def test_strip_whitespace(self):
        """String values should be stripped."""
        engine = build_standard_rules()
        record = Record(
            data={"name": "  Test User  "},
            record_id="1",
            source_bank="bank_a",
        )
        result = engine.apply(record)
        assert result["name"] == "Test User"

    def test_capitalize_names(self):
        """Fields ending in _name should be title-cased."""
        engine = build_standard_rules()
        record = Record(
            data={"first_name": "muhammad", "last_name": "tayyab", "age": "25"},
            record_id="1",
            source_bank="bank_a",
        )
        result = engine.apply(record)
        assert result["first_name"] == "Muhammad"
        assert result["last_name"] == "Tayyab"
        assert result["age"] == "25"  # not a _name field

    def test_capitalize_names_only_when_condition_met(self):
        """capitalize_names rule only applies when a _name field exists."""
        engine = build_standard_rules()
        record = Record(
            data={"balance": "50000"},
            record_id="1",
            source_bank="bank_a",
        )
        result = engine.apply(record)
        assert result["balance"] == "50000"

    def test_non_string_values_preserved_by_strip(self):
        """Non-string values should not be affected by strip rule."""
        engine = build_standard_rules()
        record = Record(
            data={"count": 42, "active": True},
            record_id="1",
            source_bank="bank_a",
        )
        result = engine.apply(record)
        assert result["count"] == 42
        assert result["active"] is True
