from __future__ import annotations

from collections.abc import Iterable

import app_services
from PySide6.QtCore import QObject, Signal, Slot

from repkg_gui.domain.entities import (
    ExtractionItemResult,
    ExtractionOutcome,
    ExtractionPlan,
    ExtractionProgress,
    ExtractionTaskInfo,
    SessionSettings,
    WallpaperRecord,
)
from repkg_gui.services.extraction_service import ExtractionService, ExtractionValidationError


class ExtractionWorker(QObject):
    started = Signal(object)
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: ExtractionService,
        records: Iterable[WallpaperRecord],
        item_ids: Iterable[str],
        settings: SessionSettings,
    ) -> None:
        super().__init__()
        self._service = service
        self._records = tuple(records)
        self._item_ids = tuple(item_ids)
        self._settings = settings

    @Slot()
    def run(self) -> None:
        try:
            self._service.validate_environment(self._settings)
            plan = self._service.prepare_requests(self._records, self._item_ids, self._settings.steam_path)
            task_info = ExtractionTaskInfo(
                requested_count=plan.total_count,
                executable_count=len(plan.requests),
                skipped_count=len(plan.skipped),
                effective_workers=self._service.resolve_effective_workers(plan, self._settings),
            )
            self.started.emit(task_info)

            processed = len(plan.skipped)
            if plan.total_count:
                self.progress.emit(
                    ExtractionProgress(
                        completed=processed,
                        total=plan.total_count,
                        message=self._build_progress_message(processed, plan.total_count, plan),
                    )
                )

            def on_result(result: ExtractionItemResult) -> None:
                nonlocal processed
                processed += 1
                self.progress.emit(
                    ExtractionProgress(
                        completed=processed,
                        total=plan.total_count,
                        current_item_id=result.item_id,
                        message=self._build_result_message(result, processed, plan.total_count),
                    )
                )

            summary = self._service.execute_requests(plan, self._settings, on_result=on_result)
            self.finished.emit(ExtractionOutcome(plan=plan, summary=summary))
        except ExtractionValidationError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            app_services.log_error(f"提取任务执行时发生未处理异常: {exc}")
            self.failed.emit(str(exc))

    @staticmethod
    def _build_progress_message(processed: int, total: int, plan: ExtractionPlan) -> str:
        if not plan.requests:
            return f"没有可执行的提取任务（已处理 {processed}/{total} 项）。"
        if plan.skipped:
            return f"已准备提取任务（已处理 {processed}/{total} 项，预先跳过 {len(plan.skipped)} 项）。"
        return f"已准备提取任务（0/{total}）。"

    @staticmethod
    def _build_result_message(result: ExtractionItemResult, processed: int, total: int) -> str:
        outcome = "成功" if result.success else "失败"
        return f"提取{outcome}：{result.item_id}（{processed}/{total}）"
