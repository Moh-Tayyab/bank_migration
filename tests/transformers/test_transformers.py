"""
Tests for WorldCheck transformation engine.
"""

import pytest
from datetime import datetime

from src.transformers import (
    ConditionalNameParser,
    RiskScoringEngine,
    GenderTransformer,
    RecordTypeClassifier,
    DateValidator,
    ConfidenceCalculator,
    PEPClassifier,
    WorldCheckTransformOrchestrator,
    create_orchestrator
)


# Fixtures for test data
@pytest.fixture
def person_record():
    """Sample WorldCheck record for a person."""
    return {
        "category": "POLITICAL INDIVIDUAL",
        "editor": None,
        "entered": "2000-10-16",
        "sub-category": "PEP",
        "uid": 7,
        "updated": "2023-03-09",
        "entity_type": "person",
        "e-i": "M",
        "first_name": "Bashar",
        "last_name": "AL-ASSAD"
    }


@pytest.fixture
def entity_record():
    """Sample WorldCheck record for an entity."""
    return {
        "category": "CRIME - TERROR",
        "editor": None,
        "entered": "2000-11-10",
        "sub-category": None,
        "uid": 1,
        "updated": "2022-11-15",
        "entity_type": "person",
        "e-i": "E",
        "first_name": None,
        "last_name": "REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
    }


@pytest.fixture
def incomplete_record():
    """Sample WorldCheck record with missing data."""
    return {
        "category": "INDIVIDUAL",
        "editor": None,
        "entered": "2000-10-16",
        "sub-category": None,
        "uid": 100,
        "updated": "2023-03-09",
        "entity_type": "person",
        "e-i": "M",
        "first_name": None,
        "last_name": "SMITH"
    }


class TestConditionalNameParser:
    """Tests for T1: ConditionalNameParser."""

    def test_parse_person_name(self, person_record):
        """Test parsing a person name."""
        parser = ConditionalNameParser()
        result = parser.transform(person_record)

        assert result.success is True
        assert result.data["FullName"] == "Bashar AL-ASSAD"
        assert result.data["GivenNames"] == "Bashar"
        assert result.data["FamilyName"] == "AL-ASSAD"
        assert result.data["NameType"] == "Primary Name"
        assert result.data["IsEntity"] is False

    def test_parse_entity_name(self, entity_record):
        """Test parsing an entity name."""
        parser = ConditionalNameParser()
        result = parser.transform(entity_record)

        assert result.success is True
        assert result.data["FullName"] == "REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
        assert result.data["GivenNames"] is None
        assert result.data["FamilyName"] == "REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
        assert result.data["IsEntity"] is True
        assert result.requires_review is True

    def test_incomplete_name(self, incomplete_record):
        """Test parsing with incomplete name data."""
        parser = ConditionalNameParser()
        result = parser.transform(incomplete_record)

        assert result.success is True
        assert result.data["GivenNames"] is None
        assert result.requires_review is True

    def test_missing_last_name(self):
        """Test handling of missing last_name."""
        parser = ConditionalNameParser()
        result = parser.transform({"first_name": "John", "last_name": None})

        assert result.success is False
        assert any(i["code"] == "NAME_001" for i in result.issues)


class TestRiskScoringEngine:
    """Tests for T2: RiskScoringEngine."""

    def test_terror_risk_score(self):
        """Test risk score for terror category."""
        scorer = RiskScoringEngine()
        result = scorer.transform({"category": "CRIME - TERROR", "sub-category": None})

        assert result.success is True
        assert result.data["RiskScore"] == 100
        assert result.data["RiskCategory"] == "CRITICAL"

    def test_pep_boost(self):
        """Test PEP boost to risk score."""
        scorer = RiskScoringEngine()
        result = scorer.transform({
            "category": "POLITICAL INDIVIDUAL",
            "sub-category": "PEP"
        })

        assert result.success is True
        assert result.data["RiskScore"] == 80  # 70 + 10 boost
        assert result.data["PEPBoostApplied"] is True

    def test_unknown_category_default(self):
        """Test default score for unknown category."""
        scorer = RiskScoringEngine()
        result = scorer.transform({"category": "UNKNOWN CATEGORY", "sub-category": None})

        assert result.success is True
        assert result.data["RiskScore"] == 50  # Default
        assert result.requires_review is True

    def test_financial_crime_score(self):
        """Test risk score for financial crime."""
        scorer = RiskScoringEngine()
        result = scorer.transform({"category": "CRIME - FINANCIAL", "sub-category": None})

        assert result.success is True
        assert result.data["RiskScore"] == 85


