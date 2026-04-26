from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

from repkg_gui.domain.entities import CatalogSnapshot, WallpaperRecord
from repkg_gui.services.runtime_compat import RuntimeCompatService


@dataclass(slots=True)
class CatalogService:
    runtime: RuntimeCompatService = field(default_factory=RuntimeCompatService)

    def scan_catalog(self, steam_path: str | None = None) -> CatalogSnapshot:
        effective_steam_path = steam_path or self.runtime.load_config().steam_path
        if not self.runtime.has_valid_steam_path(effective_steam_path):
            raise ValueError("steam_path 未找到或无效")

        csv_path = self.runtime.extract_info_to_csv(steam_path=effective_steam_path)
        return self.load_snapshot_from_csv(csv_path, steam_path=effective_steam_path)

    def load_snapshot_from_csv(self, csv_path: str, steam_path: str = "") -> CatalogSnapshot:
        dataframe = self.runtime.read_info_csv(csv_path)
        if dataframe is None:
            raise FileNotFoundError(f"无法读取 CSV 文件: {csv_path}")

        return CatalogSnapshot(
            steam_path=steam_path,
            csv_path=csv_path,
            records=self.records_from_dataframe(dataframe),
        )

    @staticmethod
    def records_from_dataframe(dataframe: pd.DataFrame) -> tuple[WallpaperRecord, ...]:
        return tuple(WallpaperRecord.from_mapping(row) for row in dataframe.to_dict(orient="records"))

    @staticmethod
    def record_from_mapping(data: Mapping[str, object]) -> WallpaperRecord:
        return WallpaperRecord.from_mapping(data)
