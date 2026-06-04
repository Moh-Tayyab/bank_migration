# 05. Product Improvement Roadmap - Migration Engine Gaps

## CRITICAL GAPS (Must Implement Before This Migration)

### G1: Conditional Name Parsing Engine
**Why**: WorldCheck stores entity names in `last_name` when `first_name` is NULL
**Impact**: 34% of records affected
**Current State**: Not implemented
**Target State**:
```python
class ConditionalNameParser:
    """
    Parses names where entity/full name is stored in last_name field.
    Handles both person names and entity names correctly.
    """
    def parse(self, first_name: str, last_name: str) -> NameResult:
        # Returns: FullName, GivenNames, FamilyName, NameType, IsEntity
        pass
```
**Implementation**: 2 days
**Priority**: **P0**

---

### G2: Risk Scoring Matrix Engine
**Why**: Compliance requires risk-based screening prioritization
**Impact**: Cannot prioritize high-risk alerts
**Current State**: Hardcoded values
**Target State**:
```python
class RiskScoringEngine:
    """
    Configurable risk scoring matrix for category-based scoring.
    Supports:
    - Category → Score mapping
    - Sub-category boosters
    - Custom risk factors
    """
    def calculate(self, category: str, sub_category: str) -> int:
        pass
```
**Implementation**: 3 days
**Priority**: **P0**

---

### G3: Business Rule Engine for ListRecordType
**Why**: WorldCheck categories don't map 1:1 to SAN/PEP/SIP
**Impact**: Misclassification leads to compliance exposure
**Current State**: No derivation logic
**Target State**:
```python
class RecordTypeClassifier:
    """
    Derives ListRecordType from source category/sub-category.
    Configurable business rules.
    """
    RULES = [
        If(sub_category="PEP").then("PEP"),
        If(category_contains="CRIME").then("SAN"),
        If(category_contains="TERROR").then("SAN"),
        If(category="POLITICAL INDIVIDUAL").then("SIP")
    ]
```
**Implementation**: 2 days
**Priority**: **P0**

---

### G4: Mandatory Field Enforcement
**Why**: Export cannot proceed without required fields
**Impact**: Regulatory non-compliance
**Current State**: No validation
**Target State**:
```python
class MandatoryFieldValidator:
    """
    Enforces mandatory fields before export.
    Blocker-level validation.
    """
    REQUIRED_FIELDS = [
        "ListRecordId", "ListRecordType", "FullName",
        "FamilyName", "AddedDate", "LastUpdatedDate"
    ]
```
**Implementation**: 1 day
**Priority**: **P0**

---

### G5: Manual Review Queue System
**Why**: 34% of records require human review
**Impact**: Cannot safely auto-migrate all records
**Current State**: No review workflow
**Target State**:
```python
class ManualReviewQueue:
    """
    Queues records for manual review when:
    - Confidence score < threshold
    - First_name is NULL
    - Sub_category is NULL
    - Risk score is default value
    """
    def flag_for_review(self, record, reason: str):
        pass

    def get_review_queue(self) -> List[Record]:
        pass
```
**Implementation**: 3 days
**Priority**: **P0**

---

## HIGH PRIORITY GAPS (Implement in Phase 2)

### G6: Transformation Audit Trail
**Why**: Compliance requires complete transformation history
**Current State**: No logging
**Target State**:
```python
class TransformationLogger:
    """
    Logs every transformation with:
    - Timestamp
    - Source/Target values
    - Transformation applied
    - Confidence score
    """
    def log(self, transformation: Transformation):
        pass
```
**Implementation**: 2 days
**Priority**: **P1**

---

### G7: Data Confidence Calculator
**Why**: Need to quantify data quality for each record
**Current State**: No scoring
**Target State**:
```python
class ConfidenceScorer:
    """
    Calculates confidence score (0-100) based on:
    - Field completeness
    - Data validity
    - Source reliability
    """
    def calculate(self, record) -> int:
        pass
```
**Implementation**: 2 days
**Priority**: **P1**

---

