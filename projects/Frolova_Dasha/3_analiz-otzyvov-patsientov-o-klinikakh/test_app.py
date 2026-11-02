import tempfile,unittest
from unittest.mock import patch
from pathlib import Path
import app
class ReviewTest(unittest.TestCase):
 def setUp(self):
  self.environment=patch.dict('os.environ',{'PRODUCTION_MODE':'','REVIEW_CLASSIFIER':'baseline'}); self.environment.start()
  self.tmp=tempfile.TemporaryDirectory(); app.DB_PATH=Path(self.tmp.name)/"reviews.db"
 def tearDown(self): self.tmp.cleanup(); self.environment.stop()
 def test_aspect_and_sentiment(self):
  x=app.add_review({"review_id":"r1","clinic_id":"c1","rating":2,"text":"Долго ждал, но врач внимательный"}); self.assertIn("ожидание",[a["aspect"] for a in x["labels"]]); self.assertIsNotNone(app.get_review("r1"))
 def test_corpus_mode_classifies_mixed_review(self):
  with patch.dict("os.environ", {"REVIEW_CLASSIFIER":"corpus"}):
   result=app.add_review({"review_id":"r3","clinic_id":"c1","rating":2,"text":"Врач внимательный, но ожидание было ужасным и долгим"})
  labels={item["aspect"]:item["sentiment"] for item in result["labels"]}
  self.assertEqual(labels["врач"],"positive");self.assertEqual(labels["ожидание"],"negative")
 def test_unknown_strategy_rejected(self):
  with self.assertRaises(ValueError): app.review_strategy('unknown')
 def test_empty_review_rejected(self):
  with self.assertRaises(ValueError): app.add_review({"review_id":"r2","clinic_id":"c1","rating":3,"text":""})
 def test_preprocessing_and_unicode(self):
  with patch.dict('os.environ',{'REVIEW_CLASSIFIER':'baseline','PRODUCTION_MODE':''}):
   result=app.add_review({'review_id':'unicode','clinic_id':'клиника','rating':3,'text':'  Врач   внимательный\nи вежливый  '})
  self.assertEqual(result['text'],'Врач внимательный и вежливый')
  self.assertEqual(app.get_review('unicode')['clinic_id'],'клиника')
 def test_update_does_not_duplicate_aggregation(self):
  payload={'review_id':'same','clinic_id':'clinic','rating':3,'text':'Врач внимательный'}
  with patch.dict('os.environ',{'REVIEW_CLASSIFIER':'baseline','PRODUCTION_MODE':''}):
   app.add_review(payload); app.add_review(payload)
   rows=app.clinic_summary('clinic')['aggregation']
  self.assertEqual(sum(x['count'] for x in rows),1)
 def test_invalid_rating_and_missing_id(self):
  for payload in [{'review_id':'r','clinic_id':'c','rating':True,'text':'текст'},{'clinic_id':'c','rating':3,'text':'текст'}]:
   with self.assertRaises(ValueError): app.add_review(payload)
 def test_dashboard_and_pipeline_show_aggregates(self):
  import api
  with patch.dict('os.environ',{'REVIEW_CLASSIFIER':'baseline','PRODUCTION_MODE':''}):
   app.add_review({'review_id':'r','clinic_id':'c','rating':5,'text':'Врач внимательный'})
   self.assertIn('врач',api.dashboard('c').body.decode('utf-8'))
   self.assertIn('Text stream',api.pipeline('c').body.decode('utf-8'))
if __name__=="__main__": unittest.main()
