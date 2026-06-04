# WorldCheck → Private Individuals Migration Analysis
## Complete Schema Mapping & Transformation Guide

**Date**: 2026-06-03
**Source**: WorldCheck (50 records, 10 columns)
**Target**: Private Individuals (93 columns)

---

## 📋 Table of Contents

1. [Mapping Table](./01-mapping-table.md) - Exact field mappings with confidence scores
2. [Validation Table](./02-validation-table.md) - Per-field validation rules
3. [Transformation Table](./03-transformation-table.md) - Exact transformation logic
4. [Risk Table](./04-risk-table.md) - Data quality risks and mitigation
5. [Product Improvement Roadmap](./05-product-improvement-roadmap.md) - Engine gaps and implementation plan

---

## 🚨 Executive Summary

This is **NOT a standard customer data migration**. This is a **high-risk AML/KYC screening data migration** from WorldCheck (Refinitiv sanctions/watchlist database) to an internal bank screening system.

### Critical Findings

| Dimension | Assessment |
|-----------|-------------|
| **Schema Complexity** | **HIGH** - Target has 93 fields vs Source 10 fields (83% data gap) |
| **Mapping Complexity** | **CRITICAL** - Multiple semantic transformations required |
| **Data Quality Risk** | **SEVERE** - 34% missing first names, 100% missing editor field |
| **AML Compliance Risk** | **CRITICAL** - Missing validation for sanctions, PEP, and risk scoring |
| **Auto-mappability** | **LOW** - Only 20% of fields can be safely auto-mapped |

---

## 🎯 Key Recommendations

### Immediate Actions (Before Migration)

1. **DO NOT** auto-migrate without implementing:
   - Conditional name parsing (for entity names in last_name field)
   - Risk scoring matrix (category → score derivation)
   - ListRecordType derivation (category → SAN/PEP/SIP)
   - Mandatory field validation
   - Manual review queue for low-confidence records

2. **Get business sign-off on**:
   - Risk scoring matrix (see Transformation Table T2)
   - Category → SAN/PEP/SIP mapping rules (see Transformation Table T4)
   - Default values for Custom fields

3. **Implement manual review workflow** for:
   - Records with NULL first_name (34% of data)
   - Records with NULL sub_category (34% of data)
   - Records with default risk scores

---

## 📊 Quick Reference

### Safe Auto-Mappings (90-100% Confidence)

| Source | Target | Notes |
|--------|--------|-------|
| `uid` | `ListRecordId` | Direct copy |
| `updated` | `LastUpdatedDate` | Validate ISO format |
| `entered` | `AddedDate` | Validate ISO format |

### High-Value Derivations

| Target | Derivation | Source |
|--------|------------|--------|
| `FullName` | first_name + last_name | Concatenation |
| `ListRecordType` | IF PEP THEN "PEP" ELSE "SAN" | sub-category |
| `RiskScore` | CRIME→90, POLITICAL→85, INDIVIDUAL→50 | category |
| `DataConfidenceScore` | IF first_name NULL THEN 60 ELSE 85 | Completeness |

### Fields to Never Auto-Map

| Target | Reason |
|--------|--------|
| `editor` | 100% NULL in source |
| `PassportNumber` | Not in source |
| `NationalId` | Not in source |
| `DateOfBirth` | Not in source |
| `Address1-4` | Not in source |

---

## 🔄 Transformation Execution Order

```
1. Validate Dates (T5)
2. Parse Names (T1) ← CRITICAL for entity detection
3. Derive Record Type (T4)
4. Calculate Risk Score (T2)
5. Transform Gender (T3)
6. Derive PEP Classification (T7)
7. Calculate Confidence Score (T6)
8. Set Default Values
9. Validate Mandatory Fields
10. Queue for Manual Review (if needed)
```

---

## ⚠️ Risk Summary

### Critical Data Quality Issues

| Issue | Impact | Records Affected |
|-------|--------|------------------|
| 34% NULL `first_name` | Entity names in wrong field | 17 of 50 |
| 34% NULL `sub-category` | Missing PEP classification | 17 of 50 |
| 100% NULL `editor` | Lost provenance | 50 of 50 |

### AML Compliance Risks

| Risk | Mitigation |
|------|------------|
| Missing PEP classification | Manual review of 17 records |
| No risk score derivation | Implement risk matrix |
| Entity vs Person not detected | Add entity detection logic |
| No sanctions list validation | Integrate OFAC/UN lists |

---

## 🛠️ Product Gaps (Must Implement)

### Phase 1 (P0) - 10 days

| Gap | Description | Why |
|-----|-------------|-----|
| G1 | Conditional Name Parser | Handle entity names in last_name |
| G2 | Risk Scoring Engine | Derive scores from categories |
| G3 | Business Rule Engine | Derive ListRecordType |
| G4 | Mandatory Field Validator | Block invalid exports |
| G5 | Manual Review Queue | Handle low-confidence records |

### Phase 2 (P1) - 13 days

| Gap | Description | Why |
|-----|-------------|-----|
| G6 | Transformation Audit Trail | Compliance requirement |
| G7 | Data Confidence Calculator | Quantify quality |
| G8 | Cross-Field Validator | Catch inconsistencies |
| G9 | Entity Type Detector | Distinguish person vs org |
| G10 | Sanctions List Integration | OFAC/UN validation |

---

## 📁 Document Index

| Document | Purpose | Key Sections |
|----------|---------|--------------|
| [01-mapping-table.md](./01-mapping-table.md) | Exact field mappings with confidence scores | Auto-mappings, Derived fields, Never-map list |
| [02-validation-table.md](./02-validation-table.md) | Per-field validation rules | Identity fields, Classification fields, Date validations |
| [03-transformation-table.md](./03-transformation-table.md) | Exact transformation logic | Name parsing, Risk scoring, Gender transformation |
| [04-risk-table.md](./04-risk-table.md) | Data quality risks | Source risks, AML risks, Mitigation strategies |
| [05-product-improvement-roadmap.md](./05-product-improvement-roadmap.md) | Engine gaps and implementation plan | 20 gaps, Timeline, Resource requirements |

---

## 🎯 Success Criteria

A successful migration must achieve:

- [ ] Zero data loss (50 records in = 50 records out)
- [ ] All mandatory fields populated
- [ ] Manual review queue processed
- [ ] Risk scores calculated for all records
- [ ] PEP classifications complete
- [ ] Audit trail intact
- [ ] Zero validation errors on export
- [ ] Compliance sign-off obtained

---

## 📞 Next Steps

1. **Review this analysis** with Compliance and Risk Management teams
2. **Approve risk scoring matrix** (see 03-transformation-table.md, T2)
3. **Approve category → SAN/PEP/SIP mapping** (see 03-transformation-table.md, T4)
4. **Implement Phase 1 gaps** (10 days estimated)
5. **Run test migration** with sample data
6. **Execute production migration** with manual review

---

**Document Status**: ✅ COMPLETE - Ready for Business Review
**Last Updated**: 2026-06-03
**Version**: 1.0
