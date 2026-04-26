from __future__ import annotations

from collections.abc import Iterable, Sequence

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from repkg_gui.app_context import AppContext
from repkg_gui.domain.entities import (
    ExtractionOutcome,
    ExtractionProgress,
    ExtractionTaskInfo,
    WallpaperRecord,
)
from repkg_gui.services.extraction_service import ExtractionService
from repkg_gui.ui.dialogs.progress_dialog import ProgressDialog
from repkg_gui.workers.extraction_worker import ExtractionWorker


class ExtractionController(QObject):
    task_started = Signal(object)
    task_progress = Signal(object)
    task_finished = Signal(object)
    task_failed = Signal(str)

    def __init__(self, context: AppContext, service: ExtractionService | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.service = service or ExtractionService()
        self._thread: QThread | None = None
        self._worker: ExtractionWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._active_parent: QWidget | None = None
        self._active_item_ids: tuple[str, ...] = ()
        self._active_task_info: ExtractionTaskInfo | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    def extract_single(
        self,
        item_id: str,
        records: Iterable[WallpaperRecord] | None = None,
        parent: QWidget | None = None,
    ) -> bool:
        return self.extract_items((item_id,), records=records, show_progress=False, parent=parent)

    def extract_batch(
        self,
        item_ids: Sequence[str],
        records: Iterable[WallpaperRecord] | None = None,
        parent: QWidget | None = None,
    ) -> bool:
        return self.extract_items(item_ids, records=records, show_progress=True, parent=parent)

    def extract_items(
        self,
        item_ids: Iterable[str],
        records: Iterable[WallpaperRecord] | None = None,
        show_progress: bool | None = None,
        parent: QWidget | None = None,
    ) -> bool:
        if self.is_busy:
            self._show_message("提取进行中", "已有提取任务正在运行，请等待当前任务完成。", warning=True, parent=parent)
            return False

        normalized_item_ids = tuple(dict.fromkeys(str(item_id).strip() for item_id in item_ids if str(item_id).strip()))
        if not normalized_item_ids:
            self.context.set_status("提取未开始：请先选择要提取的壁纸。")
            self._show_message("未选择壁纸", "请先选择至少一个壁纸项目。", warning=True, parent=parent)
            return False

        available_records = tuple(records) if records is not None else self.context.state.catalog_records
        if not available_records:
            self.context.set_status("提取未开始：当前还没有可用的壁纸数据。")
            self._show_message("数据未就绪", "当前还没有可用的壁纸数据，请先完成扫描。", warning=True, parent=parent)
            return False

        self._active_parent = parent
        self._active_item_ids = normalized_item_ids
        self._active_task_info = None
        should_show_progress = len(normalized_item_ids) > 1 if show_progress is None else bool(show_progress)
        if should_show_progress:
            self._progress_dialog = ProgressDialog(parent=parent)
            self._progress_dialog.set_running(True)
            self._progress_dialog.set_progress(
                completed=0,
                total=len(normalized_item_ids),
                message="正在准备提取任务…",
                worker_count=0,
            )
            self._progress_dialog.show()

        self.context.set_task_state("extracting")
        self.context.set_status(f"正在准备提取 {len(normalized_item_ids)} 项壁纸…")

        self._thread = QThread(self)
        self._worker = ExtractionWorker(
            service=self.service,
            records=available_records,
            item_ids=normalized_item_ids,
            settings=self.context.build_session_settings(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.started.connect(self._handle_started)
        self._worker.progress.connect(self._handle_progress)
        self._worker.finished.connect(self._handle_finished)
        self._worker.failed.connect(self._handle_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()
        return True

    def _handle_started(self, task_info: ExtractionTaskInfo) -> None:
        self._active_task_info = task_info
        status_message = self._build_started_message(task_info)
        self.context.set_status(status_message)
        if self._progress_dialog is not None:
            self._progress_dialog.set_progress(
                completed=task_info.skipped_count,
                total=task_info.requested_count,
                message=status_message,
                worker_count=task_info.effective_workers,
            )
        self.task_started.emit(task_info)

    def _handle_progress(self, progress: ExtractionProgress) -> None:
        if progress.message:
            self.context.set_status(progress.message)
        if self._progress_dialog is not None:
            worker_count = self._active_task_info.effective_workers if self._active_task_info is not None else 0
            self._progress_dialog.set_progress(
                completed=progress.completed,
                total=progress.total,
                message=progress.message,
                current_item_id=progress.current_item_id,
                worker_count=worker_count,
            )
        self.task_progress.emit(progress)

    def _handle_finished(self, outcome: ExtractionOutcome) -> None:
        summary_text, status_text, has_warning = outcome.summary.to_display_messages()
        self.context.set_last_extraction_summary(summary_text)
        self.context.set_task_state("idle")
        self.context.set_status(status_text)

        if self._progress_dialog is not None:
            self._progress_dialog.set_running(False)
            self._progress_dialog.set_progress(
                completed=outcome.summary.requested_count,
                total=outcome.summary.requested_count,
                message=status_text,
                worker_count=outcome.summary.effective_workers,
            )
            self._progress_dialog.close()
            self._progress_dialog = None

        self.task_finished.emit(outcome)
        self._show_message("提取完成", summary_text, warning=has_warning)

    def _handle_failed(self, message: str) -> None:
        failure_message = message or "提取任务执行失败。"
        if self._progress_dialog is not None:
            self._progress_dialog.set_running(False)
            self._progress_dialog.close()
            self._progress_dialog = None
        self.context.set_task_state("idle")
        self.context.set_status(f"提取未开始：{failure_message}")
        self.task_failed.emit(failure_message)
        self._show_message("提取失败", failure_message, warning=True)

    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        self._active_parent = None
        self._active_item_ids = ()
        self._active_task_info = None

    def _show_message(
        self,
        title: str,
        message: str,
        warning: bool,
        parent: QWidget | None = None,
    ) -> None:
        resolved_parent = parent or self._active_parent
        if warning:
            QMessageBox.warning(resolved_parent, title, message)
        else:
            QMessageBox.information(resolved_parent, title, message)

    @staticmethod
    def _build_started_message(task_info: ExtractionTaskInfo) -> str:
        if task_info.requested_count == 0:
            return "没有收到可提取的壁纸项目。"
        if task_info.executable_count == 0:
            return f"没有可执行的提取任务（共 {task_info.requested_count} 项）。"
        if task_info.executable_count == 1:
            return f"正在提取 1 项壁纸（共 {task_info.requested_count} 项）。"
        return f"正在提取 {task_info.requested_count} 项壁纸（并发 {task_info.effective_workers} 线程）…"
