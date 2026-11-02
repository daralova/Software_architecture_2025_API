"""Train and evaluate a small Russian aspect classifier on authored examples."""
import json
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.pipeline import make_pipeline

ROOT=Path(__file__).resolve().parent
samples={
 'врач': [('Врач внимательно меня осмотрел','train'),('Доктор был добрым','train'),('Специалист всё подробно объяснил','train'),('Врач грубо разговаривал','train'),('Доктор профессиональный','train'),('Внимательный врач','train'),('Доктор показался невежливым','train'),('Специалист ответил на вопросы','train'),('Хороший лечащий врач','test'),('Доктор внимательно выслушал','test')],
 'ожидание': [('Долго ждал приёма','train'),('В очереди провёл час','train'),('Пришлось долго ожидать','train'),('Очередь двигалась медленно','train'),('Ждал записи несколько дней','train'),('Приём задержали на час','train'),('Ожидание было долгим','train'),('Быстро вызвали на приём','train'),('Долго сидел в очереди','test'),('Не пришлось долго ждать','test')],
 'сервис': [('Администратор очень вежливый','train'),('Регистратура работает плохо','train'),('Сервис клиники понравился','train'),('Сотрудники на ресепшене грубые','train'),('Хорошее обслуживание пациентов','train'),('Персонал клиники дружелюбный','train'),('Администратор помог с записью','train'),('Регистратор не ответил на звонок','train'),('Сервис и персонал замечательные','test'),('Грубый администратор на ресепшене','test')],
 'стоимость': [('Стоимость приёма высокая','train'),('Цена обследования доступная','train'),('Оплата лечения слишком дорогая','train'),('Цены клиники разумные','train'),('За приём взяли много денег','train'),('Лечение дорогое','train'),('Стоимость услуг приятно удивила','train'),('Оплатил консультацию картой','train'),('Цена оказалась очень высокой','test'),('Стоимость диагностики низкая','test')],
 'результат лечения': [('Лечение помогло избавиться от боли','train'),('После терапии стало лучше','train'),('Результат лечения отличный','train'),('Назначенное лечение не помогло','train'),('После операции быстро выздоровел','train'),('Симптомы прошли после терапии','train'),('Боль не ушла после лечения','train'),('Лечение оказалось успешным','train'),('Терапия помогла и боль прошла','test'),('Результат лечения плохой','test')],
}
rows=[{'text':text,'aspect':aspect,'split':split} for aspect,items in samples.items() for text,split in items]
train=[x for x in rows if x['split']=='train']; test=[x for x in rows if x['split']=='test']
model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(2,5),lowercase=True),LogisticRegression(max_iter=1000,random_state=42))
model.fit([x['text'] for x in train],[x['aspect'] for x in train])
pred=model.predict([x['text'] for x in test])
metrics=classification_report([x['aspect'] for x in test],pred,output_dict=True,zero_division=0)
result={'train_samples':len(train),'test_samples':len(test),'dataset':'manually authored phrases','accuracy':metrics['accuracy'],'macro_f1':metrics['macro avg']['f1-score'],'items':[dict(item,predicted=str(p)) for item,p in zip(test,pred)]}
(ROOT/'artifacts'/'aspect_examples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'artifacts'/'aspect_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
joblib.dump(model,ROOT/'artifacts'/'aspect_classifier.joblib')
print(json.dumps(result,ensure_ascii=False,indent=2))
