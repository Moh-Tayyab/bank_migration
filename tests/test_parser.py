"""
Tests for Parser — intelligent name, date, address, and currency parsing.
"""


# ===========================================================================
# Name Parsing Tests
# ===========================================================================


class TestNameParsing:
    """Test parse_name() for various name formats."""

    def test_single_name(self, parser):
        result = parser.parse_name("Tayyab")
        assert result == {"first_name": "Tayyab", "middle_name": "", "last_name": ""}

    def test_two_part_name(self, parser):
        result = parser.parse_name("Muhammad Tayyab")
        assert result["first_name"] == "Muhammad"
        assert result["middle_name"] == ""
        assert result["last_name"] == "Tayyab"

    def test_three_part_name(self, parser):
        result = parser.parse_name("Muhammad Tayyab Khan")
        assert result["first_name"] == "Muhammad"
        assert result["middle_name"] == "Tayyab"
        assert result["last_name"] == "Khan"

    def test_four_part_name(self, parser):
        result = parser.parse_name("Muhammad Tayyab Ahmed Khan")
        assert result["first_name"] == "Muhammad"
        assert result["middle_name"] == "Tayyab Ahmed"
        assert result["last_name"] == "Khan"

    def test_empty_name(self, parser):
        result = parser.parse_name("")
        assert result == {"first_name": "", "middle_name": "", "last_name": ""}

    def test_none_name(self, parser):
        result = parser.parse_name(None)
        assert result == {"first_name": "", "middle_name": "", "last_name": ""}

    def test_whitespace_only_name(self, parser):
        result = parser.parse_name("   ")
        assert result == {"first_name": "", "middle_name": "", "last_name": ""}

    def test_extra_whitespace_between_parts(self, parser):
        result = parser.parse_name("  Muhammad   Tayyab  ")
        assert result["first_name"] == "Muhammad"
        assert result["last_name"] == "Tayyab"


# ===========================================================================
# Date Parsing Tests
# ===========================================================================


class TestDateParsing:
    """Test parse_date() for various date formats."""

    def test_iso_format(self, parser):
        result = parser.parse_date("1995-03-15")
        assert result == "15-03-1995"  # default target: DD-MM-YYYY

    def test_dmy_format(self, parser):
        result = parser.parse_date("15-03-1995")
        assert result == "15-03-1995"

    def test_mdy_format(self, parser):
        result = parser.parse_date("03/15/1995")
        assert result == "15-03-1995"

    def test_yyyy_mm_dd_format(self, parser):
        result = parser.parse_date("1995/03/15")
        assert result == "15-03-1995"

    def test_compact_format(self, parser):
        result = parser.parse_date("19950315")
        assert result == "15-03-1995"

    def test_text_month_format(self, parser):
        result = parser.parse_date("15 Mar 1995")
        assert result == "15-03-1995"

    def test_full_month_format(self, parser):
        result = parser.parse_date("15 March 1995")
        assert result == "15-03-1995"

    def test_custom_source_format(self, parser):
        result = parser.parse_date("15/03/1995", source_format="%d/%m/%Y")
        assert result == "15-03-1995"

    def test_custom_target_format(self, parser):
        result = parser.parse_date("1995-03-15", target_format="%Y/%m/%d")
        assert result == "1995/03/15"

    def test_empty_date(self, parser):
        result = parser.parse_date("")
        assert result == ""

    def test_invalid_date_returns_original(self, parser):
        result = parser.parse_date("not-a-date")
        assert result == "not-a-date"

    def test_whitespace_trimming(self, parser):
        result = parser.parse_date("  1995-03-15  ")
        assert result == "15-03-1995"


# ===========================================================================
# Address Parsing Tests
# ===========================================================================


