# Анализ отзывов пациентов

Запускаемый сервис принимает обезличенный отзыв, выделяет аспекты и определяет базовую тональность. Правила словаря служат воспроизводимым baseline; production-профиль содержит адаптеры Hugging Face, Kafka, PostgreSQL и Elasticsearch и включается конфигурацией.

```powershell
python app.py --demo
python app.py --evaluate
python app.py --integration-status
python app.py --serve --port 8013
python -m unittest -v
```

`artifacts/review_metrics.json` содержит macro-F1 по тональности и аспектам на фиксированной тестовой выборке.

В `services.yml` включён режим `REVIEW_CLASSIFIER=corpus`: две модели TF-IDF и логистической регрессии определяют несколько аспектов и тональность фрагментов. Модель обучена на корпусе helling100/sentiment-pragmatic-med-ru (CC BY-SA 4.0; ревизия 4e0223b289a187e9538c7056609f1cb5061119bb). На 3159 отложенных предложениях macro-F1 аспектов 0,5350 против 0,3397 у словарного baseline; тональности 0,7333 против 0,3325 у baseline. Сопоставление категорий и все показатели находятся в `artifacts/clinical_corpus_metrics.json`. Пороги выбирались только по валидационной части; совпадающие фразы удалены между частями. Корпус размечен на уровне предложения, а не тональности каждого аспекта; ошибки на отрицании и нескольких темах возможны. Для воспроизведения: `python train_clinical_corpus.py`. Исходные данные загружаются по закреплённой версии.

Варианты: `REVIEW_CLASSIFIER=baseline` (словарь), `corpus`, или `transformer` (аспекты из корпуса и модель тональности из `REVIEW_MODEL`, например `blanchefort/rubert-base-cased-sentiment`). Для последнего варианта веса загружаются при первом вызове; метрики корпуса не являются его оценкой. FastAPI: `uvicorn api:api --host 127.0.0.1 --port 8013`.

Контейнер `worker` читает `reviews.created`, индексирует запись и публикует `reviews.indexed` после сохранения.

## Поток отзывов, аналитика и отчёт

`ReviewPreprocessor` приводит Unicode к NFC и нормализует пробелы, сохраняя пунктуацию и отрицания. `ReviewPipeline` вызывает выбранную Strategy; `LocalReviewObserver` сохраняет отзыв и метки в SQLite. В production API сохраняет результат в PostgreSQL, Elasticsearch и публикует событие в Kafka; worker группы `review-analytics` индексирует событие и публикует `reviews.indexed`. Производственные чтение и сводка используют PostgreSQL. Используйте только заранее обезличенные отзывы: автоматической деидентификации приложение не выполняет.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Запуск_Docker.ps1
python -X utf8 review_stream.py --input data/demo_reviews.jsonl --api-url http://127.0.0.1:18013
python -X utf8 -m unittest -v
```

Скрипт выводит адрес и команду остановки; параметр `-Port` задаёт внешний порт. Он собирает проект из временной папки с ASCII-именем, чтобы избежать ошибок Docker при кириллических путях. После запуска доступны `/docs`, `/dashboard/clinic-demo` и `/pipeline/clinic-demo`. PostgreSQL и Elasticsearch сохраняют данные в именованных томах; обычный `down` не удаляет тома. Kafka-события в учебном профиле не сохраняются между пересозданиями контейнера. В `contracts/` приведены API и JSON-сообщения; в `diagrams/` — схемы контекста и компонентов. Демонстрационные отзывы вымышлены.

Качество аспекта и тональности подтверждается сохранённым файлом `artifacts/clinical_corpus_metrics.json`; метрика относится к предложениям из корпуса и не является независимой проверкой тональности каждого аспекта. Две модели сохранены с scikit-learn 1.9.1; для корректной загрузки используйте версию из `requirements.txt`.

В контейнере проверен дополнительный режим Hugging Face `blanchefort/rubert-base-cased-sentiment`: на 15 контрольных фразах accuracy и macro-F1 составили 0,6667; это малая учебная выборка, а не оценка на независимом корпусе. Для включения задайте `REVIEW_CLASSIFIER=transformer` и `REVIEW_MODEL=blanchefort/rubert-base-cased-sentiment`; веса загружаются из Hugging Face при первом запуске.