### G8: Cross-Field Validation
**Why**: Catch logical inconsistencies (e.g., Updated < Added)
**Current State**: Single-field validation only
**Target State**:
```python
class CrossFieldValidator:
    """
    Validates relationships between fields:
    - LastUpdatedDate >= AddedDate
    - FullName = GivenNames + FamilyName
    - Gender consistent with entity_type
    """
```
**Implementation**: 2 days
**Priority**: **P1**

---

### G9: Entity Type Detection
**Why**: Need to distinguish persons from organizations
**Impact**: Screening logic differs by entity type
**Current State**: Assumes all are persons
**Target State**:
```python
class EntityTypeDetector:
    """
    Detects if record represents person vs entity.
    Heuristics:
    - first_name NULL + last_name = organization name
    - e-i = "E"
    - Category contains "ORGANIZATION"
    """
    def detect(self, record) -> EntityType:
        pass
```
**Implementation**: 2 days
**Priority**: **P1**

---

### G10: Sanctions List Integration
**Why**: Must cross-reference with OFAC/UN/EU lists
**Impact**: Complete AML/KYC screening
**Current State**: No integration
**Target State**:
```python
class SanctionsListValidator:
    """
    Validates against:
    - OFAC SDN List
    - UN Sanctions List
    - EU Sanctions List
    - UK Sanctions List
    Returns: Match status, confidence, list source
    """
```
**Implementation**: 5 days
**Priority**: **P1**

---

## MEDIUM PRIORITY GAPS (Phase 3)

### G11: Fuzzy Name Matching (Deduplication)
**Why**: Detect duplicate records before import
**Current State**: No deduplication
**Target State**:
```python
class FuzzyNameMatcher:
    """
    Detects potential duplicates using:
    - Levenshtein distance
    - Phonetic matching (Soundex/Metaphone)
    - Token-based similarity
    """
    def find_matches(self, record, database) -> List[Match]:
        pass
```
**Implementation**: 3 days
**Priority**: **P2**

---

### G12: PEP Hierarchy Classification
**Why**: PEP Level 1-4 determines review depth
**Current State**: Binary PEP/non-PEP only
**Target State**:
```python
class PEPHierarchyClassifier:
    """
    Classifies PEPs into:
    - Level 1: Heads of State/Gov
    - Level 2: Senior Officials
    - Level 3: Mid-level Officials
    - Level 4: Associates/Family
    """
    def classify(self, record) -> PEPLevel:
        pass
```
**Implementation**: 3 days
**Priority**: **P2**

---

### G13: Risk-Based Scoring Model UI
**Why**: Business users need to configure risk matrices
**Current State**: Hardcoded in code
**Target State**:
```python
class RiskScoringUI:
    """
    UI for configuring:
    - Category → Score mappings
    - Boosters/penalties
    - Risk thresholds
    """
```
**Implementation**: 5 days
**Priority**: **P2**

---

### G14: Custom Field Mapping Interface
**Why**: Allow business users to map CustomString fields
**Current State**: No UI
**Target State**:
```python
class CustomFieldMapper:
    """
    UI for mapping source fields to:
    - CustomString1-40
    - CustomNumber1-5
    - CustomDate1-5
    """
```
**Implementation**: 4 days
**Priority**: **P2**

---

### G15: Ongoing Monitoring Flags
**Why**: Regulatory requirement for continuous monitoring
**Current State**: No flagging
**Target State**:
```python
class OngoingMonitoringFlagger:
    """
    Flags records requiring ongoing monitoring:
    - PEPs
    - High-risk individuals
    - Recent sanctions matches
    """
    def flag(self, record) -> MonitoringStatus:
        pass
```
**Implementation**: 2 days
**Priority**: **P2**

---

## NICE-TO-HAVE GAPS (Phase 4)

### G16: Transformation Preview
**Why**: Show before/after of transformations
**Implementation**: 3 days
**Priority**: **P3**

### G17: Adverse Media Integration
**Why**: Detect negative news associations
**Implementation**: 5 days
**Priority**: **P3**

