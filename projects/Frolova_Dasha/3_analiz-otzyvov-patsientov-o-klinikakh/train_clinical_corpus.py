"""Train and assess aspect and sentiment classifiers on RuSPUTMed.

Only the original, non-augmented split is used. Thresholds are selected on
validation data; the independent test set is evaluated once afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_recall_fscore_support
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MultiLabelBinarizer

ROOT = Path(__file__).resolve().parent
REVISION = '4e0223b289a187e9538c7056609f1cb5061119bb'
BASE = f'https://huggingface.co/datasets/helling100/sentiment-pragmatic-med-ru/resolve/{REVISION}/SA/original/'
ASPECT_CODES = {
    'врач': {'DR', 'CH'},
    'ожидание': {'W'},
    'сервис': {'S', 'SER', 'COM', 'TR'},
    'стоимость': {'M'},
    'результат лечения': {'CUR', 'Q'},
}


def labels(value):
    codes = {part.strip().upper() for part in re.split(r'[,;]', str(value))}
    return [name for name, values in ASPECT_CODES.items() if codes & values]


def sentiment(value):
    code = str(value).strip().upper()
    if code.startswith('POS'): return 'positive'
    if code.startswith('NEG'): return 'negative'
    if code == 'NEUT': return 'neutral'
    return None


def load_split(folder, name):
    path = folder / f'{name}.csv'
    if not path.exists():
        request = urllib.request.Request(BASE + path.name, headers={'User-Agent': 'CourseworkEvaluation/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response:
            path.write_bytes(response.read())
    data = pd.read_csv(path, keep_default_na=False)
    required = {'Sentence', 'Aspect', 'Sentiment'}
    if not required.issubset(data.columns): raise ValueError(f'Missing columns in {path}')
    data = data[data['Sentence'].astype(str).str.strip().ne('')].copy()
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=ROOT/'data'/'rusputmed')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'artifacts')
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    splits = {}; hashes = {}
    for split in ('train', 'val', 'test'):
        splits[split], hashes[split] = load_split(args.data_dir, split)

    # Remove exact duplicate sentences across splits, including conflicting labels.
    def norm(frame): return frame['Sentence'].astype(str).str.strip().str.casefold()
    test_text = set(norm(splits['test']))
    val_text = set(norm(splits['val']))
    removed_train = int(norm(splits['train']).isin(test_text | val_text).sum())
    removed_val = int(norm(splits['val']).isin(test_text).sum())
    splits['train'] = splits['train'][~norm(splits['train']).isin(test_text | val_text)]
    splits['val'] = splits['val'][~norm(splits['val']).isin(test_text)]
    mlb = MultiLabelBinarizer(classes=list(ASPECT_CODES))
    y_train = mlb.fit_transform(splits['train']['Aspect'].map(labels))
    y_val = mlb.transform(splits['val']['Aspect'].map(labels))
    y_test = mlb.transform(splits['test']['Aspect'].map(labels))
    aspect = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=60000, sublinear_tf=True),
                           OneVsRestClassifier(LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)))
    aspect.fit(splits['train']['Sentence'].tolist(), y_train)
    val_prob = aspect.predict_proba(splits['val']['Sentence'].tolist())
    thresholds = []
    for idx in range(len(mlb.classes_)):
        choices = np.linspace(.1, .9, 17)
        scores = [f1_score(y_val[:, idx], val_prob[:, idx] >= t, zero_division=0) for t in choices]
        thresholds.append(float(choices[int(np.argmax(scores))]))
    test_prob = aspect.predict_proba(splits['test']['Sentence'].tolist())
    predicted = (test_prob >= np.array(thresholds)).astype(int)
    precision, recall, f1, support = precision_recall_fscore_support(y_test, predicted, average=None, zero_division=0)
    aspect_metrics = {'macro_f1': round(float(f1_score(y_test, predicted, average='macro', zero_division=0)), 4),
                      'micro_f1': round(float(f1_score(y_test, predicted, average='micro', zero_division=0)), 4),
                      'per_class': {label: {'precision': round(float(p),4), 'recall': round(float(r),4),
                                           'f1': round(float(f),4), 'support': int(n), 'threshold': round(t,4)}
                                    for label,p,r,f,n,t in zip(mlb.classes_, precision, recall, f1, support, thresholds)}}
    sentiment_train = splits['train'].copy()
    sentiment_train['target'] = sentiment_train['Sentiment'].map(sentiment)
    sentiment_train = sentiment_train.dropna(subset=['target'])
    sentiment_test = splits['test'].copy()
    sentiment_test['target'] = sentiment_test['Sentiment'].map(sentiment)
    sentiment_test = sentiment_test.dropna(subset=['target'])
    sent = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=60000, sublinear_tf=True),
                         LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))
    sent.fit(sentiment_train['Sentence'].tolist(), sentiment_train['target'].tolist())
    sent_pred = sent.predict(sentiment_test['Sentence'].tolist())
    sent_metrics = classification_report(sentiment_test['target'], sent_pred, labels=['negative','neutral','positive'],
                                         output_dict=True, zero_division=0)
    # Apply the shipped lexicon baseline to the same untouched test sentences.
    from app import classify
    from sklearn.metrics import accuracy_score
    baseline_rows = [classify(str(text)) for text in splits['test']['Sentence']]
    baseline_aspects = mlb.transform([[item['aspect'] for item in row if item['aspect'] in ASPECT_CODES] for row in baseline_rows])
    valid_sentiment = splits['test']['Sentiment'].map(sentiment).notna().tolist()
    baseline_sentiment = [row[0]['sentiment'] for row, valid in zip(baseline_rows, valid_sentiment) if valid]
    baseline = {'method':'local lexicon; single sentence polarity',
                'aspect_macro_f1':round(float(f1_score(y_test,baseline_aspects,average='macro',zero_division=0)),4),
                'aspect_micro_f1':round(float(f1_score(y_test,baseline_aspects,average='micro',zero_division=0)),4),
                'sentiment_macro_f1':round(float(f1_score(sentiment_test['target'],baseline_sentiment,labels=['negative','neutral','positive'],average='macro',zero_division=0)),4),
                'sentiment_accuracy':round(float(accuracy_score(sentiment_test['target'],baseline_sentiment)),4),
                'samples':len(splits['test'])}
    joblib.dump({'model': aspect, 'classes': list(mlb.classes_), 'thresholds': thresholds,
                 'sklearn_version': sklearn.__version__}, args.output_dir/'clinical_aspect_model.joblib', compress=3)
    joblib.dump({'model': sent, 'sklearn_version': sklearn.__version__}, args.output_dir/'clinical_sentiment_model.joblib', compress=3)
    result = {'dataset': 'helling100/sentiment-pragmatic-med-ru', 'revision': REVISION,
              'license': 'CC-BY-SA-4.0', 'config': 'sa_original', 'source_sha256': hashes,
              'split_sizes_after_dedup': {k: len(v) for k,v in splits.items()},
              'removed_cross_split_train': removed_train, 'removed_cross_split_validation': removed_val,
              'aspect_mapping': {k: sorted(v) for k,v in ASPECT_CODES.items()},
              'aspect': aspect_metrics,
              'sentiment': {'test_samples': len(sentiment_test), 'accuracy': round(sent_metrics['accuracy'],4),
                            'macro_f1': round(sent_metrics['macro avg']['f1-score'],4),
                            'per_class': {k: sent_metrics[k] for k in ['negative','neutral','positive']}},
              'sklearn_version': sklearn.__version__, 'baseline': baseline,
              'limitations': 'Sentence-level labels; mapped categories combine related aspects; no independent per-aspect sentiment labels.'}
    (args.output_dir/'clinical_corpus_metrics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