class TestGenderTransformer:
    """Tests for T3: GenderTransformer."""

    def test_male_gender(self):
        """Test male gender transformation."""
        transformer = GenderTransformer()
        result = transformer.transform({"e-i": "M"})

        assert result.success is True
        assert result.data["Gender"] == "M"

    def test_female_gender(self):
        """Test female gender transformation."""
        transformer = GenderTransformer()
        result = transformer.transform({"e-i": "F"})

        assert result.success is True
        assert result.data["Gender"] == "F"

    def test_entity_to_unknown(self):
        """Test entity value maps to Unknown."""
        transformer = GenderTransformer()
        result = transformer.transform({"e-i": "E"})

        assert result.success is True
        assert result.data["Gender"] == "U"

    def test_null_gender(self):
        """Test NULL gender defaults to Unknown."""
        transformer = GenderTransformer()
        result = transformer.transform({"e-i": None})

        assert result.success is True
        assert result.data["Gender"] == "U"


class TestRecordTypeClassifier:
    """Tests for T4: RecordTypeClassifier."""

    def test_pep_classification(self):
        """Test PEP classification."""
        classifier = RecordTypeClassifier()
        result = classifier.transform({
            "category": "POLITICAL INDIVIDUAL",
            "sub-category": "PEP"
        })

        assert result.success is True
        assert result.data["ListRecordType"] == "PEP"
        assert result.data["RuleApplied"] == "PEP Detection"

    def test_sanctions_classification(self):
        """Test sanctions classification."""
        classifier = RecordTypeClassifier()
        result = classifier.transform({
            "category": "CRIME - TERROR",
            "sub-category": None
        })

        assert result.success is True
        assert result.data["ListRecordType"] == "SAN"

    def test_sip_classification(self):
        """Test SIP classification."""
        classifier = RecordTypeClassifier()
        result = classifier.transform({
            "category": "INDIVIDUAL",
            "sub-category": None
        })

        assert result.success is True
        assert result.data["ListRecordType"] == "SIP"

    def test_missing_category(self):
        """Test handling of missing category."""
        classifier = RecordTypeClassifier()
        result = classifier.transform({"category": None, "sub-category": None})

        assert result.success is False
        assert result.requires_review is True


class TestDateValidator:
    """Tests for T5: DateValidator."""

    def test_iso_date_format(self):
        """Test ISO date format validation."""
        validator = DateValidator()
        result = validator.transform({
            "entered": "2000-10-16",
            "updated": "2023-03-09"
        })

        assert result.success is True
        assert result.data["EnteredValid"] is True
        assert result.data["UpdatedValid"] is True
        assert result.data["AddedDate"] == "2000-10-16"
        assert result.data["LastUpdatedDate"] == "2023-03-09"

    def test_european_date_format(self):
        """Test European date format."""
        validator = DateValidator()
        result = validator.transform({
            "entered": "16/10/2000",
            "updated": "09/03/2023"
        })

        assert result.success is True
        assert result.data["AddedDate"] == "2000-10-16"
        assert result.data["LastUpdatedDate"] == "2023-03-09"

    def test_invalid_date(self):
        """Test invalid date handling."""
        validator = DateValidator()
        result = validator.transform({
            "entered": "invalid-date",
            "updated": "2023-03-09"
        })

        assert result.success is False
        assert result.data["EnteredValid"] is False

    def test_date_order_validation(self):
        """Test updated >= entered validation."""
        validator = DateValidator()
        result = validator.transform({
            "entered": "2023-03-09",
            "updated": "2020-01-01"
        })

        assert result.success is False
        assert result.requires_review is True


class TestConfidenceCalculator:
    """Tests for T6: ConfidenceCalculator."""

    def test_high_confidence_complete_record(self, person_record):
        """Test high confidence for complete record."""
        calculator = ConfidenceCalculator()
        result = calculator.transform(person_record)

        assert result.success is True
        assert result.data["DataConfidenceScore"] >= 85
        assert result.data["ConfidenceCategory"] == "HIGH"
        assert result.requires_review is False

    def test_low_confidence_incomplete_record(self, incomplete_record):
        """Test low confidence for incomplete record."""
        calculator = ConfidenceCalculator()
        result = calculator.transform(incomplete_record)

        assert result.success is True
        assert result.data["DataConfidenceScore"] < 70
        assert result.requires_review is True

    def test_batch_confidence_scoring(self, person_record, incomplete_record):
        """Test batch confidence scoring."""
        calculator = ConfidenceCalculator()
        summary = calculator.calculate_batch_scores([person_record, incomplete_record])

        assert summary["total_records"] == 2
        assert "average_score" in summary
        assert "category_distribution" in summary


