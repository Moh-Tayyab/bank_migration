# 01. Mapping Table - WorldCheck → Private Individuals

## HIGH CONFIDENCE AUTO-MAPPINGS (90-100%)

| Source Field | Target Field | Transformation | Confidence | Mandatory | AML Impact |
|--------------|--------------|----------------|------------|-----------|------------|
| `uid` | `ListRecordId` | Direct copy | 100% | ✅ YES | Critical for audit |
| `updated` | `LastUpdatedDate` | ISO date validation | 95% | ✅ YES | Audit trail |
| `entered` | `AddedDate` | ISO date validation | 95% | ✅ YES | Audit trail |

## MEDIUM CONFIDENCE MAPPINGS (60-89%)

| Source Field | Target Field | Transformation | Confidence | Mandatory | Risk |
|--------------|--------------|----------------|------------|-----------|------|
| `first_name` | `GivenNames` | Trim + uppercase | 85% | ⚠️ Conditional | 34% NULL in source |
| `last_name` | `FamilyName` | Trim + uppercase | 85% | ✅ YES | May contain entity name |
| `first_name + last_name` | `FullName` | Concatenate with space | 80% | ✅ YES | Key for search |
| `first_name + last_name` | `PrimaryName` | Copy from FullName | 80% | ✅ YES | Primary search field |
| `sub-category` | `PEPclassification` | Direct copy (when "PEP") | 75% | ✅ YES | Only 66% populated |
| `e-i` | `Gender` | M→M, F→F, E→U | 70% | ○ Optional | E=Entity case |
| `category` | `CustomString1` | Direct copy | 70% | ○ Optional | Reference only |

## DERIVED FIELDS (Computed Values)

| Target Field | Derivation Logic | Source Fields | Risk |
|--------------|-----------------|---------------|------|
| `ListSubKey` | Constant: "Private" | N/A | None |
| `ListRecordType` | IF sub-category="PEP" THEN "PEP" ELSE "SAN" | category, sub-category | Medium |
| `ListRecordOrigin` | Constant: "WORLDCHECK" | N/A | None |
| `RiskScore` | CRIME→90, POLITICAL→85, INDIVIDUAL→50 | category | **High** |
| `NameType` | Constant: "Primary Name" | N/A | Low |
| `DataConfidenceScore` | IF first_name NULL THEN 60 ELSE 85 | first_name | Medium |

## FIELDS TO NEVER AUTO-MAP

| Target Field | Reason | Action |
|--------------|--------|--------|
| `editor` | 100% NULL in source | **DROP** |
| `PassportNumber` | Not in source | Leave empty |
| `NationalId` | Not in source | Leave empty |
| `DateOfBirth` | Not in source | Leave empty |
| `YearOfBirth` | Not in source | Leave empty |
| `Address1-4` | Not in source | Leave empty |
| `City` | Not in source | Leave empty |
| `CountryOfBirthCode` | Not in source | Leave empty |
| `NationalityCountryCodes` | Not in source | Leave empty |
| `ProfileHyperlink` | Not in source | Leave empty |

## FIELDS REQUIRING MANUAL REVIEW

| Target Field | Why Manual Review | Recommended Value |
|--------------|-------------------|-------------------|
| `ListRecordType` | WorldCheck categories don't map 1:1 | Business rule matrix |
| `RiskScore` | Category is text, risk is numeric | Risk scoring matrix |
| `RiskScorePEP` | Complex derivation | PEP-specific formula |
| `InactiveFlag` | Business decision needed | Default: false |
| `DataConfidenceScore` | Subjective scoring | Formula based on completeness |
