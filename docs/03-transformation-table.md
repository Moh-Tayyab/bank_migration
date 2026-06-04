# 03. Transformation Table - Exact Rules

## T1: Name Parsing (COMPLEX - CRITICAL)

### Problem Statement
WorldCheck stores data inconsistently:
- When `first_name` is NULL, `last_name` contains the FULL ENTITY NAME
- Example: `first_name=NULL`, `last_name="REVOLUTIONARY ORGANIZATION 17 NOVEMBER"`

### Transformation Logic

```python
def transform_name(first_name, last_name):
    """
    Transform WorldCheck name fields to target schema.
    CRITICAL: Handle entity names stored in last_name field.
    """
    if pd.isna(first_name) or str(first_name).strip() == "":
        # Entity name stored in last_name
        return {
            "FullName": str(last_name).strip(),
            "GivenNames": None,
            "FamilyName": str(last_name).strip(),
            "NameType": "Entity Name",
            "PrimaryName": str(last_name).strip(),
            "Title": None
        }
    else:
        # Person name split across fields
        full_name = f"{str(first_name).strip()} {str(last_name).strip()}"
        return {
            "FullName": full_name,
            "GivenNames": str(first_name).strip(),
            "FamilyName": str(last_name).strip(),
            "NameType": "Primary Name",
            "PrimaryName": full_name,
            "Title": None
        }
```

### Test Cases

| first_name | last_name | FullName | GivenNames | FamilyName | NameType |
|------------|-----------|----------|-----------|------------|----------|
| NULL | REVOLUTIONARY ORGANIZATION 17 NOVEMBER | REVOLUTIONARY ORGANIZATION 17 NOVEMBER | NULL | REVOLUTIONARY ORGANIZATION 17 NOVEMBER | Entity Name |
| Sadi Tuma Abbas | AL-JABBURI | Sadi Tuma Abbas AL-JABBURI | Sadi Tuma Abbas | AL-JABBURI | Primary Name |
| Bashar | AL-ASSAD | Bashar AL-ASSAD | Bashar | AL-ASSAD | Primary Name |

---

## T2: Risk Score Calculation

### Business Logic Matrix

| Source Category | Target RiskScore | Rationale |
|-----------------|------------------|------------|
| CRIME - TERROR | 100 | Highest risk - terrorism |
| NONCONVICTION TERROR | 95 | Very high risk - terror association |
| CRIME - WAR | 90 | High risk - war crimes |
| CRIME - FINANCIAL | 85 | High risk - financial crime |
| POLITICAL INDIVIDUAL | 70 | Medium-high risk - PEP |
| INDIVIDUAL | 50 | Medium risk - general |

### Transformation Logic

```python
def calculate_risk_score(category, sub_category):
    """
    Calculate risk score based on WorldCheck category.
    Returns: Integer 0-100
    """
    base_scores = {
        "CRIME - TERROR": 100,
        "NONCONVICTION TERROR": 95,
        "CRIME - WAR": 90,
        "CRIME - FINANCIAL": 85,
        "POLITICAL INDIVIDUAL": 70,
        "INDIVIDUAL": 50
    }

    base_score = base_scores.get(category, 50)

    # Boost score if PEP
    if sub_category == "PEP" and category == "POLITICAL INDIVIDUAL":
        base_score = min(100, base_score + 10)

    return base_score
```

---

## T3: Gender Transformation

### Mapping Table

| Source (e-i) | Target (Gender) | Meaning |
|--------------|-----------------|---------|
| M | M | Male |
| F | F | Female |
| E | U | Entity/Unknown |
| NULL/other | U | Unknown |

### Transformation Logic

```python
def transform_gender(ei_value):
    """
    Transform WorldCheck e-i field to target Gender.
    E = Entity, M = Male, F = Female
    """
    if pd.isna(ei_value):
        return "U"

    ei_upper = str(ei_value).upper().strip()

    if ei_upper == "M":
        return "M"
    elif ei_upper == "F":
        return "F"
    elif ei_upper == "E":
        return "U"  # Entity mapped to Unknown
    else:
        return "U"  # Default to Unknown
```

---

## T4: ListRecordType Derivation

### Business Rules

