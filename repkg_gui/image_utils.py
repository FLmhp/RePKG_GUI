from __future__ import annotations

from PIL import Image, ImageSequence, UnidentifiedImageError
from PySide6.QtGui import QImage, QPixmap


def _select_representative_frame(pil_image: Image.Image) -> Image.Image:
    if not getattr(pil_image, "is_animated", False):
        return pil_image.convert("RGBA")

    best_frame: Image.Image | None = None
    best_score = -1
    for index, frame in enumerate(ImageSequence.Iterator(pil_image)):
        if index >= 10:
            break
        converted_frame = frame.convert("RGBA")
        bbox = converted_frame.getbbox()
        if bbox is None:
            continue
        area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1)
        brightness = converted_frame.convert("L").getextrema()[1]
        score = area * max(brightness, 1)
        if score > best_score:
            best_frame = converted_frame
            best_score = score

    if best_frame is not None:
        return best_frame
    pil_image.seek(0)
    return pil_image.convert("RGBA")


def load_static_qimage(path: str) -> QImage:
    if not path.lower().endswith(".gif"):
        image = QImage(path)
        if not image.isNull():
            return image

    try:
        with Image.open(path) as pil_image:
            frame = _select_representative_frame(pil_image)
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return QImage()

    width, height = frame.size
    qimage = QImage(frame.tobytes("raw", "RGBA"), width, height, QImage.Format.Format_RGBA8888)
    return qimage.copy()


def load_static_pixmap(path: str) -> QPixmap:
    image = load_static_qimage(path)
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image)
