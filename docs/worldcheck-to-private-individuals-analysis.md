# WorldCheck to Private Individuals Schema Migration Analysis

**Date**: 2026-06-03
**Analyst**: Senior Data Architect / AML-KYC Specialist
**Source**: WorldCheck (50 records, 10 columns)
**Target**: Private Individuals (93 columns)

---

## Executive Summary

**Critical Finding**: This is NOT a standard customer data migration. This is a **high-risk AML/KYC screening data migration** from WorldCheck (Refinitiv sanctions/watchlist database) to an internal bank screening system.

| Dimension | Assessment |
|-----------|-------------|
| Schema Complexity | **HIGH** - Target has 93 fields vs Source 10 fields (83% data gap) |
| Mapping Complexity | **CRITICAL** - Multiple semantic transformations required |
| Data Quality Risk | **SEVERE** - 34% missing first names, 100% missing editor field |
| AML Compliance Risk | **CRITICAL** - Missing validation for sanctions, PEP, and risk scoring |
| Auto-mappability | **LOW** - Only 20% of fields can be safely auto-mapped |

---

## 1. Mapping Table with Confidence Scores

### 1.1 HIGH CONFIDENCE AUTO-MAPPINGS (Confidence: 90-100%)

| Source Field | Target Field | Transformation | Confidence | Mandatory | Notes |
|--------------|--------------|----------------|------------|-----------|-------|
| `uid` | `ListRecordId` | Direct copy | 100% | Yes | Unique identifier - critical for audit trail |
| `updated` | `LastUpdatedDate` | Date format validation | 95% | Yes | Requires ISO 8601 format validation |
| `entered` | `AddedDate` | Date format validation | 95% | Yes | Requires ISO 8601 format validation |

### 1.2 MEDIUM CONFIDENCE MAPPINGS (Confidence: 60-89%)

| Source Field | Target Field | Transformation | Confidence | Mandatory | Notes |
|--------------|--------------|----------------|------------|-----------|-------|
| `first_name` | `GivenNames` | Trim + uppercase standardization | 85% | Conditional | 34% NULL in source |
| `last_name` | `FamilyName` | Trim + uppercase standardization | 85% | Yes | **CRITICAL**: May contain full entity name when first_name is NULL |
| `first_name + last_name` | `FullName` | Concatenate with space | 80% | Yes | Use as fallback for entity names |
| `first_name + last_name` | `PrimaryName` | Copy from FullName | 80% | Yes | Primary name for search |
| `sub-category` | `PEPclassification` | Direct copy (when "PEP") | 75% | Yes | Only 66% populated |
| `e-i` | `Gender` | M→Male, F→Female, E→Unknown | 70% | No | E=Entity requires special handling |
| `category` | `CustomString1` | Direct copy | 70% | No | Store for reference |

### 1.3 LOW/NO CONFIDENCE (Requires Manual Review)

| Source Field | Target Field | Why No Auto-Map | Action Required |
|--------------|--------------|-----------------|-----------------|
| `category` | `RiskScore` | Category is TEXT, RiskScore is NUMBER | Manual risk scoring matrix required |
| `category` | `ListRecordType` | WorldCheck categories don't map 1:1 to SAN/PEP/SIP | Manual mapping table needed |
| `editor` | ANY | 100% NULL in source | **DO NOT MAP** - Drop field |
| `entity_type` | `ListRecordType` | Source only has "person" - need logic for entities | Conditional mapping |

### 1.4 DERIVED FIELDS (Computed Values)

| Target Field | Derivation Logic | Source Fields |
|--------------|-----------------|---------------|
| `ListSubKey` | Constant: "Private" | N/A |
| `ListRecordType` | Logic: IF sub-category="PEP" THEN "PEP" ELSE "SAN" | category, sub-category |
| `ListRecordOrigin` | Constant: "WORLDCHECK" | N/A |
| `RiskScore` | Matrix: CRIME→90, POLITICAL→85, INDIVIDUAL→50 | category |
| `NameType` | Constant: "Primary Name" | N/A |
| `DataConfidenceScore` | Logic: IF first_name IS NULL THEN 60 ELSE 85 | first_name |

---

## 2. Validation Rules Per Critical Field

### 2.1 Identity Fields (CRITICAL FOR AML)

