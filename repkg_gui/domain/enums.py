from enum import StrEnum


class ViewMode(StrEnum):
    LIST = "list"
    THUMBNAIL = "thumbnail"


class FilterField(StrEnum):
    TITLE = "title"
    TAGS = "tags"
    TYPE = "type"


class TaskState(StrEnum):
    IDLE = "idle"
    SCANNING = "scanning"
    EXTRACTING = "extracting"


class OutputMode(StrEnum):
    LOCAL = "local"
    SHARED = "shared"
    SEPARATE = "separate"