class TestAddressParsing:
    """Test parse_address() for various address formats."""

    def test_full_address(self, parser):
        result = parser.parse_address("123 Main St, Lahore, Punjab 54000, Pakistan")
        assert result["street"] == "123 Main St"
        assert result["city"] == "Lahore"
        assert result["state"] == "Punjab"
        assert result["zip"] == "54000"
        assert result["country"] == "Pakistan"

    def test_street_only(self, parser):
        result = parser.parse_address("123 Main St")
        assert result["street"] == "123 Main St"
        assert result["city"] == ""
        assert result["state"] == ""

    def test_street_and_city(self, parser):
        result = parser.parse_address("123 Main St, Lahore")
        assert result["street"] == "123 Main St"
        assert result["city"] == "Lahore"

    def test_state_without_zip(self, parser):
        result = parser.parse_address("123 Main St, Lahore, Punjab")
        assert result["state"] == "Punjab"
        assert result["zip"] == ""

    def test_empty_address(self, parser):
        result = parser.parse_address("")
        assert result == {"street": "", "city": "", "state": "", "zip": "", "country": ""}

    def test_none_address(self, parser):
        result = parser.parse_address(None)
        assert result == {"street": "", "city": "", "state": "", "zip": "", "country": ""}


# ===========================================================================
# Currency Parsing Tests
# ===========================================================================


class TestCurrencyParsing:
    """Test parse_currency() for various currency formats."""

    def test_usd_symbol(self, parser):
        code, value = parser.parse_currency("$50000.00")
        assert code == "USD"
        assert value == 50000.00

    def test_eur_symbol(self, parser):
        code, value = parser.parse_currency("€1250.50")
        assert code == "EUR"
        assert value == 1250.50

    def test_gbp_symbol(self, parser):
        code, value = parser.parse_currency("£999.99")
        assert code == "GBP"
        assert value == 999.99

    def test_pkr_rupee_symbol(self, parser):
        code, value = parser.parse_currency("₨75000")
        assert code == "PKR"
        assert value == 75000.0

    def test_pkr_rs_prefix(self, parser):
        code, value = parser.parse_currency("Rs 75000")
        assert code == "PKR"
        assert value == 75000.0

    def test_plain_number(self, parser):
        code, value = parser.parse_currency("50000")
        assert code == ""
        assert value == 50000.0

    def test_comma_separated(self, parser):
        code, value = parser.parse_currency("50,000")
        assert value == 50000.0

    def test_comma_and_decimal(self, parser):
        code, value = parser.parse_currency("1,250.50")
        assert value == 1250.50

    def test_european_format(self, parser):
        """European format: 1.250,50 (dot=thousands, comma=decimal)."""
        code, value = parser.parse_currency("1.250,50")
        assert value == 1250.50

    def test_empty_currency(self, parser):
        code, value = parser.parse_currency("")
        assert code == ""
        assert value == 0.0

    def test_invalid_currency(self, parser):
        code, value = parser.parse_currency("abc")
        assert value == 0.0


# ===========================================================================
# parse_all() Integration Tests
# ===========================================================================


class TestParseAll:
    """Test parse_all() which combines all parsers."""

    def test_parse_all_with_full_record(self, parser):
        record = {
            "full_name": "Muhammad Tayyab",
            "dob": "1995-03-15",
            "address": "123 Main St, Lahore, Pakistan",
            "balance": "$50000",
        }
        result = parser.parse_all(record)
        assert result["first_name"] == "Muhammad"
        assert result["last_name"] == "Tayyab"
        assert result["dob"] == "15-03-1995"
        assert "street" in result
        assert "balance_currency" in result
        assert result["balance_currency"] == "USD"

    def test_parse_all_preserves_extra_fields(self, parser):
        record = {"full_name": "Test", "custom_field": "preserved"}
        result = parser.parse_all(record)
        assert result["custom_field"] == "preserved"

    def test_parse_all_with_name_field_alias(self, parser):
        """Should also detect 'name' and 'customer_name' fields."""
        record = {"name": "Ali Ahmed Khan", "dob": "1990-01-01"}
        result = parser.parse_all(record)
        assert result["first_name"] == "Ali"
        assert result["middle_name"] == "Ahmed"
        assert result["last_name"] == "Khan"

    def test_parse_all_with_custom_name_fields(self, parser):
        record = {"customer_name": "Sara Khan", "dob": "2000-01-01"}
        result = parser.parse_all(record, name_fields=["customer_name"])
        assert result["first_name"] == "Sara"
        assert result["last_name"] == "Khan"
