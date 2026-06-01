import re
from typing import Dict, Any, List, Optional
from .models import AuditEvent
from .audit_logger import AuditLogger


class SecurityMasker:
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self._audit = audit_logger
        self._masking_rules: Dict[str, str] = {
            "account_number": "show_last_4",
            "email": "mask_email",
            "phone": "show_last_4",
            "cnic": "show_last_4",
            "ssn": "show_last_4",
            "passport": "show_last_4",
        }

    def set_bank_rules(self, rules: Dict[str, str]):
        self._masking_rules.update(rules)

    def mask(self, data: Dict[str, Any], record_id: str = "") -> Dict[str, Any]:
        masked = dict(data)
        for field, value in data.items():
            if not isinstance(value, str) or not value.strip():
                continue
            rule = self._detect_rule(field, value)
            if rule:
                masked[field] = self._apply_rule(value, rule)
                if self._audit:
                    self._audit.log(
                        AuditEvent.SECURITY_MASK,
                        record_id=record_id,
                        details=f"Masked field '{field}' with rule '{rule}'",
                    )
        return masked

    def _detect_rule(self, field: str, value: str) -> Optional[str]:
        field_lower = field.lower()
        if field_lower in self._masking_rules:
            return self._masking_rules[field_lower]
        for pattern, rule in self._auto_detect_patterns().items():
            if re.search(pattern, value):
                return rule
        if any(keyword in field_lower for keyword in ["account", "acct", "iban"]):
            return "show_last_4"
        if any(keyword in field_lower for keyword in ["email", "e-mail"]):
            return "mask_email"
        if any(keyword in field_lower for keyword in ["phone", "mobile", "contact", "tel"]):
            return "show_last_4"
        if any(keyword in field_lower for keyword in ["cnic", "ssn", "passport", "id_number", "identity"]):
            return "show_last_4"
        return None

    def _auto_detect_patterns(self) -> Dict[str, str]:
        return {
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': "mask_email",
            r'\b\d{16}\b': "show_last_4",
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b': "show_last_4",
            r'\b\d{13}\b': "show_last_4",
            r'\b\d{3}-\d{3}-\d{4}\b': "show_last_4",
            r'\b\d{5}-\d{7}-\d\b': "show_last_4",
        }

    def _apply_rule(self, value: str, rule: str) -> str:
        rules = {
            "show_last_4": self._mask_show_last_4,
            "show_last_6": self._mask_show_last_6,
            "mask_email": self._mask_email,
            "mask_all": lambda v: "*" * len(v),
            "mask_first_half": self._mask_first_half,
        }
        handler = rules.get(rule)
        if handler:
            return handler(value)
        return value

    def _mask_show_last_4(self, value: str) -> str:
        digits = re.sub(r'\D', '', value)
        if len(digits) <= 4:
            return value
        masked_digits = "*" * (len(digits) - 4) + digits[-4:]
        result = []
        digit_idx = 0
        for char in value:
            if char.isdigit():
                result.append(masked_digits[digit_idx])
                digit_idx += 1
            else:
                result.append(char)
        return "".join(result)

    def _mask_show_last_6(self, value: str) -> str:
        digits = re.sub(r'\D', '', value)
        if len(digits) <= 6:
            return value
        return "*" * (len(digits) - 6) + digits[-6:]

    def _mask_email(self, value: str) -> str:
        parts = value.split("@")
        if len(parts) != 2:
            return value
        local = parts[0]
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        domain = parts[1]
        domain_parts = domain.split(".")
        if len(domain_parts) > 0:
            domain_parts[0] = domain_parts[0][0] + "*" * (len(domain_parts[0]) - 1) if domain_parts[0] else ""
        return f"{masked_local}@{'.'.join(domain_parts)}"

    def _mask_first_half(self, value: str) -> str:
        mid = len(value) // 2
        return "*" * mid + value[mid:]