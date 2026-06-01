"""
Tests for SecurityMasker — PII detection and masking.
"""

from src.audit_logger import AuditLogger
from src.security import SecurityMasker

# ===========================================================================
# Account Number Masking Tests
# ===========================================================================


class TestAccountNumberMasking:
    """Test account number and IBAN masking."""

    def test_mask_show_last_4(self, masker):
        result = masker._mask_show_last_4("1234567890123456")
        assert result == "************3456"

    def test_mask_show_last_4_short_number(self, masker):
        """Numbers with <= 4 digits should not be masked."""
        result = masker._mask_show_last_4("1234")
        assert result == "1234"

    def test_mask_show_last_4_with_dashes(self, masker):
        result = masker._mask_show_last_4("1234-5678-9012-3456")
        # Non-digit chars are preserved in position
        assert "3456" in result

    def test_mask_show_last_6(self, masker):
        result = masker._mask_show_last_6("1234567890123456")
        assert result == "**********123456"

    def test_mask_all(self, masker):
        result = masker._apply_rule("secret", "mask_all")
        assert result == "******"

    def test_mask_first_half(self, masker):
        result = masker._mask_first_half("12345678")
        assert result == "****5678"


# ===========================================================================
# Email Masking Tests
# ===========================================================================


class TestEmailMasking:
    """Test email address masking."""

    def test_mask_email_standard(self, masker):
        result = masker._mask_email("tayyab@example.com")
        assert result[0] == "t"
        assert result.split("@")[0][-1] == "b"
        assert "@" in result

    def test_mask_email_short_local(self, masker):
        result = masker._mask_email("ab@test.com")
        assert result[0] == "a"
        assert "@" in result

    def test_mask_email_single_char_local(self, masker):
        result = masker._mask_email("a@test.com")
        assert result[0] == "a"
        assert "@" in result

    def test_mask_email_invalid(self, masker):
        """Invalid email (no @) should be returned as-is."""
        result = masker._mask_email("not-an-email")
        assert result == "not-an-email"


# ===========================================================================
# Auto-Detection Tests
# ===========================================================================


class TestAutoDetection:
    """Test automatic PII detection from field names and values."""

    def test_detect_account_field(self, masker):
        rule = masker._detect_rule("account_number", "1234567890123456")
        assert rule == "show_last_4"

    def test_detect_email_field(self, masker):
        rule = masker._detect_rule("email", "test@test.com")
        assert rule == "mask_email"

    def test_detect_phone_field(self, masker):
        rule = masker._detect_rule("phone", "03001234567")
        assert rule == "show_last_4"

    def test_detect_cnic_field(self, masker):
        rule = masker._detect_rule("cnic", "3520112345678")
        assert rule == "show_last_4"

    def test_detect_ssn_field(self, masker):
        rule = masker._detect_rule("ssn", "123-45-6789")
        assert rule == "show_last_4"

    def test_detect_passport_field(self, masker):
        rule = masker._detect_rule("passport", "AB1234567")
        assert rule == "show_last_4"

    def test_detect_iban_keyword(self, masker):
        rule = masker._detect_rule("iban", "DE89370400440532013000")
        assert rule == "show_last_4"

    def test_detect_mobile_keyword(self, masker):
        rule = masker._detect_rule("mobile", "03001234567")
        assert rule == "show_last_4"

    def test_detect_email_pattern_in_value(self, masker):
        """Email pattern in value should be auto-detected."""
        rule = masker._detect_rule("contact_info", "user@example.com")
        assert rule == "mask_email"

    def test_detect_16_digit_pattern(self, masker):
        """16-digit number pattern should be auto-detected."""
        rule = masker._detect_rule("some_field", "1234567890123456")
        assert rule == "show_last_4"

    def test_detect_credit_card_format(self, masker):
        """Credit card format (4-4-4-4) should be auto-detected."""
        rule = masker._detect_rule("payment", "1234-5678-9012-3456")
        assert rule == "show_last_4"

    def test_no_pii_detected(self, masker):
        rule = masker._detect_rule("full_name", "Muhammad Tayyab")
        assert rule is None

    def test_empty_value_no_detection(self, masker):
        rule = masker._detect_rule("unknown_field", "")
        assert rule is None


# ===========================================================================
# Full Masking Pipeline Tests
# ===========================================================================


class TestMaskingPipeline:
    """Test the full mask() method."""

    def test_mask_multiple_fields(self, masker):
        data = {
            "full_name": "Muhammad Tayyab",
            "account_number": "1234567890123456",
            "email": "tayyab@example.com",
            "phone": "03001234567",
            "balance": "50000",
        }
        result = masker.mask(data, record_id="REC-001")
        assert result["full_name"] == "Muhammad Tayyab"  # not masked
        assert "3456" in result["account_number"]
        assert "@" in result["email"]
        assert "4567" in result["phone"]
        assert result["balance"] == "50000"  # not masked

    def test_mask_preserves_non_pii(self, masker):
        data = {"name": "Test", "city": "Lahore", "balance": "1000"}
        result = masker.mask(data, record_id="REC-001")
        assert result["name"] == "Test"
        assert result["city"] == "Lahore"
        assert result["balance"] == "1000"

    def test_mask_empty_data(self, masker):
        result = masker.mask({}, record_id="REC-001")
        assert result == {}

    def test_mask_with_bank_rules(self, masker):
        """Custom bank rules should override defaults."""
        masker.set_bank_rules({"balance": "show_last_4"})
        data = {"balance": "1234567890"}
        result = masker.mask(data, record_id="REC-001")
        assert "7890" in result["balance"]

    def test_mask_with_audit_logging(self, tmp_dir):
        """Masking with audit logger should log masking events."""
        from pathlib import Path

        audit = AuditLogger(migration_id="test_mask")
        audit._log_path = Path(tmp_dir) / "audit_mask.jsonl"
        m = SecurityMasker(audit_logger=audit)
        data = {"account_number": "1234567890123456", "name": "Test"}
        m.mask(data, record_id="REC-001")
        # Audit trail should have entries
        trail = audit.get_trail()
        assert len(trail) >= 1
        assert any("account_number" in entry.details for entry in trail)


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Test edge cases in masking."""

    def test_mask_unknown_rule_returns_original(self, masker):
        result = masker._apply_rule("value", "unknown_rule")
        assert result == "value"

    def test_mask_with_special_characters(self, masker):
        data = {"account_number": "1234-5678-9012-3456"}
        result = masker.mask(data, record_id="REC-001")
        assert "3456" in result["account_number"]

    def test_mask_preserves_data_types(self, masker):
        """Non-string values should be skipped."""
        data = {"count": 42, "active": True, "name": "Test"}
        result = masker.mask(data, record_id="REC-001")
        assert result["count"] == 42
        assert result["active"] is True
