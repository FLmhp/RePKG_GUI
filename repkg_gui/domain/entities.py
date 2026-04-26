from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterable, Mapping

from repkg_gui.domain.enums import FilterField, OutputMode, TaskState


def _normalize_tags(tags: object) -> tuple[str, ...]:
    if tags is None:
        return ()

    if isinstance(tags, str):
        normalized = tags.strip()
        return (normalized,) if normalized else ()

    if not isinstance(tags, Iterable):
        return ()

    normalized_tags = []
    for tag in tags:
        text = str(tag).strip()
        if text:
            normalized_tags.append(text)
    return tuple(normalized_tags)


@dataclass(frozen=True, slots=True)
class WallpaperRecord:
    id: str
    title: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    type: str = ""
    visibility: str = ""
    file: str = ""
    preview_path: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "WallpaperRecord":
        return cls(
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            tags=_normalize_tags(data.get("tags", ())),
            type=str(data.get("type", "")).strip(),
            visibility=str(data.get("visibility", "")).strip(),
            file=str(data.get("file", "")).strip(),
            preview_path=str(data.get("preview", data.get("preview_path", ""))).strip(),
        )

    @property
    def display_title(self) -> str:
        return self.title or self.id

    @property
    def tags_text(self) -> str:
        return ", ".join(self.tags)

    @property
    def has_preview(self) -> bool:
        return bool(self.preview_path)


@dataclass(frozen=True, slots=True)
class FilterState:
    field: FilterField = FilterField.TITLE
    value: str = ""

    @property
    def is_active(self) -> bool:
        return bool(self.value.strip())


@dataclass(slots=True)
class SessionSettings:
    steam_path: str = ""
    output_path: str = "./output"
    batch_extract_workers: int = 0
    output_mode: OutputMode = OutputMode.SEPARATE
    not_convert_tex_to_image: bool = False
    use_wallpaper_name_as_subdir: bool = True
    copy_project_json_and_preview: bool = False
    overwrite_files: bool = True


@dataclass(frozen=True, slots=True)
class TaskSummary:
    state: TaskState = TaskState.IDLE
    message: str = ""
    completed: int = 0
    total: int = 0


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    steam_path: str
    csv_path: str
    records: tuple[WallpaperRecord, ...] = field(default_factory=tuple)
    scanned_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_count(self) -> int:
        return len(self.records)

    def index_by_id(self) -> dict[str, WallpaperRecord]:
        return {record.id: record for record in self.records if record.id}


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    item_id: str
    title: str
    scene_pkg_path: str
    item_directory: str


@dataclass(frozen=True, slots=True)
class SkippedItem:
    item_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ExtractionPlan:
    requests: tuple[ExtractionRequest, ...] = field(default_factory=tuple)
    skipped: tuple[SkippedItem, ...] = field(default_factory=tuple)

    @property
    def total_count(self) -> int:
        return len(self.requests) + len(self.skipped)


@dataclass(frozen=True, slots=True)
class ExtractionItemResult:
    item_id: str
    title: str
    success: bool
    command: tuple[str, ...] = field(default_factory=tuple)
    error: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


@dataclass(frozen=True, slots=True)
class ExtractionSummary:
    requested_count: int
    succeeded: tuple[ExtractionItemResult, ...] = field(default_factory=tuple)
    failed: tuple[ExtractionItemResult, ...] = field(default_factory=tuple)
    skipped: tuple[SkippedItem, ...] = field(default_factory=tuple)
    effective_workers: int = 0

    @property
    def success_ids(self) -> tuple[str, ...]:
        return tuple(result.item_id for result in self.succeeded)

    @property
    def failed_ids(self) -> tuple[str, ...]:
        return tuple(result.item_id for result in self.failed)

    @property
    def has_warnings(self) -> bool:
        return bool(self.failed or self.skipped)

    @property
    def missing_scene_pkg_ids(self) -> tuple[str, ...]:
        return tuple(item.item_id for item in self.skipped if item.reason == "缺少 scene.pkg")

    @property
    def preparation_failures(self) -> tuple[SkippedItem, ...]:
        return tuple(item for item in self.skipped if item.reason != "缺少 scene.pkg")

    @property
    def failure_details(self) -> tuple[tuple[str, str], ...]:
        skipped_failures = tuple((item.item_id, item.reason) for item in self.preparation_failures)
        execution_failures = tuple((item.item_id, item.error or "未知错误") for item in self.failed)
        return skipped_failures + execution_failures

    def to_display_messages(self) -> tuple[str, str, bool]:
        success_count = len(self.succeeded)
        summary_lines = [f"成功提取 {success_count} 项"]

        if self.missing_scene_pkg_ids:
            summary_lines.append(f"缺少 scene.pkg: {', '.join(self.missing_scene_pkg_ids)}")
        if self.failure_details:
            failure_summary = ", ".join(f"{item_id}({reason})" for item_id, reason in self.failure_details)
            summary_lines.append(f"执行失败: {failure_summary}")

        status_parts = [f"提取完成：成功 {success_count} 项"]
        if self.missing_scene_pkg_ids:
            status_parts.append(f"缺少资源 {len(self.missing_scene_pkg_ids)} 项")
        if self.failure_details:
            status_parts.append(f"失败 {len(self.failure_details)} 项")

        return "\n".join(summary_lines), "，".join(status_parts), self.has_warnings


@dataclass(frozen=True, slots=True)
class ExtractionTaskInfo:
    requested_count: int
    executable_count: int
    skipped_count: int
    effective_workers: int


@dataclass(frozen=True, slots=True)
class ExtractionProgress:
    completed: int
    total: int
    current_item_id: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class ExtractionOutcome:
    plan: ExtractionPlan
    summary: ExtractionSummary
