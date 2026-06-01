import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class Parser:
    @staticmethod
    def parse_name(full_name: str) -> Dict[str, str]:
        if not full_name or not full_name.strip():
            return {"first_name": "", "middle_name": "", "last_name": ""}
        parts = full_name.strip().split()
        if len(parts) == 1:
            return {"first_name": parts[0], "middle_name": "", "last_name": ""}
        elif len(parts) == 2:
            return {"first_name": parts[0], "middle_name": "", "last_name": parts[1]}
        else:
            return {
                "first_name": parts[0],
                "middle_name": " ".join(parts[1:-1]),
                "last_name": parts[-1],
            }

    @staticmethod
    def parse_date(date_str: str, source_format: str = "", target_format: str = "%d-%m-%Y") -> str:
        if not date_str or not date_str.strip():
            return ""
        date_str = date_str.strip()
        if source_format:
            try:
                dt = datetime.strptime(date_str, source_format)
                return dt.strftime(target_format)
            except ValueError:
                pass
        input_formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%Y%m%d",
            "%d %b %Y",
            "%d %B %Y",
            "%m-%d-%Y",
            "%Y.%m.%d",
            "%d.%m.%Y",
        ]
        for fmt in input_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime(target_format)
            except ValueError:
                continue
        return date_str

    @staticmethod
    def parse_address(address: str) -> Dict[str, str]:
        if not address or not address.strip():
            return {"street": "", "city": "", "state": "", "zip": "", "country": ""}
        parts = [p.strip() for p in address.split(",")]
        result: Dict[str, str] = {"street": "", "city": "", "state": "", "zip": "", "country": ""}
        if len(parts) >= 1:
            result["street"] = parts[0]
        if len(parts) >= 2:
            result["city"] = parts[1]
        if len(parts) >= 3:
            zip_state = parts[2].strip()
            zip_match = re.search(r"(\d{4,10})", zip_state)
            if zip_match:
                result["zip"] = zip_match.group(1)
                result["state"] = zip_state.replace(zip_match.group(1), "").strip()
            else:
                result["state"] = zip_state
        if len(parts) >= 4:
            result["country"] = parts[3].strip()
        return result

    @staticmethod
    def parse_currency(amount: str) -> Tuple[str, float]:
        if not amount:
            return ("", 0.0)
        amount = str(amount).strip()
        currency_map = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY",
            "₨": "PKR",
            "Rs": "PKR",
            "PKR": "PKR",
            "USD": "USD",
            "EUR": "EUR",
            "GBP": "GBP",
        }
        symbol = ""
        for sym, code in currency_map.items():
            if amount.startswith(sym) or amount.startswith(sym.lower()):
                symbol = code
                amount = amount[len(sym) :].strip()
                break
        amount_clean = re.sub(r"[^\d.,]", "", amount)
        if "," in amount_clean and "." in amount_clean:
            if amount_clean.rindex(",") > amount_clean.rindex("."):
                amount_clean = amount_clean.replace(".", "").replace(",", ".")
            else:
                amount_clean = amount_clean.replace(",", "")
        elif "," in amount_clean:
            amount_clean = amount_clean.replace(",", "")
        try:
            value = float(amount_clean)
        except ValueError:
            value = 0.0
        return (symbol, value)

    @staticmethod
    def parse_all(record: Dict[str, Any], name_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        parsed = dict(record)
        name_fields = name_fields or ["name", "full_name", "customer_name"]
        for field in name_fields:
            if field in parsed:
                name_parts = Parser.parse_name(str(parsed[field]))
                parsed.update(name_parts)
                break
        date_fields = [k for k in parsed if "date" in k.lower() or "dob" in k.lower()]
        for field in date_fields:
            parsed[field] = Parser.parse_date(str(parsed[field]))
        for field in list(parsed.keys()):
            if "address" in field.lower():
                addr = Parser.parse_address(str(parsed[field]))
                for k, v in addr.items():
                    parsed[f"{field}_{k}" if field != "address" else k] = v
                break
        for field in list(parsed.keys()):
            if "amount" in field.lower() or "balance" in field.lower() or "salary" in field.lower():
                code, value = Parser.parse_currency(str(parsed[field]))
                parsed[field] = str(value)
                if code:
                    parsed[f"{field}_currency"] = code
        return parsed
