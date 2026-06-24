import re
from typing import Any, Dict, List, Optional, Tuple

from .models import BankSchema, MappingRule, Record
from .registry import BankRegistry

# Canonical field name aliases for fuzzy matching
_FIELD_ALIASES: Dict[str, List[str]] = {
    "first_name": ["first_name", "given_name", "givennames", "firstname", "fname", "first", "given", "custfirstname", "customer_first_name", "prenom", "nombre"],
    "last_name": ["last_name", "family_name", "familyname", "lastname", "lname", "last", "surname", "custlastname", "customer_last_name", "nom", "apellido"],
    "full_name": ["full_name", "fullname", "name", "display_name", "primaryname", "primary_name", "customer_name", "custname", "account_name", "nom_complet"],
    "date_of_birth": ["date_of_birth", "dob", "birthdate", "birth_date", "dateofbirth", "birthday", "birth", "custdob", "customer_dob", "date_naissance", "fecha_nacimiento"],
    "gender": ["gender", "sex", "e-i", "ei", "gender_code", "genero", "genre"],
    "email": ["email", "email_address", "emailaddress", "mail", "e_mail", "custemail", "customer_email", "correo", "courriel"],
    "phone": ["phone", "phone_number", "phonenumber", "contact_number", "contactnumber", "mobile", "tel", "telephone", "fax", "custphone", "customer_phone", "telefono", "contacto", "contact"],
    "address": ["address", "address1", "address_1", "street", "address_line_1", "addressline1", "full_address", "street_address", "direccion"],
    "city": ["city", "town", "locality", "municipality", "ville", "ciudad"],
    "state": ["state", "province", "region", "emirate", "governorate", "estado", "departement"],
    "postal_code": ["postal_code", "postalcode", "zip", "zipcode", "zip_code", "postcode", "pincode", "cp", "codigo_postal"],
    "country": ["country", "country_code", "countrycode", "nationality", "country_of_birth", "nationalitycode", "pais", "pays", "nation", "country_name"],
    "category": ["category", "risk_category", "riskcategory", "risk_score", "riskscore", "classification", "risk_category_name"],
    "sub_category": ["sub_category", "subcategory", "sub-category", "pepclassification", "pep_class", "risk_sub_category", "risk_subcategory"],
    "uid": ["uid", "id", "record_id", "recordid", "listrecordid", "account_number", "accountnumber", "account_id", "acct_num", "acct_no", "account_no", "account_no.", "numero_compte"],
    "entered": ["entered", "added_date", "addeddate", "created", "create_date", "created_at", "createddate", "entry_date", "date_added", "fecha_creacion"],
    "updated": ["updated", "last_updated", "lastupdated", "modified", "modify_date", "updated_at", "modifieddate", "update_date", "date_updated", "fecha_modificacion"],
    "occupation": ["occupation", "job", "title", "role", "position", "profession", "ocupacion", "metier"],
    "entity_type": ["entity_type", "entitytype", "type", "record_type", "recordtype", "entity", "tipo_entidad"],
    "inactive_flag": ["inactive_flag", "inactiveflag", "inactive", "is_inactive", "status", "active", "is_active", "flag"],
    "deceased_flag": ["deceased_flag", "deceasedflag", "deceased", "is_deceased", "is_dead"],
    "passport_number": ["passport_number", "passportnumber", "passport_no", "passportno", "passport", "pasaporte", "passeport"],
    "national_id": ["national_id", "nationalid", "cnic", "ssn", "national_identity_number", "id_number", "identity_number", "dni", "nie", "cedula", "nin"],
    "source": ["source", "source_name", "sourcename", "data_source", "origin", "fuente", "origen"],
    "risk_score": ["risk_score", "riskscore", "score", "threat_score", "risk_level", "puntuacion_riesgo"],
    "pep": ["pep", "pep_flag", "pepstatus", "pep_status", "is_pep", "pep_classification"],
    "sanctions": ["sanctions", "sanctioned", "sanction_flag", "sanctions_list", "sanciones"],
    "watchlist": ["watchlist", "watch_list", "watchlist_status", "lista_vigilancia"],
    "list_name": ["list_name", "listname", "checklist_name", "checklistname", "nombre_lista"],
    "comment": ["comment", "comments", "notes", "remark", "remarks", "description", "observaciones", "comentarios"],
    "date_added": ["date_added", "dateadded", "added_date", "addeddate", "entry_date", "fecha_alta"],
    "date_updated": ["date_updated", "dateupdated", "last_updated", "lastupdated", "update_date", "fecha_baja"],
    "name_quality": ["name_quality", "namequality", "quality_score", "calidad_nombre"],
    "script_name": ["script_name", "scriptname", "original_script_name", "nombre_original"],
    "amount": ["amount", "balance", "total", "sum", "value", "monto", "saldo", "total_amount", "current_balance", "account_balance", "acct_balance"],
    "currency": ["currency", "currency_code", "currencycode", "moneda", "devise"],
    "status": ["status", "state", "condition", "estat", "estado", "situacion"],
    "type": ["type", "record_type", "entity_type", "tipo", "categorie"],
    "description": ["description", "desc", "details", "detail", "descripcion", "detalle", "observacion"],
    "date": ["date", "transaction_date", "trans_date", "fecha", "date_field"],
    "number": ["number", "num", "no", "numero", "numéro"],
    "code": ["code", "codigo", "código", "cod"],
    "name": ["name", "nombre", "nom", "denomination", "denominacion"],
    "flag": ["flag", "indicator", "indicador", "bandera"],
}