| Condition | Target ListRecordType |
|-----------|----------------------|
| sub_category = "PEP" | PEP |
| category contains "CRIME" OR "TERROR" | SAN (Sanctions) |
| category = "POLITICAL INDIVIDUAL" AND sub_category != "PEP" | SIP (Special Interest Person) |
| category = "INDIVIDUAL" | SIP |
| Default | SIP |

### Transformation Logic

```python
def derive_record_type(category, sub_category):
    """
    Derive ListRecordType for screening system.
    Returns: SAN, PEP, SIP, or SOE
    """
    if sub_category == "PEP":
        return "PEP"

    category_upper = str(category).upper() if not pd.isna(category) else ""

    if "CRIME" in category_upper or "TERROR" in category_upper:
        return "SAN"

    if "POLITICAL" in category_upper or "INDIVIDUAL" in category_upper:
        return "SIP"

    return "SIP"  # Default
```

---

## T5: Date Format Validation

### Transformation Rules

| Source Format | Target Format | Example |
|---------------|----------------|---------|
| YYYY-MM-DD | YYYY-MM-DD | 2000-11-10 → 2000-11-10 |
| DD/MM/YYYY | YYYY-MM-DD | 10/11/2000 → 2000-11-10 |
| MM-DD-YYYY | YYYY-MM-DD | 11-10-2000 → 2000-11-10 |

### Validation Logic

```python
def validate_and_format_date(date_value, field_name):
    """
    Validate and format date to ISO 8601 (YYYY-MM-DD).
    Raises ValueError if invalid.
    """
    if pd.isna(date_value):
        raise ValueError(f"{field_name} is required")

    date_str = str(date_value).strip()

    # Try parsing various formats
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d"]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # Validate not in future
            if parsed.date() > datetime.now().date():
                raise ValueError(f"{field_name} cannot be in future")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"{field_name} has invalid format: {date_str}")
```

---

## T6: Data Confidence Scoring

### Completeness-Based Scoring

| Completeness | Score | Rationale |
|--------------|-------|-----------|
| All name fields present | 85 | High confidence |
| first_name NULL | 60 | Medium-low confidence |
| Both names NULL | 30 | Low confidence |
| sub_category NULL | -5 penalty | Missing classification |

### Transformation Logic

```python
def calculate_confidence_score(record):
    """
    Calculate data confidence score based on field completeness.
    Returns: Integer 0-100
    """
    score = 50  # Base score

    # Name completeness
    if not pd.isna(record.get('first_name')) and str(record['first_name']).strip():
        score += 35
    else:
        score -= 20

    # Classification present
    if not pd.isna(record.get('sub_category')) and str(record['sub_category']).strip():
        score += 10
    else:
        score -= 5

    # Dates present and valid
    try:
        validate_and_format_date(record.get('entered'), 'entered')
        score += 5
    except:
        score -= 5

    return max(0, min(100, score))
```

---

## T7: PEP Classification Enrichment

### Source → Target Mapping

| Source sub_category | Target PEPclassification |
|--------------------|-------------------------|
| "PEP" | "PEP" |
| NULL (if category = POLITICAL INDIVIDUAL) | "PEP - Review Required" |
| NULL (other) | NULL |

### Transformation Logic

```python
def derive_pep_classification(sub_category, category):
    """
    Derive PEP classification from source fields.
    """
    if not pd.isna(sub_category) and str(sub_category).strip() == "PEP":
        return "PEP"

    if not pd.isna(category) and "POLITICAL" in str(category).upper():
        return "PEP - Review Required"

    return None
```

---

## TRANSFORMATION EXECUTION ORDER

```
1. Validate Dates (T5)
2. Parse Names (T1)
3. Derive Record Type (T4)
4. Calculate Risk Score (T2)
5. Transform Gender (T3)
6. Derive PEP Classification (T7)
7. Calculate Confidence Score (T6)
8. Set Default Values
```

## TRANSFORMATION AUDIT TRAIL

Each transformation should log:

```json
{
  "timestamp": "2026-06-03T10:30:00Z",
  "source_record_id": 7,
  "transformation": "T1-NameParsing",
  "input": {"first_name": "Bashar", "last_name": "AL-ASSAD"},
  "output": {"FullName": "Bashar AL-ASSAD", "GivenNames": "Bashar", "FamilyName": "AL-ASSAD"},
  "confidence": 0.85,
  "requires_review": false
}
```
