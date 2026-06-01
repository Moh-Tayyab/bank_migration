from typing import Any, Callable, Dict, List, Optional

from .models import Record


class Rule:
    def __init__(self, name: str, condition: Callable[[Dict], bool], action: Callable[[Dict], Dict]):
        self.name = name
        self.condition = condition
        self.action = action

    def apply(self, data: Dict) -> Optional[Dict]:
        if self.condition(data):
            return self.action(data)
        return None


class RulesEngine:
    def __init__(self, rules_engine: Optional["RulesEngine"] = None):
        self._global_rules: List[Rule] = []
        self._bank_rules: Dict[str, List[Rule]] = {}
        if rules_engine is not None:
            self._global_rules = list(rules_engine._global_rules)
            self._bank_rules = dict(rules_engine._bank_rules)

    def add_rule(self, rule: Rule, bank: str = ""):
        if bank:
            self._bank_rules.setdefault(bank, []).append(rule)
        else:
            self._global_rules.append(rule)

    def apply(self, record: Record) -> Dict[str, Any]:
        data = dict(record.data)
        for rule in self._global_rules:
            result = rule.apply(data)
            if result:
                data = result
        bank_rules = self._bank_rules.get(record.target_bank, [])
        for rule in bank_rules:
            result = rule.apply(data)
            if result:
                data = result
        return data


def build_standard_rules() -> RulesEngine:
    engine = RulesEngine()

    engine.add_rule(
        Rule(
            name="empty_to_null",
            condition=lambda d: True,
            action=lambda d: {k: (v if v != "" else None) for k, v in d.items()},
        )
    )

    engine.add_rule(
        Rule(
            name="strip_whitespace",
            condition=lambda d: True,
            action=lambda d: {k: (v.strip() if isinstance(v, str) else v) for k, v in d.items()},
        )
    )

    engine.add_rule(
        Rule(
            name="capitalize_names",
            condition=lambda d: any(k.endswith("_name") for k in d),
            action=lambda d: {
                k: (v.title() if k.endswith("_name") and isinstance(v, str) else v) for k, v in d.items()
            },
        )
    )

    return engine
