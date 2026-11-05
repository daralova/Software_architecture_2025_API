"""Inference service: FastAPI-обёртка над обученной SB3-моделью.

Эндпоинты:
    GET  /health  - жив ли сервис и загружена ли модель
    POST /predict - action для наблюдения (список каналов H x W)
"""
from __future__ import annotations

import argparse
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.utils.config import load_config

app = FastAPI(title="Dungeon RL Inference", version="1.0.0")
_model = None
_model_path = None
_obs_shape = None


class ObservationRequest(BaseModel):
    observation: List[List[List[float]]] = Field(..., description="[channels][height][width]")


class PredictionResponse(BaseModel):
    action: int
    action_name: str
    model_path: str


def load_model(path: str) -> None:
    global _model, _model_path, _obs_shape
    from stable_baselines3 import PPO
    _model = PPO.load(path, device="cpu")
    _model_path = path
    _obs_shape = _model.observation_space.shape
    print(f"[inference] модель загружена: {path}, obs shape {_obs_shape}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": _model is not None, "model_path": _model_path}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: ObservationRequest) -> PredictionResponse:
    if _model is None:
        raise HTTPException(status_code=503, detail="model is not loaded")
    obs = np.asarray(request.observation, dtype=np.float32)
    if obs.shape != _obs_shape:
        raise HTTPException(status_code=400, detail=f"expected shape {_obs_shape}, got {obs.shape}")
    action, _ = _model.predict(obs, deterministic=True)
    from src.game.dungeon import DungeonSimulator
    return PredictionResponse(
        action=int(action),
        action_name=DungeonSimulator.ACTION_NAMES[int(action)],
        model_path=_model_path,
    )


def main() -> None:
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    inf_cfg = cfg["inference"]
    model_path = args.model or inf_cfg.get("model_path", "models/ppo_dungeon.zip")
    load_model(model_path)
    uvicorn.run(app, host=inf_cfg.get("host", "0.0.0.0"), port=int(inf_cfg.get("port", 8000)))


if __name__ == "__main__":
    main()