| Target Field | Validation Rule | Error Level |
|--------------|-----------------|-------------|
| `ListRecordId` | Must be unique, integer > 0 | **BLOCKER** |
| `FullName` | Must NOT be empty or whitespace only | **BLOCKER** |
| `GivenNames` | Required IF entity_type = "person" | **HIGH** |
| `FamilyName` | Must NOT be empty | **BLOCKER** |
| `PrimaryName` | Must equal FullName | **HIGH** |

### 2.2 Classification Fields (CRITICAL FOR SANCTIONS)

| Target Field | Validation Rule | Error Level |
|--------------|-----------------|-------------|
| `ListRecordType` | Must be in: [SAN, PEP, SIP, SOE] | **BLOCKER** |
| `PEPclassification` | Required IF ListRecordType = "PEP" | **BLOCKER** |
| `RiskScore` | Must be 0-100 | **HIGH** |
| `Gender` | Must be in: [M, F, U, E] | **MEDIUM** |

### 2.3 Date Fields (CRITICAL FOR AUDIT)

| Target Field | Validation Rule | Error Level |
|--------------|-----------------|-------------|
| `AddedDate` | Must be valid ISO date <= today | **BLOCKER** |
| `LastUpdatedDate` | Must be valid ISO date <= today | **BLOCKER** |
| `LastUpdatedDate` | Must be >= AddedDate | **BLOCKER** |

### 2.4 Custom Fields (Optional)

| Target Field | Validation Rule | Error Level |
|--------------|-----------------|-------------|
| `CustomString1-40` | Max length 255 chars | **LOW** |
| `CustomNumber1-5` | Must be numeric | **LOW** |

---

## 3. Transformation Rules

### 3.1 Name Parsing (COMPLEX)

```python
def transform_name(first_name, last_name):
    """
    CRITICAL: WorldCheck has dirty name data
    - When first_name is NULL, last_name contains FULL ENTITY NAME
    - Example: first_name=NULL, last_name="REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
    """
    if pd.isna(first_name) or first_name.strip() == "":
        # Entity name stored in last_name
        return {
            "FullName": last_name.strip(),
            "GivenNames": None,
            "FamilyName": last_name.strip(),
            "NameType": "Entity Name"
        }
    else:
        # Person name split across fields
        return {
            "FullName": f"{first_name.strip()} {last_name.strip()}",
            "GivenNames": first_name.strip(),
            "FamilyName": last_name.strip(),
            "NameType": "Primary Name"
        }
```

### 3.2 Category-to-RiskScore Mapping

```python
def calculate_risk_score(category):
    """
    Risk scoring based on WorldCheck category
    Values: 0-100 where 100 = highest risk
    """
    risk_matrix = {
        "CRIME - TERROR": 100,
        "NONCONVICTION TERROR": 95,
        "CRIME - WAR": 90,
        "CRIME - FINANCIAL": 85,
        "POLITICAL INDIVIDUAL": 70,
        "INDIVIDUAL": 50
    }
    return risk_matrix.get(category, 50)  # Default: Medium risk
```

### 3.3 Gender Transformation

```python
def transform_gender(ei_value):
    """
    WorldCheck 'e-i' field: E=Entity, I=Individual (with M/F subcode)
    """
    if ei_value == "M":
        return "M"  # Male
    elif ei_value == "F":
        return "F"  # Female
    elif ei_value == "E":
        return "U"  # Unknown/Entity
    else:
        return "U"  # Default to Unknown
```

### 3.4 ListRecordType Derivation

```python
def derive_record_type(category, sub_category):
    """
    Derive SAN/PEP classification for screening system
    """
    if sub_category == "PEP":
        return "PEP"  # Politically Exposed Person
    elif "CRIME" in category or "TERROR" in category:
        return "SAN"  # Sanctions
    else:
        return "SIP"  # Special Interest Person
```

---

## 4. Data Quality Risks in Source File

| Risk ID | Description | Impact | Affected Records | Mitigation |
|---------|-------------|--------|------------------|------------|
| **DQ-001** | `editor` field is 100% empty | Medium - Lost provenance | All 50 (100%) | Drop field, log warning |
| **DQ-002** | `first_name` is 34% empty | **CRITICAL** - Entity names in wrong field | 17 (34%) | Implement name parsing logic |
| **DQ-003** | `last_name` contains organization names | **CRITICAL** - Misclassification | ~17 (34%) | Add entity_type detection |
| **DQ-004** | `sub-category` has 34% NULL values | **CRITICAL** - PEP classification missing | 17 (34%) | Manual review required |
| **DQ-005** | No validation of date formats | Medium - Parse errors possible | Unknown | Add ISO date validation |
| **DQ-006** | `uid` may have gaps | Low - Audit trail issues | All | Verify uniqueness |
| **DQ-007** | `e-i` values E/M/F not validated | Medium - Gender misclassification | Unknown | Add allowed value check |

