"""Strategy + Factory: выбор сегментатора по имени из конфига или CLI."""
from app.models.base import Segmenter
from app.core.config import settings

_registry: dict[str, type] = {}

def register(name: str):
    def deco(cls):
        _registry[name] = cls
        return cls
    return deco

def create_segmenter(name: str | None = None, **kwargs) -> Segmenter:
    name = (name or settings.model_name).lower()
    if name not in _registry:
        raise KeyError(f"Неизвестный сегментатор: {name}. Доступно: {list(_registry)}")
    return _registry[name](**kwargs)

def available() -> list[str]:
    return list(_registry)
