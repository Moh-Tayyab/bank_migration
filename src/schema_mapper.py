import re
from typing import Any, Dict, List, Optional

from .models import MappingRule, Record
from .registry import BankRegistry

# Canonical field name aliases for fuzzy matching
_FIELD_ALIASES: Dict[str, List[str]] = {
    "first_name": ["first_name", "given_name", "givennames", "firstname", "fname", "first"],
    "last_name": ["last_name", "family_name", "familyname", "lastname", "lname", "last", "surname"],
    "full_name": ["full_name", "fullname", "name", "display_name"],
    "date_of_birth": ["date_of_birth", "dob", "birthdate", "birth_date", "dateofbirth"],
    "gender": ["gender", "sex", "e-i", "ei"],
    "email": ["email", "email_address", "emailaddress", "mail"],
    "phone": ["phone", "phone_number", "phonenumber", "contact_number", "contactnumber", "mobile", "tel"],
    "address": ["address", "address1", "address_1", "street", "address_line_1"],
    "city": ["city", "town", "locality"],
    "state": ["state", "province", "region"],
    "postal_code": ["postal_code", "postalcode", "zip", "zipcode", "zip_code", "postcode"],
    "country": ["country", "country_code", "countrycode", "nationality"],
    "category": ["category", "risk_category", "riskcategory", "risk_score", "riskscore"],
    "sub_category": ["sub_category", "subcategory", "sub-category", "pepclassification", "pep_class"],
    "uid": ["uid", "id", "record_id", "recordid", "listrecordid"],
    "entered": ["entered", "added_date", "addeddate", "created", "create_date"],
    "updated": ["updated", "last_updated", "lastupdated", "modified", "modify_date"],
    "occupation": ["occupation", "job", "title", "role", "position"],
    "entity_type": ["entity_type", "entitytype", "type", "record_type", "recordtype"],
    "inactive_flag": ["inactive_flag", "inactiveflag", "inactive", "is_inactive"],
    "deceased_flag": ["deceased_flag", "deceasedflag", "deceased", "is_deceased"],
}

# Direct mappings for WorldCheck specific columns to private_individuals fields
_WC_DIRECT_MAPPINGS: Dict[str, str] = {
    "uid": "ListRecordId",
    "entered": "AddedDate",
    "updated": "LastUpdatedDate",
    "first_name": "GivenNames",
    "last_name": "FamilyName",
    "category": "RiskScore",
    "sub-category": "PEPclassification",
    "e-i": "Gender",
    "entity_type": "ListRecordType",
}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _match_field(source_col: str, target_fields: List[str]) -> Optional[str]:
    norm_src = _normalize(source_col)

    # Check direct WorldCheck mappings first
    if source_col in _WC_DIRECT_MAPPINGS:
        target = _WC_DIRECT_MAPPINGS[source_col]
        if target in target_fields:
            return target

    # Direct alias match
    for alias_key, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            if _normalize(alias) == norm_src:
                for tf in target_fields:
                    if _normalize(tf) == _normalize(alias_key):
                        return tf
                    if _normalize(tf) == norm_src:
                        return tf

    # Direct match
    for tf in target_fields:
        if _normalize(tf) == norm_src:
            return tf

    # Substring match
    for tf in target_fields:
        norm_tf = _normalize(tf)
        if len(norm_src) >= 4 and norm_src in norm_tf:
            return tf
        if len(norm_tf) >= 4 and norm_tf in norm_src:
            return tf

    return None


def auto_generate_mappings(
    source_columns: List[str], target_bank: str, registry: Optional[BankRegistry] = None
) -> List[MappingRule]:
    reg = registry or BankRegistry()
    schema = reg.get_schema(target_bank)
    if not schema:
        return []

    target_fields = list(schema.fields.keys())
    mappings: List[MappingRule] = []

    for col in source_columns:
        matched = _match_field(col, target_fields)
        if matched:
            mappings.append(
                MappingRule(
                    source_field=col,
                    target_field=matched,
                    transform="",
                    required=False,
                    default=None,
                )
            )

    return mappings


class SchemaMapper:
    def __init__(self, registry: Optional[BankRegistry] = None):
        self._registry = registry or BankRegistry()
        self._auto_cache: Dict[str, List[MappingRule]] = {}

    def map_record(
        self,
        record: Record,
        target_bank: str,
        version: str = "latest",
    ) -> Record:
        if record.source_bank == "__auto__":
            if target_bank not in self._auto_cache:
                self._auto_cache[target_bank] = auto_generate_mappings(
                    list(record.data.keys()), target_bank, self._registry
                )
            mappings = self._auto_cache[target_bank]
        else:
            mappings = self._registry.get_mappings(record.source_bank, target_bank)

        if not mappings:
            return record

        mapped_data: Dict[str, Any] = {}
        for mapping in mappings:
            value = record.data.get(mapping.source_field, mapping.default)
            if mapping.transform:
                value = self._apply_transform(value, mapping.transform)
            mapped_data[mapping.target_field] = value

        schema = self._registry.get_schema(target_bank)
        if schema:
            for field in schema.fields:
                if field not in mapped_data:
                    mapped_data[field] = None

        record.data = mapped_data
        record.target_bank = target_bank
        return record

    def _apply_transform(self, value: Any, transform: str) -> Any:
        if value is None:
            return value
        str_value = str(value)
        transforms = {
            "upper": lambda v: str(v).upper(),
            "lower": lambda v: str(v).lower(),
            "strip": lambda v: str(v).strip(),
            "title": lambda v: str(v).title(),
            "reverse": lambda v: str(v)[::-1],
        }
        handler = transforms.get(transform)
        if handler:
            return handler(value)
        if transform.startswith("prefix:"):
            return transform.split(":", 1)[1] + str(value)
        if transform.startswith("suffix:"):
            return str(value) + transform.split(":", 1)[1]
        if transform.startswith("substring:"):
            parts = transform.split(":")[1].split(",")
            start, end = int(parts[0]), int(parts[1])
            return str_value[start:end]
        return value