---

## 5. Fields Requiring MANUAL REVIEW (Do Not Auto-Map)

### 5.1 CANNOT AUTO-MAP (Semantic Mismatch)

| Target Field | Why Manual | Recommendation |
|--------------|------------|-----------------|
| `PassportNumber` | Not in source | Leave empty, add to optional enrichment |
| `NationalId` | Not in source | Leave empty |
| `Identifiers` | Not in source | Leave empty |
| `DateOfBirth` | Not in source | Leave empty |
| `YearOfBirth` | Not in source | Leave empty |
| `Address1-4` | Not in source | Leave empty |
| `City` | Not in source | Leave empty |
| `CountryOfBirthCode` | Not in source | Leave empty |
| `NationalityCountryCodes` | Not in source | Leave empty |
| `ProfileHyperlink` | Not in source | Could derive from WorldCheck URL pattern |
| `CustomString1-40` | Not in source | Map category to CustomString1 for reference |

### 5.2 REQUIRE BUSINESS RULES

| Target Field | Decision Needed | Owner |
|--------------|----------------|-------|
| `ListRecordType` | Map WorldCheck categories to SAN/PEP/SIP/SOE | Compliance Officer |
| `RiskScore` | Define risk scoring matrix | Risk Management |
| `RiskScorePEP` | Define PEP-specific scoring | AML Officer |
| `InactiveFlag` | When to mark a record inactive? | Data Governance |
| `DataConfidenceScore` | Define confidence criteria | Data Quality Team |

---

## 6. Fields That Should Be Mandatory Before Export

### 6.1 ABSOLUTE REQUIREMENTS (Block Export If Missing)

```
✓ ListRecordId          - Unique identifier
✓ ListRecordType        - SAN/PEP/SIP classification
✓ FullName              - Searchable name
✓ FamilyName            - At minimum surname
✓ AddedDate             - Audit trail
✓ LastUpdatedDate       - Audit trail
```

### 6.2 STRONGLY RECOMMENDED (Warn If Missing)

```
⚠ GivenNames            - Person's first name
⚠ PrimaryName           - Search index
⚠ RiskScore             - For prioritization
⚠ PEPclassification     - If ListRecordType=PEP
```

### 6.3 NICE-TO-HAVE (Optional)

```
○ Gender                - For filtering
○ NameType              - Person vs Entity
○ ListRecordOrigin      - Source system tracking
```

---

## 7. Safe Default Values

| Target Field | Default Value | When to Apply |
|--------------|---------------|---------------|
| `ListSubKey` | `"Private"` | Always |
| `ListRecordOrigin` | `"WORLDCHECK"` | Always |
| `NameType` | `"Primary Name"` | When cannot determine entity |
| `Gender` | `"U"` | When e-i is not M/F |
| `RiskScore` | `50` | Medium risk when category unknown |
| `DataConfidenceScore` | `60` | When first_name is NULL |
| `Title` | `NULL` | No default - leave empty |
| `PrimaryName` | Same as FullName | Always |
| `InactiveFlag` | `false` | Always |
| `DeceasedFlag` | `false` | Always |

---

## 8. Missing Features in Migration Engine

### 8.1 CRITICAL GAPS (Must Implement)

| Feature | Why Needed | Priority |
|---------|------------|----------|
| **Conditional Name Parsing** | Entity names stored in last_name field | P0 |
| **Category-to-Risk Matrix Engine** | Auto-calculate risk scores from categories | P0 |
| **Multi-field Derivation** | Combine first_name + last_name → FullName | P0 |
| **Business Rule Engine** | Map source categories to target ListRecordType | P0 |
| **Data Confidence Calculator** | Score based on field completeness | P1 |
| **Audit Trail for Transformations** | Track every field transformation | P1 |

### 8.2 VALIDATION GAPS

| Feature | Why Needed | Priority |
|---------|------------|----------|
| **Cross-field Validation** | LastUpdatedDate >= AddedDate | P0 |
| **Allowed Value Validation** | Gender only M/F/U/E | P0 |
| **Mandatory Field Enforcement** | Block export if required fields empty | P0 |
| **ISO Date Format Validation** | Ensure all dates are parseable | P1 |
| **Uniqueness Check** | ListRecordId must be unique | P1 |

