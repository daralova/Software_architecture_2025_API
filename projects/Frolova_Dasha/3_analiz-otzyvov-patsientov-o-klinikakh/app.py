"""Runnable aspect and sentiment analytics service for anonymized clinic reviews."""
from __future__ import annotations
import argparse, asyncio, json, re, sqlite3
import importlib.util
import os
from contextlib import contextmanager
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent; DB_PATH=ROOT/"reviews.db"
ASPECTS={"врач":("врач","доктор","специалист"),"ожидание":("ждал","ожидан","очеред"),"сервис":("сервис","администратор","регистрат"),"стоимость":("цен","стоим","дорого","оплат"),"результат лечения":("лечение","результат","выздоров","боль")}
POSITIVE={"хорош","вниматель","спасибо","отличн","помог","чист"}; NEGATIVE={"плох","долго","очеред","груб","дорог","боль","ужас"}
PRODUCTION_PACKAGES={"Hugging Face Transformers":"transformers","Kafka (aiokafka)":"aiokafka","PostgreSQL (asyncpg)":"asyncpg","Elasticsearch":"elasticsearch"}

def production_enabled()->bool:
    return os.environ.get("PRODUCTION_MODE","").lower() in {"1","true","yes"}

def integration_status()->dict[str,Any]:
    return {"packages":{name:bool(importlib.util.find_spec(module)) for name,module in PRODUCTION_PACKAGES.items()},"model":os.environ.get("REVIEW_MODEL","local-lexicon-baseline"),"weights":os.environ.get("REVIEW_MODEL_REVISION","not-configured"),"production_mode":production_enabled(),"network_probe":"not_run","storage":"postgres-elasticsearch-kafka" if production_enabled() else "sqlite-baseline"}

class HuggingFaceReviewClassifier:
    """Optional transformer classifier; no model download occurs implicitly."""
    def __init__(self, model_id:str|None=None):
        model_id=model_id or os.environ.get("REVIEW_MODEL")
        if not model_id: raise ValueError("REVIEW_MODEL is required for transformer mode")
        from transformers import pipeline
        self.model_id=model_id
        self.pipeline=pipeline("text-classification",model=model_id,tokenizer=model_id)
    def predict(self,text:str)->dict[str,Any]:
        result=self.pipeline(text,truncation=True)[0]
        return {"label":str(result["label"]),"score":round(float(result["score"]),4),"model":self.model_id}


_review_classifier = None
_aspect_classifier = None
_corpus_models = None

def classify_corpus(text: str, use_transformer: bool = False)->list[dict[str,Any]]:
    """Classify aspects and polarity for each clause using the clinic corpus."""
    global _corpus_models, _review_classifier
    if _corpus_models is None:
        import joblib
        _corpus_models = (joblib.load(ROOT/'artifacts'/'clinical_aspect_model.joblib'),
                          joblib.load(ROOT/'artifacts'/'clinical_sentiment_model.joblib'))
    aspect_bundle, sentiment_bundle = _corpus_models
    if use_transformer and _review_classifier is None:
        _review_classifier = HuggingFaceReviewClassifier()
    clauses = [part.strip() for part in re.split(r'[.!?;]+|\bно\b|\bоднако\b', text, flags=re.IGNORECASE) if part.strip()]
    output = {}
    for clause in clauses or [text]:
        probabilities = aspect_bundle['model'].predict_proba([clause])[0]
        names = [name for name, value, threshold in zip(aspect_bundle['classes'], probabilities, aspect_bundle['thresholds']) if value >= threshold]
        if not names: names = ['общее впечатление']
        if use_transformer:
            prediction = _review_classifier.predict(clause)
            raw = prediction['label'].lower()
            sentiment = 'positive' if raw in {'positive','pos','label_2'} else 'negative' if raw in {'negative','neg','label_0'} else 'neutral'
            confidence = prediction['score']
        else:
            model = sentiment_bundle['model']
            probabilities_sent = model.predict_proba([clause])[0]
            index = int(probabilities_sent.argmax())
            sentiment = str(model.classes_[index]); confidence = round(float(probabilities_sent[index]),4)
        for name in names:
            output[name] = {'aspect':name, 'sentiment':sentiment, 'score':confidence}
    return list(output.values())

