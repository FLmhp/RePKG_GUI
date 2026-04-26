from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap


@dataclass(slots=True)
class ThumbnailCache:
    _pixmaps: dict[str, QPixmap] = field(default_factory=dict)
    _pending: set[str] = field(default_factory=set)
    _placeholders: dict[str, QPixmap] = field(default_factory=dict)

    @staticmethod
    def build_key(path: str, size: QSize) -> str:
        return f"{path}|{size.width()}x{size.height()}"

    def get(self, key: str) -> QPixmap | None:
        return self._pixmaps.get(key)

    def store(self, key: str, pixmap: QPixmap) -> None:
        self._pixmaps[key] = pixmap
        self._pending.discard(key)

    def mark_pending(self, key: str) -> bool:
        if key in self._pending:
            return False
        self._pending.add(key)
        return True

    def clear_pending(self, key: str) -> None:
        self._pending.discard(key)

    def placeholder(self, size: QSize) -> QPixmap:
        placeholder_key = f"{size.width()}x{size.height()}"
        placeholder = self._placeholders.get(placeholder_key)
        if placeholder is not None:
            return placeholder

        safe_width = max(size.width(), 1)
        safe_height = max(size.height(), 1)
        placeholder = QPixmap(safe_width, safe_height)
        placeholder.fill(QColor("#202020"))

        painter = QPainter(placeholder)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#4a4a4a")))
        painter.drawRect(0, 0, safe_width - 1, safe_height - 1)
        painter.setPen(QColor("#b8b8b8"))
        painter.drawText(
            placeholder.rect(),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            "暂无\n预览",
        )
        painter.end()

        self._placeholders[placeholder_key] = placeholder
        return placeholder
