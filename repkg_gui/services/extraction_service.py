from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Iterable

import app_services
from repkg_gui.domain.entities import (
    ExtractionItemResult,
    ExtractionPlan,
    ExtractionRequest,
    ExtractionSummary,
    SessionSettings,
    SkippedItem,
    WallpaperRecord,
)
from repkg_gui.domain.enums import OutputMode
from repkg_gui.services.runtime_compat import RuntimeCompatService


class ExtractionValidationError(ValueError):
    pass


@dataclass(slots=True)
class ExtractionService:
    runtime: RuntimeCompatService = field(default_factory=RuntimeCompatService)

    def validate_environment(self, settings: SessionSettings) -> None:
        errors = []
        if not self.runtime.has_valid_steam_path(settings.steam_path):
            errors.append("steam_path 未找到或无效")
        if settings.output_mode != OutputMode.LOCAL and not settings.output_path.strip():
            errors.append("输出路径为空")
        if not os.path.exists(self.runtime.repkg_executable):
            errors.append(f"未找到提取工具：{self.runtime.repkg_executable}")
        if errors:
            raise ExtractionValidationError("；".join(errors))

    def prepare_requests(
        self,
        records: Iterable[WallpaperRecord],
        item_ids: Iterable[str],
        steam_path: str,
    ) -> ExtractionPlan:
        indexed_records = {app_services.normalize_wallpaper_id(record.id): record for record in records}
        requests: list[ExtractionRequest] = []
        skipped: list[SkippedItem] = []

        for item_id in item_ids:
            normalized_item_id = app_services.normalize_wallpaper_id(item_id)
            record = indexed_records.get(normalized_item_id)
            if record is None:
                skipped.append(SkippedItem(item_id=normalized_item_id, reason="未找到对应的壁纸信息"))
                app_services.log_error(f"未找到 ID 为 {normalized_item_id} 的项目")
                continue

            scene_pkg_path = self.runtime.get_scene_pkg_path(steam_path, normalized_item_id)
            if not os.path.exists(scene_pkg_path):
                skipped.append(SkippedItem(item_id=normalized_item_id, reason="缺少 scene.pkg"))
                continue

            requests.append(
                ExtractionRequest(
                    item_id=normalized_item_id,
                    title=record.display_title,
                    scene_pkg_path=scene_pkg_path,
                    item_directory=self.runtime.get_item_directory(steam_path, normalized_item_id),
                )
            )

        return ExtractionPlan(requests=tuple(requests), skipped=tuple(skipped))

    def execute_requests(
        self,
        plan: ExtractionPlan,
        settings: SessionSettings,
        on_result: Callable[[ExtractionItemResult], None] | None = None,
    ) -> ExtractionSummary:
        self.validate_environment(settings)
        if not plan.requests:
            return ExtractionSummary(
                requested_count=plan.total_count,
                skipped=plan.skipped,
                effective_workers=0,
            )

        effective_workers = self.resolve_effective_workers(plan, settings)

        ordered_results: list[ExtractionItemResult | None] = [None] * len(plan.requests)
        if len(plan.requests) == 1:
            result = self._execute_request(plan.requests[0], settings)
            ordered_results[0] = result
            if on_result is not None:
                on_result(result)
        else:
            with ThreadPoolExecutor(max_workers=effective_workers) as executor:
                futures = {
                    executor.submit(self._execute_request, request, settings): index
                    for index, request in enumerate(plan.requests)
                }
                for future in as_completed(futures):
                    result = future.result()
                    ordered_results[futures[future]] = result
                    if on_result is not None:
                        on_result(result)

        results = tuple(result for result in ordered_results if result is not None)
        return ExtractionSummary(
            requested_count=plan.total_count,
            succeeded=tuple(result for result in results if result.success),
            failed=tuple(result for result in results if not result.success),
            skipped=plan.skipped,
            effective_workers=effective_workers,
        )

    def extract(
        self,
        records: Iterable[WallpaperRecord],
        item_ids: Iterable[str],
        settings: SessionSettings,
        on_result: Callable[[ExtractionItemResult], None] | None = None,
    ) -> tuple[ExtractionPlan, ExtractionSummary]:
        plan = self.prepare_requests(records, item_ids, settings.steam_path)
        return plan, self.execute_requests(plan, settings, on_result=on_result)

    def resolve_effective_workers(self, plan: ExtractionPlan, settings: SessionSettings) -> int:
        if not plan.requests:
            return 0

        return min(
            self.runtime.resolve_batch_extract_workers(settings.batch_extract_workers),
            max(len(plan.requests), 1),
        )

    def _execute_request(self, request: ExtractionRequest, settings: SessionSettings) -> ExtractionItemResult:
        try:
            command = tuple(self.runtime.build_extract_command(settings, request.item_id, request.title))
            result = self.runtime.run_extract_command(list(command))
        except ValueError as exc:
            app_services.log_error(str(exc))
            return ExtractionItemResult(
                item_id=request.item_id,
                title=request.title,
                success=False,
                command=(),
                error=str(exc),
                returncode=-1,
            )
        except OSError as exc:
            app_services.log_error(f"执行命令时发生错误: {exc}")
            return ExtractionItemResult(
                item_id=request.item_id,
                title=request.title,
                success=False,
                command=(),
                error=str(exc),
                returncode=-1,
            )

        if result.returncode == 0:
            app_services.log_success(f"成功提取壁纸ID: {request.item_id} 并执行命令")
            return ExtractionItemResult(
                item_id=request.item_id,
                title=request.title,
                success=True,
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )

        error_message = result.stderr.strip() or result.stdout.strip() or "未知错误"
        app_services.log_error(f"提取壁纸ID {request.item_id} 失败: {error_message}")
        return ExtractionItemResult(
            item_id=request.item_id,
            title=request.title,
            success=False,
            command=command,
            error=error_message,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )
