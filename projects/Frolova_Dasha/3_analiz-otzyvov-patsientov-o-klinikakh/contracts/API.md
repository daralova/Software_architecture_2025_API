# API и события

`POST /api/v1/reviews` принимает JSON с review_id, clinic_id, rating (1–5), text; возвращает 201 и массив labels. `GET /api/v1/reviews/{review_id}` возвращает запись; `GET /api/v1/clinics/{clinic_id}/summary` — количество сочетаний аспекта и тональности. `/dashboard/{clinic_id}` и `/pipeline/{clinic_id}` показывают сводку. Входные отзывы должны быть обезличены до отправки.

API публикует UTF-8 JSON в `reviews.created`; consumer группы `review-analytics` сохраняет документ в Elasticsearch и публикует `reviews.indexed`. Примеры сообщений и ключи перечислены в JSON-файлах данного каталога.