# WorldCheck -> private_individuals column mappings are resolved dynamically via
# the alias groups below (_FIELD_ALIASES); no hardcoded bank-specific table.


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _levenshtein(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _similarity(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    n1, n2 = _normalize(s1), _normalize(s2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    max_len = max(len(n1), len(n2))
    if max_len == 0:
        return 1.0
    dist = _levenshtein(n1, n2)
    return 1.0 - (dist / max_len)


def _match_field(source_col: str, target_fields: List[str]) -> Optional[str]:
    """Multi-strategy field matching for any bank-to-bank mapping."""
    norm_src = _normalize(source_col)

    # 1. Exact match (normalized)
    for tf in target_fields:
        if _normalize(tf) == norm_src:
            return tf

    # 2. Alias match — both source AND target must be in the same alias group
    for alias_key, aliases in _FIELD_ALIASES.items():
        norm_aliases = [_normalize(a) for a in aliases]
        # Check if source is in this alias group
        if norm_src in norm_aliases:
            for tf in target_fields:
                norm_tf = _normalize(tf)
                # Target is the canonical key itself
                if norm_tf == _normalize(alias_key):
                    return tf
                # Target is also in the same alias group
                if norm_tf in norm_aliases:
                    return tf
                # Target normalized matches source normalized
                if norm_tf == norm_src:
                    return tf

    # 3. Substring match
    for tf in target_fields:
        norm_tf = _normalize(tf)
        if len(norm_src) >= 4 and norm_src in norm_tf:
            return tf
        if len(norm_tf) >= 4 and norm_tf in norm_src:
            return tf

    # 4. Levenshtein similarity (typo tolerance)
    best_match = None
    best_score = 0.0
    for tf in target_fields:
        score = _similarity(source_col, tf)
        if score > 0.75 and score > best_score:
            best_score = score
            best_match = tf
    if best_match:
        return best_match

    # 5. Word-level overlap (e.g., "risk_score_percentage" matches "risk_score")
    src_words = set(re.split(r"[_\-\s]+", norm_src))
    for tf in target_fields:
        tf_words = set(re.split(r"[_\-\s]+", _normalize(tf)))
        if len(src_words) >= 2 and len(tf_words) >= 2:
            overlap = src_words & tf_words
            if len(overlap) >= 2:
                return tf
            if len(overlap) == 1 and len(overlap) / max(len(src_words), len(tf_words)) >= 0.5:
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


def infer_schema_from_columns(
    columns: List[str],
    bank_name: str = "custom_target",
    sample_values: Optional[Dict[str, Any]] = None,
) -> BankSchema:
    """Infer a BankSchema from a list of column names (e.g., from an uploaded target file)."""
    fields: Dict[str, Any] = {}
    for col in columns:
        sample = (sample_values or {}).get(col)
        field_type = "string"
        if sample is not None:
            if isinstance(sample, bool):
                field_type = "boolean"
            elif isinstance(sample, int):
                field_type = "integer"
            elif isinstance(sample, float):
                field_type = "number"
        fields[col] = {
            "type": field_type,
            "required": False,
            "default": None,
            "description": f"Auto-inferred from uploaded file column: {col}",
        }

    return BankSchema(
        bank_name=bank_name,
        version="v1.0",
        fields=fields,
        mappings=[],
        masking_rules={},
    )


def generate_custom_mappings(
    source_columns: List[str],
    target_columns: List[str],
) -> List[MappingRule]:
    """Generate mappings between source file columns and target file columns using multi-strategy matching."""
    mappings: List[MappingRule] = []
    used_targets: set = set()

    for src_col in source_columns:
        matched = _match_field(src_col, target_columns)
        if matched and matched not in used_targets:
            mappings.append(
                MappingRule(
                    source_field=src_col,
                    target_field=matched,
                    transform="",
                    required=False,
                    default=None,
                )
            )
            used_targets.add(matched)

    return mappings


def register_custom_target(
    registry: BankRegistry,
    target_columns: List[str],
    sample_values: Optional[Dict[str, Any]] = None,
    bank_name: str = "custom_target",
) -> str:
    """Register a dynamically-inferred schema from uploaded target file columns."""
    schema = infer_schema_from_columns(target_columns, bank_name, sample_values)
    return registry.register_bank(bank_name, schema)
