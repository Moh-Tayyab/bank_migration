# 04. Risk Table - Data Quality Assessment

## DATA QUALITY RISKS IN SOURCE FILE

### CRITICAL RISKS (Block Migration Without Resolution)

| Risk ID | Description | Impact | Affected Records | Probability | Severity |
|---------|-------------|--------|------------------|-------------|----------|
| **DQ-001** | `first_name` is 34% NULL | **CRITICAL** - Entity names in wrong field | 17 of 50 (34%) | High | **P0** |
| **DQ-002** | `sub-category` has 34% NULL values | **CRITICAL** - PEP classification missing | 17 of 50 (34%) | High | **P0** |
| **DQ-003** | `editor` field is 100% empty | Medium - Lost provenance tracking | 50 of 50 (100%) | Certain | **P2** |
| **DQ-004** | No date format validation | Medium - Parse errors possible | Unknown | Medium | **P1** |

### HIGH RISKS (Flag for Manual Review)

| Risk ID | Description | Impact | Affected Records | Probability | Severity |
|---------|-------------|--------|------------------|-------------|----------|
| **DQ-005** | `last_name` contains organization names | **HIGH** - Misclassification risk | ~17 records | Medium | **P1** |
| **DQ-006** | `e-i` values E/M/F not validated | Medium - Gender misclassification | Unknown | Low | **P2** |
| **DQ-007** | `uid` may have gaps | Low - Audit trail issues | All 50 | Low | **P3** |

## AML/KYC COMPLIANCE RISKS

| Risk ID | Description | Regulatory Impact | Mitigation | Priority |
|---------|-------------|-------------------|------------|----------|
| **AML-001** | Missing PEP classification | Potential OFAC/FINRA violation | Manual review of 17 records | **P0** |
| **AML-002** | No risk score derivation | Ineffective screening | Implement risk matrix | **P0** |
| **AML-003** | Entity vs Person not detected | False negatives in screening | Add entity detection | **P1** |
| **AML-004** | No sanctions list validation | Compliance gap | Integrate OFAC/UN lists | **P0** |
| **AML-005** | Missing ongoing monitoring flags | Regulatory requirement | Add monitoring flags | **P1** |

## TRANSFORMATION RISKS

| Risk ID | Description | Impact | Mitigation |
|---------|-------------|--------|------------|
| **TX-001** | Name concatenation may create duplicates | Search efficiency | Add deduplication logic |
| **TX-002** | Risk score matrix may be misaligned | Over/under-screening | Business sign-off required |
| **TX-003** | ListRecordType derivation may misclassify | Compliance exposure | Manual review queue |
| **TX-004** | Date format assumptions may fail | Migration blocking | Test all date formats |
| **TX-005** | Default values may hide issues | Data quality decay | Flag all defaults used |

## SOURCE FIELD RISK ASSESSMENT

| Source Field | Data Quality | Risk Level | Action Required |
|--------------|--------------|------------|-----------------|
| `category` | ✅ Good - No NULL | Low | None |
| `editor` | ❌ 100% NULL | Medium | Drop field |
| `entered` | ✅ Good - All populated | Low | Validate format |
| `sub-category` | ⚠️ 34% NULL | **High** | Business rule for NULL |
| `uid` | ✅ Good - All populated | Low | Verify uniqueness |
| `updated` | ✅ Good - All populated | Low | Validate format |
| `entity_type` | ✅ Good - All "person" | Low | Handle future entities |
| `e-i` | ✅ Good - No NULL | Low | Validate values |
| `first_name` | ❌ 34% NULL | **Critical** | Entity name logic |
| `last_name` | ✅ Good - No NULL | Medium | May contain entities |

## TARGET FIELD COMPLETENESS RISK

| Target Field | Can Populate | Default Strategy | Risk |
|--------------|--------------|-------------------|------|
| `ListRecordId` | ✅ Yes | N/A | None |
| `ListRecordType` | ⚠️ Derive | Default to SIP | Medium |
| `FullName` | ✅ Yes | N/A | None |
| `GivenNames` | ⚠️ 66% | NULL for entities | Medium |
| `FamilyName` | ✅ Yes | N/A | None |
| `Gender` | ✅ Yes | Default to U | Low |
| `DateOfBirth` | ❌ No | Leave NULL | N/A |
| `PassportNumber` | ❌ No | Leave NULL | N/A |
| `Address1-4` | ❌ No | Leave NULL | N/A |
| `RiskScore` | ⚠️ Derive | Matrix lookup | Medium |
| `PEPclassification` | ⚠️ 66% | NULL for 34% | Medium |

## RISK MITIGATION MATRIX

```
┌────────────────────────────────────────────────────────────────────┐
│                    RISK × MITIGATION STRATEGY                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  CRITICAL (P0)  →  Implement before ANY migration                   │
│  HIGH (P1)      →  Implement in Phase 1, flag for manual review      │
│  MEDIUM (P2)    →  Implement in Phase 2, use defaults                │
│  LOW (P3)       →  Log only, fix in future release                   │
│                                                                        │
└────────────────────────────────────────────────────────────────────┘
```

## PRE-MIGRATION RISK CHECKLIST

### Source Validation
- [ ] Verify all 50 source records are valid
- [ ] Confirm `uid` uniqueness
- [ ] Validate all date formats
- [ ] Flag records with NULL `first_name`
- [ ] Flag records with NULL `sub_category`
- [ ] Confirm `category` values are in expected set

### Transformation Readiness
- [ ] Name parsing logic implemented and tested
- [ ] Risk scoring matrix defined and approved
- [ ] ListRecordType derivation rules signed off
- [ ] Date validation working for all formats
- [ ] Default values documented
- [ ] Transformation audit trail ready

### Target Readiness
- [ ] Mandatory fields identified
- [ ] Validation rules implemented
- [ ] Manual review queue configured
- [ ] Export template created
- [ ] Rollback procedure defined

## RISK ACCEPTANCE CRITERIA

### Can Proceed With:
- ⚠️ 34% NULL `first_name` IF entity detection works
- ⚠️ 34% NULL `sub_category` IF manual review in place
- ⚠️ 100% NULL `editor` IF field is dropped
- ⚠️ Missing biographic data IF acceptable for screening

### Cannot Proceed Without:
- ❌ Name parsing logic for entities
- ❌ Risk scoring matrix approval
- ❌ ListRecordType derivation rules
- ❌ Mandatory field validation
- ❌ Date format validation

## POST-MIGRATION RISK MONITORING

| Metric | Target | Alert Threshold | Owner |
|--------|--------|-----------------|-------|
| Records with NULL GivenNames | < 5% | > 10% | Data Quality |
| Records with default RiskScore | < 10% | > 20% | Risk Management |
| Records with NULL PEPclassification | 0% | > 0% | Compliance |
| Records in manual review queue | 0 | > 5 | Data Migration |
| Record count mismatch | 0 | > 0 | Migration Lead |
