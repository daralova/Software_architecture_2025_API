import redis
import pandas as pd
from clickhouse_driver import Client
import json
from app.config import Config

redis_client = redis.Redis(host=Config.REDIS_HOST, decode_responses=True)
ch_client = Client(host=Config.CLICKHOUSE_HOST)

def get_cached_features(account_id: str) -> dict | None:
    data = redis_client.get(f"features:{account_id}")
    return json.loads(data) if data else None

def save_cached_features(account_id: str, features: dict, ttl_seconds: int = 300):
    redis_client.setex(f"features:{account_id}", ttl_seconds, json.dumps(features))

def compute_historical_features(account_ids: list) -> pd.DataFrame:
    ids_str = ", ".join(f"'{i}'" for i in account_ids)
    query = f"""
        SELECT account_id, avg_bet, max_bet, total_volume, bets_count, last_bet_ts
        FROM bets_history
        WHERE account_id IN ({ids_str})
        GROUP BY account_id
    """
    result = ch_client.execute(query, columnar=True)
    return pd.DataFrame(dict(zip(["account_id","avg_bet","max_bet","total_volume","bets_count","last_bet_ts"], result)))
