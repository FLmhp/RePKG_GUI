__all__ = [
    "CatalogFilterProxyModel",
    "CatalogSelection",
    "CatalogTableModel",
    "ThumbnailCache",
]


def __getattr__(name: str):
    if name == "CatalogFilterProxyModel":
        from .catalog_filter_proxy import CatalogFilterProxyModel

        return CatalogFilterProxyModel
    if name == "CatalogSelection":
        from .selection_model import CatalogSelection

        return CatalogSelection
    if name == "CatalogTableModel":
        from .catalog_table_model import CatalogTableModel

        return CatalogTableModel
    if name == "ThumbnailCache":
        from .thumbnail_cache import ThumbnailCache

        return ThumbnailCache
    raise AttributeError(name)
