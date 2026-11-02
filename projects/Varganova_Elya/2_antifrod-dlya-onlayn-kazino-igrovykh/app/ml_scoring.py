import xgboost as xgb
import numpy as np
from app.config import Config

model = xgb.Booster()
# Р’ СЂРµР°Р»СЊРЅРѕРј РїСЂРѕРµРєС‚Рµ: model.load_model(Config.XGBOOST_MODEL_PATH)

def predict_fraud_score(features: dict) -> float:
    feature_names = sorted(features.keys())
    x = np.array([[features[f] for f in feature_names]])
    dmatrix = xgb.DMatrix(x, feature_names=feature_names)
    score = model.predict(dmatrix)[0]
    return float(score)
