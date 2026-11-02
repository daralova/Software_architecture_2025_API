"""Send a JSONL stream of anonymized reviews to the review API."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

def send_stream(path, api_url):
    sent=[]
    with Path(path).open(encoding='utf-8') as source:
        for line_no,line in enumerate(source,1):
            if not line.strip(): continue
            review=json.loads(line)
            request=Request(api_url.rstrip('/')+'/api/v1/reviews',data=json.dumps(review,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
            with urlopen(request,timeout=120) as response:
                sent.append(json.load(response))
    return sent

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('data/demo_reviews.jsonl'))
    parser.add_argument('--api-url',default='http://127.0.0.1:8013')
    args=parser.parse_args()
    result=send_stream(args.input,args.api_url)
    print(json.dumps({'sent':len(result),'review_ids':[r['review_id'] for r in result]},ensure_ascii=False,indent=2))
