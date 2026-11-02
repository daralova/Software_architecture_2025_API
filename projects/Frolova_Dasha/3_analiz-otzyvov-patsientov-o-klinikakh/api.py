from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from html import escape
import app as service

api = FastAPI(title="Clinic Reviews")

@api.get('/health')
def health(): return {"status":"ok"}

@api.post('/api/v1/reviews', status_code=201)
def review(payload: dict):
    try: return service.add_review(payload)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@api.get('/api/v1/reviews/{review_id}')
def get_review(review_id: str):
    result=service.get_review(review_id)
    if result is None: raise HTTPException(404,'review not found')
    return result

@api.get('/api/v1/clinics/{clinic_id}/summary')
def summary(clinic_id: str): return service.clinic_summary(clinic_id)

@api.get('/dashboard/{clinic_id}', response_class=HTMLResponse)
def dashboard(clinic_id: str):
    data=service.clinic_summary(clinic_id)
    rows=''.join('<tr><td>'+escape(str(x['aspect']))+'</td><td>'+escape(str(x['sentiment']))+'</td><td>'+str(x['count'])+'</td></tr>' for x in data['aggregation'])
    total=sum(x['count'] for x in data['aggregation'])
    mode='PostgreSQL' if service.production_enabled() else 'SQLite'
    return HTMLResponse('''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Аналитика отзывов</title><style>body{font-family:Arial;background:#f3f6fb;color:#1b2639;margin:0}main{max-width:1050px;margin:40px auto;padding:0 25px}.hero{background:#194477;color:white;padding:24px;border-radius:14px}.cards{display:flex;gap:15px;margin:20px 0}.card{background:white;padding:20px;min-width:180px;border-radius:10px;box-shadow:0 2px 8px #dce4ef}.num{font-size:28px;font-weight:bold}table{background:white;width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid #e0e5ed}th{background:#dceaf9}a{color:#2466a4}</style></head><body><main><div class="hero"><h1>Аналитика отзывов пациентов</h1><p>Клиника: '''+escape(clinic_id)+'''</p></div><div class="cards"><div class="card">Размеченных аспектов<div class="num">'''+str(total)+'''</div></div><div class="card">Хранилище<div class="num">'''+mode+'''</div></div></div><h2>Аспекты и тональность</h2><table><tr><th>Аспект</th><th>Тональность</th><th>Количество</th></tr>'''+(rows or '<tr><td colspan="3">Нет данных</td></tr>')+'''</table><p><a href="/docs">Документация API</a> · <a href="/pipeline/'''+escape(clinic_id,quote=True)+'''">Pipeline</a></p></main></body></html>''')

@api.get('/pipeline/{clinic_id}', response_class=HTMLResponse)
def pipeline(clinic_id: str):
    data=service.clinic_summary(clinic_id)
    count=sum(x['count'] for x in data['aggregation'])
    return HTMLResponse('''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Review Pipeline</title><style>body{font-family:Arial;background:#122139;color:white;padding:35px}.flow{display:flex;gap:12px;flex-wrap:wrap;margin:30px 0}.step{background:#2f69b1;padding:18px;border-radius:10px}.panel{background:#20344f;padding:20px;border-radius:10px}</style></head><body><h1>Анализ потока отзывов</h1><p>Клиника: '''+escape(clinic_id)+''' · Размеченных аспектов: '''+str(count)+'''</p><div class="flow"><div class="step">Text stream</div><div class="step">Preprocessing</div><div class="step">Aspect extraction</div><div class="step">Sentiment</div><div class="step">Analytics index</div></div><div class="panel">Применяется конфигурация REVIEW_CLASSIFIER. Результаты и сводка доступны в API и dashboard.</div></body></html>''')
