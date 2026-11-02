from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
import psycopg2
from app.config import Config

class CaseStatus(Enum):
    OPEN = "open"
    INVESTIGATION = "investigation"
    CLOSED = "closed"

@dataclass
class FraudCase:
    account_id: str
    event_id: str
    score: float
    rules_violated: list[str]
    status: CaseStatus
    notes: Optional[str] = None

class CaseFactory:
    @staticmethod
    def create(account_id: str, event_id: str, score: float, rules_violated: list[str]) -> FraudCase:
        if score > 0.8 or len(rules_violated) > 0:
            status = CaseStatus.OPEN
        else:
            status = CaseStatus.CLOSED
        return FraudCase(account_id=account_id, event_id=event_id, score=score, rules_violated=rules_violated, status=status)

class CaseRepository:
    def __init__(self):
        self.conn = psycopg2.connect(Config.PG_DSN)
    def save(self, case: FraudCase):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fraud_cases (account_id, event_id, score, rules_violated, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (case.account_id, case.event_id, case.score, ",".join(case.rules_violated), case.status.value, case.notes))
        self.conn.commit()
