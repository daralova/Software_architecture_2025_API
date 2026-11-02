from abc import ABC, abstractmethod
from typing import List, Dict, Any

class RuleStrategy(ABC):
    @abstractmethod
    def check(self, event: Dict[str, Any]) -> bool:
        pass

class HighStakeRule(RuleStrategy):
    def __init__(self, threshold: float = 1000.0):
        self.threshold = threshold
    def check(self, event: Dict) -> bool:
        return event.get("bet_amount", 0) > self.threshold

class RapidBetsRule(RuleStrategy):
    def __init__(self, max_bets_per_minute: int = 5):
        self.max = max_bets_per_minute
    def check(self, event: Dict) -> bool:
        return event.get("rapid_bets_count", 0) > self.max

class ChainOfResponsibility:
    def __init__(self, rules: List[RuleStrategy]):
        self.rules = rules
    def run(self, event: Dict[str, Any]) -> List[str]:
        violations = []
        for rule in self.rules:
            if rule.check(event):
                violations.append(rule.__class__.__name__)
        return violations
