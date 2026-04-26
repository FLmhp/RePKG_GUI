__all__ = ["ThumbnailLoader"]


def __getattr__(name: str):
    if name == "ThumbnailLoader":
        from .thumbnail_loader import ThumbnailLoader

        return ThumbnailLoader
    raise AttributeError(name)
