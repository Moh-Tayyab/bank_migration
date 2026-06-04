# 02. Validation Table - Per Critical Field

## IDENTITY FIELDS (CRITICAL FOR AML)

| Field | Validation Rule | Error Level | Test Case | Fix Action |
|-------|-----------------|-------------|-----------|------------|
| `ListRecordId` | Must be unique | **BLOCKER** | Duplicate ID error | Generate new ID |
| `ListRecordId` | Must be integer > 0 | **BLOCKER** | Negative/zero ID | Reject record |
| `ListRecordId` | Required field | **BLOCKER** | NULL/empty | Reject record |
| `FullName` | Must NOT be empty/whitespace | **BLOCKER** | Empty string | Use last_name fallback |
| `FullName` | Max length 255 chars | **HIGH** | Truncate warning | Truncate + flag |
| `GivenNames` | Required IF entity_type = "person" | **HIGH** | NULL for person | Flag for review |
| `FamilyName` | Must NOT be empty | **BLOCKER** | NULL/empty | Use FullName |
| `PrimaryName` | Must equal FullName | **HIGH** | Mismatch | Auto-sync |

## CLASSIFICATION FIELDS (CRITICAL FOR SANCTIONS)

| Field | Validation Rule | Error Level | Allowed Values | Fix Action |
|-------|-----------------|-------------|----------------|------------|
| `ListRecordType` | Required field | **BLOCKER** | SAN, PEP, SIP, SOE | Default to SAN |
| `ListRecordType` | Must be in allowed values | **BLOCKER** | SAN, PEP, SIP, SOE | Flag invalid |
| `PEPclassification` | Required IF ListRecordType = "PEP" | **BLOCKER** | Text string | Default to "PEP" |
| `RiskScore` | Must be 0-100 | **HIGH** | Numeric 0-100 | Default to 50 |
| `RiskScore` | Required for prioritization | **HIGH** | Not NULL | Default to 50 |
| `Gender` | Must be in allowed values | **MEDIUM** | M, F, U, E | Default to U |
| `NameType` | Must be in allowed values | **MEDIUM** | Primary Name, Alias, Entity | Default |

## DATE FIELDS (CRITICAL FOR AUDIT)

| Field | Validation Rule | Error Level | Format | Fix Action |
|-------|-----------------|-------------|--------|------------|
| `AddedDate` | Required field | **BLOCKER** | ISO 8601 | Reject record |
| `AddedDate` | Must be valid date | **BLOCKER** | YYYY-MM-DD | Reject record |
| `AddedDate` | Must be <= today | **BLOCKER** | Future date | Reject record |
| `LastUpdatedDate` | Required field | **BLOCKER** | ISO 8601 | Reject record |
| `LastUpdatedDate` | Must be valid date | **BLOCKER** | YYYY-MM-DD | Reject record |
| `LastUpdatedDate` | Must be <= today | **BLOCKER** | Future date | Reject record |
| `LastUpdatedDate` | Must be >= AddedDate | **BLOCKER** | Updated < Added | Use AddedDate |

## CUSTOM FIELDS (OPTIONAL)

| Field | Validation Rule | Error Level | Format | Fix Action |
|-------|-----------------|-------------|--------|------------|
| `CustomString1-40` | Max length 255 | **LOW** | String | Truncate |
| `CustomNumber1-5` | Must be numeric | **LOW** | Decimal | NULL on error |
| `CustomDate1-5` | Must be valid date | **LOW** | ISO 8601 | NULL on error |

## CROSS-FIELD VALIDATIONS

| Validation | Fields | Error Level | Logic | Fix Action |
|------------|--------|-------------|-------|------------|
| Name consistency | FullName = GivenNames + FamilyName | **HIGH** | Concatenation match | Auto-fix |
| Gender vs Entity | IF e-i=E THEN Gender=U | **MEDIUM** | Entity detection | Set to U |
| PEP completeness | IF ListRecordType=PEP THEN PEPclassification NOT NULL | **BLOCKER** | Conditional required | Default to "PEP" |
| Date logic | LastUpdatedDate >= AddedDate | **BLOCKER** | Date comparison | Use AddedDate |

## VALIDATION PRIORITY MATRIX

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION SEVERITY LEVELS                    │
├─────────────────────────────────────────────────────────────────┤
│ BLOCKER - Halt migration, reject record                         │
│ HIGH     - Flag for manual review before export                 │
│ MEDIUM   - Warning, auto-fix if possible                         │
│ LOW      - Log only, can proceed                                 │
└─────────────────────────────────────────────────────────────────┘
```

## PRE-MIGRATION VALIDATION CHECKLIST

- [ ] All source records have unique `uid`
- [ ] All dates are in valid format (YYYY-MM-DD)
- [ ] No NULL values in `last_name`
- [ ] `sub-category` values are valid when present
- [ ] `category` values are in expected set
- [ ] `e-i` values are only E, M, or F
- [ ] `entity_type` is always "person" (or handle entities)

## POST-MIGRATION VALIDATION CHECKLIST

- [ ] All exported records have `ListRecordId`
- [ ] All exported records have `FullName`
- [ ] All exported records have `ListRecordType`
- [ ] All date fields are ISO 8601 format
- [ ] No `RiskScore` values outside 0-100
- [ ] `LastUpdatedDate` >= `AddedDate` for all records
- [ ] Total record count matches source (50)
- [ ] Manual review queue is empty or reviewed
