from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from repkg_gui.domain.entities import WallpaperRecord
from repkg_gui.domain.enums import FilterField

VISIBILITY_LABELS = {
    "public": "公开",
    "private": "私有",
    "friends": "好友可见",
    "unlisted": "未列出",
}

FILTER_FIELD_LABELS = {
    FilterField.TITLE: "标题",
    FilterField.TAGS: "标签",
    FilterField.TYPE: "类型",
}
FILTER_FIELD_BY_LABEL = {label: field for field, label in FILTER_FIELD_LABELS.items()}


@dataclass(frozen=True, slots=True)
class CatalogSelection:
    selected_ids: tuple[str, ...] = ()
    focused_id: str | None = None

    @property
    def selected_count(self) -> int:
        return len(self.selected_ids)


def normalize_selection(item_ids: Iterable[str], focused_id: str | None = None) -> CatalogSelection:
    normalized_ids: list[str] = []
    seen_ids: set[str] = set()
    for item_id in item_ids:
        normalized_item_id = str(item_id or "").strip()
        if normalized_item_id and normalized_item_id not in seen_ids:
            normalized_ids.append(normalized_item_id)
            seen_ids.add(normalized_item_id)

    normalized_focus = str(focused_id or "").strip() or None
    if normalized_focus and normalized_focus not in seen_ids:
        normalized_ids.insert(0, normalized_focus)

    return CatalogSelection(selected_ids=tuple(normalized_ids), focused_id=normalized_focus)


def format_visibility(visibility: str) -> str:
    normalized_visibility = str(visibility or "").strip().lower()
    if not normalized_visibility:
        return "未标注"
    return VISIBILITY_LABELS.get(normalized_visibility, normalized_visibility)


def build_loaded_status(total_count: int, refreshed: bool = False) -> str:
    prefix = "刷新完成，已加载" if refreshed else "已加载"
    return f"{prefix} {total_count} 项壁纸数据。"


def build_filter_status(field: FilterField, keyword: str, visible_count: int, total_count: int) -> str:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        return build_loaded_status(total_count)

    field_label = FILTER_FIELD_LABELS[field]
    return f"已按{field_label}筛选“{normalized_keyword}”，匹配 {visible_count}/{total_count} 项。"


def build_selection_status(selected_count: int, visible_count: int) -> str:
    if selected_count:
        return f"已选择 {selected_count} 项，当前列表共 {visible_count} 项。"
    return f"当前未选择项目，当前列表共 {visible_count} 项。"


def metadata_lines(record: WallpaperRecord) -> tuple[str, ...]:
    preview_display = os.path.basename(record.preview_path) if record.preview_path else "未找到"
    tags_display = record.tags_text or "未标注"
    type_display = record.type or "未标注"
    project_file = record.file or "未标注"
    return (
        f"ID：{record.id or '未标注'}",
        f"标签：{tags_display}",
        f"类型：{type_display}",
        f"可见性：{format_visibility(record.visibility)}",
        f"项目文件：{project_file}",
        f"预览文件：{preview_display}",
    )


def distinct_field_values(records: Iterable[WallpaperRecord], field: FilterField) -> tuple[str, ...]:
    if field is FilterField.TAGS:
        values = {tag for record in records for tag in record.tags if tag}
    elif field is FilterField.TYPE:
        values = {record.type for record in records if record.type}
    else:
        values = set()
    return tuple(sorted(values, key=str.casefold))