def classify_model(text: str)->list[dict[str,Any]]:
    """Use a transformer for clause-level sentiment and preserve aspect context."""
    global _review_classifier, _aspect_classifier
    if _review_classifier is None:
        _review_classifier = HuggingFaceReviewClassifier()
    if _aspect_classifier is None:
        import joblib
        _aspect_classifier = joblib.load(ROOT/"artifacts"/"aspect_classifier.joblib")
    clauses = [part.strip() for part in re.split(r"[.!?;]+|\bно\b|\bоднако\b", text, flags=re.IGNORECASE) if part.strip()]
    result = []
    for clause in clauses or [text]:
        probabilities = _aspect_classifier.predict_proba([clause])[0]
        max_index = int(probabilities.argmax())
        aspect_names = [str(_aspect_classifier.classes_[max_index])] if float(probabilities[max_index]) >= 0.25 else ["общее впечатление"]
        prediction = _review_classifier.predict(clause)
        label = prediction["label"].lower()
        sentiment = "positive" if label in {"positive", "pos", "label_2"} else "negative" if label in {"negative", "neg", "label_0"} else "neutral"
        for aspect in aspect_names:
            result.append({"aspect": aspect, "sentiment": sentiment, "score": prediction["score"]})
    if not result:
        prediction = _review_classifier.predict(text)
        label = prediction["label"].lower()
        sentiment = "positive" if label in {"positive", "pos", "label_2"} else "negative" if label in {"negative", "neg", "label_0"} else "neutral"
        result.append({"aspect":"общее впечатление", "sentiment":sentiment, "score":prediction["score"]})
    return list({item["aspect"]:item for item in result}.values())