### G18: Batch Transformation Engine
**Why**: Optimize for bulk migrations
**Implementation**: 3 days
**Priority**: **P3**

### G19: Rollback & Recovery
**Why**: Ability to undo failed migrations
**Implementation**: 3 days
**Priority**: **P3**

### G20: Migration Reports Dashboard
**Why**: Visual migration status tracking
**Implementation**: 5 days
**Priority**: **P3**

---

## IMPLEMENTATION TIMELINE

### Week 1-2: Phase 1 (P0 - Critical)
- Day 1-2: G1 - Conditional Name Parser
- Day 3-5: G2 - Risk Scoring Engine
- Day 6-7: G3 - Business Rule Engine
- Day 8: G4 - Mandatory Field Validation
- Day 9-10: G5 - Manual Review Queue

**Deliverable**: Core migration capability with safety nets

### Week 3-4: Phase 2 (P1 - High Priority)
- Day 11-12: G6 - Transformation Audit Trail
- Day 13-14: G7 - Data Confidence Calculator
- Day 15-16: G8 - Cross-Field Validation
- Day 17-18: G9 - Entity Type Detection
- Day 19-23: G10 - Sanctions List Integration

**Deliverable**: Production-ready migration with compliance features

### Week 5-6: Phase 3 (P2 - Medium Priority)
- Day 24-26: G11 - Fuzzy Name Matching
- Day 27-29: G12 - PEP Hierarchy Classification
- Day 30-34: G13 - Risk Scoring UI
- Day 35-38: G14 - Custom Field Mapper
- Day 39-40: G15 - Ongoing Monitoring Flags

**Deliverable**: Enhanced business control and screening capabilities

### Week 7-8: Phase 4 (P3 - Nice-to-Have)
- Day 41-43: G16 - Transformation Preview
- Day 44-48: G17 - Adverse Media Integration
- Day 49-51: G18 - Batch Engine
- Day 52-54: G19 - Rollback & Recovery
- Day 55-59: G20 - Reports Dashboard

**Deliverable**: Full-featured enterprise migration platform

---

## RESOURCE REQUIREMENTS

| Role | Allocation | Key Tasks |
|------|------------|------------|
| Senior Backend Engineer | 100% | G1, G2, G3, G4, G5, G6, G7, G8 |
| AML/KYC Specialist | 50% | Risk matrix approval, G10 requirements |
| Compliance Officer | 25% | G3 sign-off, G10 validation |
| Frontend Engineer | 50% | G13, G14, G20 |
| QA Engineer | 75% | All gap testing |

---

## SUCCESS METRICS

| Metric | Target | Measurement |
|--------|--------|-------------|
| P0 Gaps Implemented | 100% | Code complete + tested |
| P1 Gaps Implemented | 80% | Core features working |
| Migration Success Rate | > 95% | Records migrated / total |
| Manual Review Queue | < 10% | Records requiring review |
| Data Quality Score | > 75 | Average confidence |
| Zero Data Loss | 100% | Source count = Target count |

---

## RISK MITIGATION FOR GAPS

| Gap | Risk | Mitigation |
|------|------|------------|
| G1 | Entity names mishandled | Extensive testing with sample data |
| G2 | Risk scores misaligned | Business sign-off on matrix |
| G3 | Misclassification | Manual review of edge cases |
| G5 | Review queue bottleneck | SLA for review completion |
| G10 | API rate limits | Caching, batch validation |

---

## ESTIMATION SUMMARY

| Phase | Gaps | Duration | Complexity |
|-------|------|----------|------------|
| Phase 1 (P0) | 5 | 10 days | High |
| Phase 2 (P1) | 5 | 13 days | High |
| Phase 3 (P2) | 5 | 17 days | Medium |
| Phase 4 (P3) | 5 | 19 days | Low-Medium |
| **Total** | **20** | **59 days** | - |

**Recommendation**: Prioritize Phase 1 and Phase 2 for immediate WorldCheck migration. Phase 3 and 4 can be delivered as incremental enhancements.