### 8.3 MAPPING GAPS

| Feature | Why Needed | Priority |
|---------|------------|----------|
| **Fuzzy Name Matching** | Detect duplicates before import | P1 |
| **Entity Type Detection** | Auto-detect person vs organization | P1 |
| **Custom Field Mapping UI** | Allow business users to map CustomString fields | P2 |
| **Transformation Preview** | Show before/after of complex transforms | P2 |
| **Manual Review Queue** | Flag low-confidence records for human review | P1 |

### 8.4 AML/KYC SPECIFIC GAPS

| Feature | Why Needed | Priority |
|---------|------------|----------|
| **Sanctions List Integration** | Cross-reference with OFAC/UN/EU lists | P0 |
| **PEP Hierarchy Detection** | Identify PEP type (Level 1-4) | P1 |
| **Risk-Based Scoring Model** | Configurable risk matrices | P0 |
| **Adverse Media Flagging** | Detect negative news associations | P2 |
| **Ongoing Monitoring Flag** | Mark records requiring continuous monitoring | P1 |

---

## 9. Recommended Migration Strategy

### Phase 1: Foundation (Week 1-2)
1. Implement name parsing logic for entity names in last_name
2. Create category-to-risk scoring matrix
3. Implement ListRecordType derivation rules
4. Add validation for mandatory fields
5. Create manual review queue for low-confidence records

### Phase 2: Validation & Quality (Week 3-4)
1. Implement cross-field validation (dates)
2. Add uniqueness check for ListRecordId
3. Create data confidence scoring
4. Build transformation audit trail
5. Generate pre-migration data quality report

### Phase 3: AML Enhancement (Week 5-6)
1. Integrate sanctions list validation
2. Implement PEP classification logic
3. Add risk-based filtering
4. Create ongoing monitoring flags
5. Build compliance reporting

### Phase 4: Testing & Sign-off (Week 7-8)
1. Full regression test with sample data
2. Compliance officer review
3. Risk management sign-off
4. Production deployment

---

## 10. Immediate Action Items

| Priority | Action | Owner | Deadline |
|----------|--------|-------|----------|
| P0 | Get business sign-off on risk scoring matrix | Risk Management | Day 3 |
| P0 | Define WorldCheck → SAN/PEP/SIP mapping rules | Compliance | Day 3 |
| P0 | Implement name parsing for entity detection | Tech Lead | Day 5 |
| P0 | Add mandatory field validation | Tech Lead | Day 5 |
| P1 | Create data quality report for source file | Data Analyst | Day 2 |
| P1 | Design manual review workflow | Product | Day 7 |
| P2 | Build custom field mapping UI | Frontend | Day 14 |

---

## Appendix A: Sample Row Transformation

### Source (WorldCheck)
```
category: POLITICAL INDIVIDUAL
editor: NULL
entered: 2000-10-16
sub-category: PEP
uid: 7
updated: 2023-03-09
entity_type: person
e-i: M
first_name: Mahmud Dhiyab
last_name: AL-AHMAD
```

### Target (Private Individuals)
```
ListSubKey: Private
ListRecordType: PEP
ListRecordOrigin: WORLDCHECK
ListRecordId: 7
FullName: Mahmud Dhiyab AL-AHMAD
GivenNames: Mahmud Dhiyab
FamilyName: AL-AHMAD
NameType: Primary Name
Gender: M
RiskScore: 70
PEPclassification: PEP
AddedDate: 2000-10-16
LastUpdatedDate: 2023-03-09
DataConfidenceScore: 85
CustomString1: POLITICAL INDIVIDUAL
```

### Transformation Log
```
[2026-06-03] uid → ListRecordId (direct copy)
[2026-06-03] first_name + last_name → FullName (concatenation)
[2026-06-03] sub-category="PEP" → ListRecordType="PEP" (business rule)
[2026-06-03] category="POLITICAL INDIVIDUAL" → RiskScore=70 (matrix lookup)
[2026-06-03] e-i="M" → Gender="M" (direct copy)
[2026-06-03] entered → AddedDate (date format validated)
[2026-06-03] updated → LastUpdatedDate (date format validated)
[2026-06-03] first_name IS NOT NULL → DataConfidenceScore=85 (completeness)
[2026-06-03] category → CustomString1 (for reference)
```

---

**Document Status**: DRAFT - Pending Business Review
**Next Review**: After risk scoring matrix approval
