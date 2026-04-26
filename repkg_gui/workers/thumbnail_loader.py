from __future__ import annotations

import os

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage
from shiboken6 import isValid

from repkg_gui.image_utils import load_static_qimage


class _ThumbnailLoadTask(QRunnable):
    def __init__(self, loader: "ThumbnailLoader", key: str, path: str, size: QSize) -> None:
        super().__init__()
        self._loader = loader
        self._key = key
        self._path = path
        self._size = size

    def run(self) -> None:
        if not isValid(self._loader):
            return
        if not os.path.exists(self._path):
            if isValid(self._loader):
                self._loader.thumbnail_failed.emit(self._key)
            return

        image = load_static_qimage(self._path)
        if image.isNull():
            if isValid(self._loader):
                self._loader.thumbnail_failed.emit(self._key)
            return

        scaled_image = image.scaled(
            self._size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if isValid(self._loader):
            self._loader.thumbnail_loaded.emit(self._key, scaled_image)


class ThumbnailLoader(QObject):
    thumbnail_loaded = Signal(str, object)
    thumbnail_failed = Signal(str)

    def __init__(self, thread_pool: QThreadPool | None = None, parent=None) -> None:
        super().__init__(parent)
        self._thread_pool = thread_pool or QThreadPool.globalInstance()

    def request(self, key: str, path: str, size: QSize) -> None:
        if not path:
            self.thumbnail_failed.emit(key)
            return
        self._thread_pool.start(_ThumbnailLoadTask(self, key, path, size))
