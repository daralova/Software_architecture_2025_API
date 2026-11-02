from kafka import KafkaConsumer
import json
from app.producer import send_event
from app.feature_service import get_cached_features, compute_historical_features
from app.rule_engine import ChainOfResponsibility, HighStakeRule, RapidBetsRule
from app.ml_scoring import predict_fraud_score
from app.case_management import CaseFactory, CaseRepository
from dataclasses import asdict

consumer = KafkaConsumer(
    "raw_events",
    bootstrap_servers=["kafka:29092"],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset="latest",
    enable_auto_commit=False,
)

rule_chain = ChainOfResponsibility([HighStakeRule(), RapidBetsRule()])
case_repo = CaseRepository()

for msg in consumer:
    event = msg.value
    account_id = event["account_id"]

    features = get_cached_features(account_id)
    if not features:
        hist = compute_historical_features([account_id])
        features = hist.to_dict(orient="records")[0] if not hist.empty else {}

    rules_violated = rule_chain.run(event | features)
    score = predict_fraud_score(features | event)

    case = CaseFactory.create(account_id, event["event_id"], score, rules_violated)
    case_repo.save(case)

    enriched = event | features | {"fraud_score": score, "rules_violated": rules_violated}
    send_event("enriched_events", enriched)
    send_event("fraud_cases", asdict(case))

    consumer.commit()