class TestPEPClassifier:
    """Tests for T7: PEPClassifier."""

    def test_explicit_pep(self):
        """Test explicit PEP classification."""
        classifier = PEPClassifier()
        result = classifier.transform({
            "category": "POLITICAL INDIVIDUAL",
            "sub-category": "PEP"
        })

        assert result.success is True
        assert result.data["IsPEP"] is True
        assert result.data["PEPclassification"] == "PEP"
        assert result.requires_review is True

    def test_political_individual_review_required(self):
        """Test political individual review required."""
        classifier = PEPClassifier()
        result = classifier.transform({
            "category": "POLITICAL INDIVIDUAL",
            "sub-category": None
        })

        assert result.success is True
        assert result.data["IsPEP"] is True
        assert result.data["PEPclassification"] == "PEP - Review Required"

    def test_non_pep(self):
        """Test non-PEP classification."""
        classifier = PEPClassifier()
        result = classifier.transform({
            "category": "INDIVIDUAL",
            "sub-category": None
        })

        assert result.success is True
        assert result.data["IsPEP"] is False
        assert result.data["PEPclassification"] is None

    def test_batch_pep_classification(self):
        """Test batch PEP classification."""
        classifier = PEPClassifier()
        records = [
            {"category": "POLITICAL INDIVIDUAL", "sub-category": "PEP"},
            {"category": "INDIVIDUAL", "sub-category": None}
        ]
        summary = classifier.classify_batch(records)

        assert summary["total_records"] == 2
        assert summary["pep_count"] == 1
        assert summary["pep_percentage"] == 50.0


class TestWorldCheckTransformOrchestrator:
    """Tests for the transformation orchestrator."""

    def test_full_transformation(self, person_record):
        """Test complete transformation pipeline."""
        orchestrator = create_orchestrator()
        result = orchestrator.transform(person_record)

        assert result.success is True
        assert result.target_record["ListRecordId"] == 7
        assert result.target_record["ListRecordType"] == "PEP"
        assert result.target_record["FullName"] == "Bashar AL-ASSAD"
        assert result.target_record["Gender"] == "M"
        assert len(result.transformation_log) > 0

    def test_entity_transformation(self, entity_record):
        """Test transformation of entity record."""
        orchestrator = create_orchestrator()
        result = orchestrator.transform(entity_record)

        assert result.success is True
        assert result.target_record["IsEntity"] is True
        assert result.target_record["ListRecordType"] == "SAN"
        assert result.target_record["RiskScore"] == 100

    def test_batch_transformation(self):
        """Test batch transformation."""
        orchestrator = create_orchestrator()
        records = [
            {
                "category": "POLITICAL INDIVIDUAL",
                "sub-category": "PEP",
                "uid": 1,
                "entered": "2000-01-01",
                "updated": "2023-01-01",
                "e-i": "M",
                "first_name": "John",
                "last_name": "DOE",
                "editor": None,
                "entity_type": "person"
            },
            {
                "category": "CRIME - FINANCIAL",
                "sub-category": None,
                "uid": 2,
                "entered": "2000-01-01",
                "updated": "2023-01-01",
                "e-i": "F",
                "first_name": None,
                "last_name": "ENTITY NAME",
                "editor": None,
                "entity_type": "person"
            }
        ]

        results = orchestrator.transform_batch(records)
        summary = orchestrator.get_batch_summary(results)

        assert len(results) == 2
        assert summary["total_records"] == 2
        assert summary["success_rate"] == 100.0

    def test_mandatory_field_validation(self):
        """Test mandatory field validation."""
        orchestrator = create_orchestrator()
        # Record with missing uid
        record = {
            "category": "INDIVIDUAL",
            "sub-category": None,
            "uid": None,  # Missing
            "entered": "2000-01-01",
            "updated": "2023-01-01",
            "e-i": "M",
            "first_name": "John",
            "last_name": "DOE",
            "editor": None,
            "entity_type": "person"
        }

        result = orchestrator.transform(record)

        # Should have issues about missing ListRecordId
        assert any("ListRecordId" in str(i.get("fields", "")) for i in result.issues)

    def test_custom_config(self):
        """Test orchestrator with custom configuration."""
        config = {
            "confidence_threshold": 0.80,
            "risk_config": {
                "base_scores": {
                    "POLITICAL INDIVIDUAL": 90
                }
            }
        }
        orchestrator = create_orchestrator(config)

        record = {
            "category": "POLITICAL INDIVIDUAL",
            "sub-category": None,
            "uid": 1,
            "entered": "2000-01-01",
            "updated": "2023-01-01",
            "e-i": "M",
            "first_name": "John",
            "last_name": "DOE",
            "editor": None,
            "entity_type": "person"
        }

        result = orchestrator.transform(record)

        # Should use custom risk score
        assert result.target_record["BaseScore"] == 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