class KafkaReviewPublisher:
    topic="reviews.created"
    async def publish(self,event:dict[str,Any])->None:
        from aiokafka import AIOKafkaProducer
        producer=AIOKafkaProducer(bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS","kafka:9092")); await producer.start()
        try: await producer.send_and_wait(self.topic,json.dumps(event,ensure_ascii=False).encode("utf-8"),key=event['review_id'].encode('utf-8'))
        finally: await producer.stop()

class ReviewAnalyticsConsumer:
    """Consumer contract for indexing labelled reviews and summaries."""
    topic="reviews.created"; group_id="review-analytics"
    async def consume_once(self)->dict[str,Any]:
        from aiokafka import AIOKafkaConsumer
        consumer=AIOKafkaConsumer(self.topic,bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS","kafka:9092"),group_id=self.group_id); await consumer.start()
        try:
            message=await consumer.getone(); return json.loads(message.value.decode("utf-8"))
        finally: await consumer.stop()

class PostgresReviewRepository:
    async def save(self,review:dict[str,Any])->None:
        import asyncpg
        con=await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            await con.execute("CREATE TABLE IF NOT EXISTS clinic_reviews (review_id text primary key, clinic_id text not null, rating int not null, text text not null, labels jsonb not null, created_at timestamptz not null)")
            await con.execute("CREATE INDEX IF NOT EXISTS idx_clinic_reviews_clinic_time ON clinic_reviews(clinic_id,created_at)")
            await con.execute("INSERT INTO clinic_reviews VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(review_id) DO UPDATE SET clinic_id=EXCLUDED.clinic_id, rating=EXCLUDED.rating, text=EXCLUDED.text, labels=EXCLUDED.labels, created_at=EXCLUDED.created_at",review["review_id"],review["clinic_id"],review["rating"],review["text"],json.dumps(review["labels"],ensure_ascii=False),datetime.fromisoformat(review["created_at"]))
        finally: await con.close()

class ElasticsearchReviewIndex:
    def __init__(self):
        from elasticsearch import Elasticsearch
        self.client=Elasticsearch(os.environ.get("ELASTICSEARCH_URL","http://elasticsearch:9200"),request_timeout=120,retry_on_timeout=True,max_retries=3)
    def index(self,review:dict[str,Any])->None:
        self.client.index(index="clinic-reviews",id=review["review_id"],document=review,refresh="wait_for")
@contextmanager
def db():
    con=sqlite3.connect(DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with db() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS reviews(review_id TEXT PRIMARY KEY, clinic_id TEXT NOT NULL, rating INTEGER NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS labels(review_id TEXT NOT NULL, aspect TEXT NOT NULL, sentiment TEXT NOT NULL, score REAL NOT NULL, PRIMARY KEY(review_id,aspect)); CREATE INDEX IF NOT EXISTS idx_reviews_clinic ON reviews(clinic_id); CREATE INDEX IF NOT EXISTS idx_labels_sentiment ON labels(sentiment);""")

def classify(text: str)->list[dict[str,Any]]:
    lower=text.lower(); words=re.findall(r"[а-яёa-z]+",lower); pos=sum(any(w.startswith(s) for s in POSITIVE) for w in words); neg=sum(any(w.startswith(s) for s in NEGATIVE) for w in words); sentiment="positive" if pos>neg else "negative" if neg>pos else "neutral"; score=round((pos-neg)/max(1,len(words)),3)
    found=[name for name, keys in ASPECTS.items() if any(key in lower for key in keys)] or ["общее впечатление"]
    return [{"aspect":a,"sentiment":sentiment,"score":score} for a in found]

class BaselineReviewStrategy:
    def classify(self, text): return classify(text)

class CorpusReviewStrategy:
    def classify(self, text): return classify_corpus(text)

class TransformerReviewStrategy:
    def classify(self, text): return classify_corpus(text, use_transformer=True)

def review_strategy(mode):
    strategies={'baseline':BaselineReviewStrategy,'corpus':CorpusReviewStrategy,'transformer':TransformerReviewStrategy}
    if mode not in strategies: raise ValueError('REVIEW_CLASSIFIER must be baseline, corpus, or transformer')
    return strategies[mode]()

class ReviewPreprocessor:
    """Normalize whitespace while preserving negation, case and punctuation."""
    def process(self,text):
        import unicodedata
        return re.sub(r'\s+', ' ', unicodedata.normalize('NFC',text)).strip()

class ReviewPipeline:
    """Preprocess text and apply a configurable aspect/sentiment strategy."""
    def __init__(self,mode): self.mode=mode; self.preprocessor=ReviewPreprocessor()
    def run(self,text):
        normalized=self.preprocessor.process(text)
        return normalized,review_strategy(self.mode).classify(normalized)

class ReviewObserver:
    def update(self,review): raise NotImplementedError

class LocalReviewObserver(ReviewObserver):
    """Write the labeled event and its analytical dimensions atomically."""
    def update(self,review):
        with db() as c:
            c.execute("INSERT OR REPLACE INTO reviews VALUES(?,?,?,?,?)",(review['review_id'],review['clinic_id'],review['rating'],review['text'],review['created_at']))
            c.execute("DELETE FROM labels WHERE review_id=?",(review['review_id'],))
            c.executemany("INSERT INTO labels VALUES(?,?,?,?)",[(review['review_id'],x['aspect'],x['sentiment'],x['score']) for x in review['labels']])

def add_review(payload:dict[str,Any])->dict[str,Any]:
    init_db(); review_id=payload.get("review_id"); clinic_id=payload.get("clinic_id"); text=payload.get("text"); rating=payload.get("rating")
    if not all(isinstance(x,str) and x.strip() for x in (review_id,clinic_id,text)): raise ValueError("review_id, clinic_id and text must be non-empty strings")
    if isinstance(rating,bool) or not isinstance(rating,int) or not 1<=rating<=5: raise ValueError("rating must be integer from 1 to 5")
    if len(text)>10000 or len(review_id)>120 or len(clinic_id)>120: raise ValueError('input length exceeds limit')
    mode=os.environ.get('REVIEW_CLASSIFIER','baseline')
    text,labels=ReviewPipeline(mode).run(text)
    created_at=datetime.now(timezone.utc).isoformat()
    result={"review_id":review_id,"clinic_id":clinic_id,"rating":rating,"text":text.strip(),"labels":labels,"created_at":created_at}
    LocalReviewObserver().update(result)
    if production_enabled():
        asyncio.run(PostgresReviewRepository().save(result))
        ElasticsearchReviewIndex().index(result)
        asyncio.run(KafkaReviewPublisher().publish(result))
        result["production"]={"postgres":True,"elasticsearch_index":"clinic-reviews","kafka_topic":KafkaReviewPublisher.topic}
    return result

def get_review(review_id:str):
    if production_enabled():
        async def fetch():
            import asyncpg
            c=await asyncpg.connect(os.environ['DATABASE_URL'])
            try: return await c.fetchrow('SELECT review_id,clinic_id,rating,text,labels,created_at FROM clinic_reviews WHERE review_id=$1',review_id)
            finally: await c.close()
        try: row=asyncio.run(fetch())
        except Exception as e:
            if type(e).__name__=='UndefinedTableError': return None
            raise
        if row is None: return None
        return {'review_id':row['review_id'],'clinic_id':row['clinic_id'],'rating':row['rating'],'text':row['text'],'labels':json.loads(row['labels']) if isinstance(row['labels'],str) else row['labels'],'created_at':row['created_at'].isoformat()}
    init_db()
    with db() as c:
        r=c.execute("SELECT review_id,clinic_id,rating,text,created_at FROM reviews WHERE review_id=?",(review_id,)).fetchone(); labels=c.execute("SELECT aspect,sentiment,score FROM labels WHERE review_id=?",(review_id,)).fetchall()
    return None if not r else {"review_id":r[0],"clinic_id":r[1],"rating":r[2],"text":r[3],"created_at":r[4],"labels":[{"aspect":x[0],"sentiment":x[1],"score":x[2]} for x in labels]}

def clinic_summary(clinic_id:str):
    if production_enabled():
        async def fetch():
            import asyncpg
            c=await asyncpg.connect(os.environ['DATABASE_URL'])
            try:
                if not await c.fetchval("SELECT to_regclass('public.clinic_reviews')"): return []
                return await c.fetch("SELECT l->>'aspect' AS aspect,l->>'sentiment' AS sentiment,count(*) AS count FROM clinic_reviews r CROSS JOIN LATERAL jsonb_array_elements(r.labels) l WHERE r.clinic_id=$1 GROUP BY 1,2 ORDER BY 1,2",clinic_id)
            finally: await c.close()
        rows=asyncio.run(fetch())
        return {'clinic_id':clinic_id,'aggregation':[dict(r) for r in rows]}
    init_db()
    with db() as c:
        rows=c.execute("SELECT l.aspect,l.sentiment,COUNT(*) FROM reviews r JOIN labels l ON l.review_id=r.review_id WHERE r.clinic_id=? GROUP BY l.aspect,l.sentiment",(clinic_id,)).fetchall()
    return {"clinic_id":clinic_id,"aggregation":[{"aspect":r[0],"sentiment":r[1],"count":r[2]} for r in rows]}

def evaluate_classifier()->dict[str,Any]:
    """Reproducible macro-F1 evaluation of the local classifier."""
    from sklearn.metrics import f1_score, precision_score, recall_score
    samples=[
        ("Врач внимательный, лечение помогло", "positive", ["врач","результат лечения"]),
        ("Долго ждал в очереди, сервис плохой", "negative", ["ожидание","сервис"]),
        ("Стоимость и расписание указаны заранее", "neutral", ["стоимость"]),
        ("Доктор помог, но оплата дорогая", "positive", ["врач","стоимость"]),
        ("Ужасная очередь и грубый администратор", "negative", ["ожидание","сервис"]),
        ("Результат лечения стабильный", "positive", ["результат лечения"]),
    ]
    y_true=[x[1] for x in samples]; y_pred=[]; aspect_true=[]; aspect_pred=[]
    for text,sent,aspects in samples:
        labels=classify(text); y_pred.append(labels[0]["sentiment"]); aspect_true.extend(aspects); aspect_pred.extend([x["aspect"] for x in labels])
    metrics={"samples":len(samples),"sentiment":{"macro_f1":round(float(f1_score(y_true,y_pred,average="macro")),4),"precision":round(float(precision_score(y_true,y_pred,average="macro",zero_division=0)),4),"recall":round(float(recall_score(y_true,y_pred,average="macro",zero_division=0)),4)},"aspect":{"macro_f1":round(float(f1_score(aspect_true,aspect_pred,average="macro")),4)},"model":"lexicon-baseline","seed":20261027}
    (Path(__file__).resolve().parent/"artifacts").mkdir(exist_ok=True)
    (Path(__file__).resolve().parent/"artifacts"/"review_metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    return metrics


def evaluate_transformer()->dict[str,Any]:
    """Evaluate clause sentiment on a small explicitly labelled set."""
    from sklearn.metrics import accuracy_score, f1_score
    samples=[
        ("Врач внимательный", "positive"), ("Доктор замечательный и очень помог", "positive"),
        ("Отличный сервис и вежливые сотрудники", "positive"), ("Лечение прошло успешно", "positive"),
        ("Клиника очень понравилась", "positive"), ("Врач грубый и невнимательный", "negative"),
        ("Ужасное обслуживание, никому не советую", "negative"), ("Очень дорого и плохо", "negative"),
        ("Долгая очередь испортила впечатление", "negative"), ("Мне не помогло лечение", "negative"),
        ("Приём состоялся в понедельник", "neutral"), ("Клиника работает каждый день", "neutral"),
        ("Стоимость приёма указана на сайте", "neutral"), ("Записался на вторник", "neutral"),
        ("Доктор назначил обследование", "neutral"),
    ]
    model=HuggingFaceReviewClassifier()
    truth=[x[1] for x in samples]
    predictions=[model.predict(x[0])["label"].lower() for x in samples]
    result={"model":model.model_id,"samples":len(samples),"dataset":"manually authored control phrases","accuracy":round(float(accuracy_score(truth,predictions)),4),"macro_f1":round(float(f1_score(truth,predictions,labels=["negative","neutral","positive"],average="macro",zero_division=0)),4),"items":[{"text":s[0],"expected":s[1],"predicted":p} for s,p in zip(samples,predictions)]}
    (ROOT/"artifacts"/"transformer_metrics.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

class Api(BaseHTTPRequestHandler):
    def respond(self,status,data):
        raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        if self.path!="/api/v1/reviews": return self.respond(404,{"error":"not found"})
        try: self.respond(201,add_review(json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))).decode())))
        except (ValueError,json.JSONDecodeError) as e: self.respond(422,{"error":str(e)})
    def do_GET(self):
        if self.path=="/health": return self.respond(200,{"status":"ok","database":DB_PATH.exists()})
        if self.path.startswith("/api/v1/reviews/"):
            x=get_review(self.path.rsplit("/",1)[-1]); return self.respond(200 if x else 404,x or {"error":"review not found"})
        if self.path.startswith("/api/v1/clinics/") and self.path.endswith("/summary"): return self.respond(200,clinic_summary(self.path.split("/")[4]))
        self.respond(404,{"error":"not found"})
    def log_message(self,*_): return

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--serve",action="store_true"); p.add_argument("--port",type=int,default=8013); p.add_argument("--demo",action="store_true"); p.add_argument("--evaluate",action="store_true"); p.add_argument("--evaluate-model",action="store_true"); p.add_argument("--integration-status",action="store_true"); a=p.parse_args()
    if a.demo: print(json.dumps(add_review({"review_id":"rev-demo","clinic_id":"cl-12","rating":2,"text":"Долго ждал приёма, но врач внимательный"}),ensure_ascii=False,indent=2))
    if a.evaluate: print(json.dumps(evaluate_classifier(),ensure_ascii=False,indent=2))
    if a.evaluate_model: print(json.dumps(evaluate_transformer(),ensure_ascii=False,indent=2))
    if a.integration_status: print(json.dumps(integration_status(),ensure_ascii=False,indent=2))
    if a.serve: init_db(); print(f"Reviews API: http://127.0.0.1:{a.port}"); ThreadingHTTPServer(("0.0.0.0",a.port),Api).serve_forever()
