__all__ = ["LibraryController"]


def __getattr__(name: str):
    if name == "LibraryController":
        from .library_controller import LibraryController

        return LibraryController
    raise AttributeError(name)
