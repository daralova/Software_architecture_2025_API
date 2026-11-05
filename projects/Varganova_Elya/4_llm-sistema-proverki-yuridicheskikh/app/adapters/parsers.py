"""Адаптеры извлечения текста из документов (паттерн Adapter).

Каждый парсер оборачивает внешнюю библиотеку за единым интерфейсом
BaseDocumentParser. Тяжёлые импорты (pymupdf, python-docx) — ленивые.
"""
from __future__ import annotations

import abc
import io
from typing import ClassVar


class BaseDocumentParser(abc.ABC):
    extensions: ClassVar[tuple[str, ...]] = ()

    @abc.abstractmethod
    def parse(self, data: bytes) -> str: ...


class TextParser(BaseDocumentParser):
    extensions = ("txt", "md", "")

    def parse(self, data: bytes) -> str:
        text = data.decode("utf-8", errors="replace")
        # если декодирование пошло плохо, пробуем cp1251
        if text.count("\ufffd") > max(len(text) // 20, 5):
            try:
                text = data.decode("cp1251")
            except UnicodeDecodeError:
                pass
        return text


class PdfParser(BaseDocumentParser):
    extensions = ("pdf",)

    def parse(self, data: bytes) -> str:
        try:
            import fitz  # pymupdf
        except ImportError as exc:
            raise RuntimeError(
                "Для разбора PDF установите pymupdf (см. requirements.txt)"
            ) from exc
        document = fitz.open(stream=data, filetype="pdf")
        pages = [page.get_text() for page in document]
        document.close()
        return "\n".join(pages)


class DocxParser(BaseDocumentParser):
    extensions = ("docx",)

    def parse(self, data: bytes) -> str:
        try:
            import docx
        except ImportError as exc:
            raise RuntimeError(
                "Для разбора DOCX установите python-docx (см. requirements.txt)"
            ) from exc
        document = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                paragraphs.append("\t".join(cell.text for cell in row.cells))
        return "\n".join(paragraphs)


class ParserRegistry:
    """Фасад над парсерами: разбор файла по расширению с fallback на текст."""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseDocumentParser] = {}
        for parser in (TextParser(), PdfParser(), DocxParser()):
            for ext in parser.extensions:
                self._parsers[ext] = parser

    def parse(self, filename: str, data: bytes) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        parser = self._parsers.get(ext, self._parsers["txt"])
        return parser.parse(data)
