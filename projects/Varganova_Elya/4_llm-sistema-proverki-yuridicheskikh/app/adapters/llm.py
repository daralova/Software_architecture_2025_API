"""Адаптеры LLM для генерации резюме (паттерн Adapter).

RuleBasedLLM — детерминированная заглушка: возвращает подготовленный пайплайном
черновик сводки (маркер DRAFT). Используется по умолчанию, чтобы система
работала без сети и тяжёлых зависимостей.
HuggingFaceLLM — реальная модель, включается через LLM_BACKEND=hf.
"""
from __future__ import annotations

import abc

from app.core.config import Settings

_DRAFT_MARKER = "DRAFT:"


class BaseLLM(abc.ABC):
    @abc.abstractmethod
    def summarize(self, prompt: str) -> str: ...


class RuleBasedLLM(BaseLLM):
    def summarize(self, prompt: str) -> str:
        if _DRAFT_MARKER in prompt:
            draft = prompt.split(_DRAFT_MARKER)[-1]
            return draft.strip()
        return " ".join(prompt.split())[:600]


class HuggingFaceLLM(BaseLLM):
    def __init__(self, model_name: str, max_length: int = 512) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._pipeline = None

    def _ensure_pipeline(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "Для LLM_BACKEND=hf установите transformers и torch"
                ) from exc
            self._pipeline = pipeline(
                "summarization", model=self.model_name, max_length=self.max_length
            )
        return self._pipeline

    def summarize(self, prompt: str) -> str:
        pipe = self._ensure_pipeline()
        text = prompt.replace(_DRAFT_MARKER, "").strip()[:2000]
        result = pipe(text)
        return result[0].get("summary_text", "").strip()


def make_llm(settings: Settings) -> BaseLLM:
    if settings.llm_backend == "hf":
        return HuggingFaceLLM(settings.llm_model)
    return RuleBasedLLM()
