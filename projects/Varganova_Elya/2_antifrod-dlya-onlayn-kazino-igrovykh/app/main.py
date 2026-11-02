from fastapi import FastAPI, HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential
from app.producer import send_event

app = FastAPI()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def safe_send(topic: str, payload: dict):
    send_event(topic, payload)

@app.post("/bet")
async def post_bet(payload: dict):
    try:
        safe_send("raw_events", payload)
        return {"status": "accepted"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
