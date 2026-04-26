from __future__ import annotations

import ctypes
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from scandir import scandir

import app_services

DEFAULT_COMMON_STEAM_PATHS = (
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
    r"D:\Program Files (x86)\Steam",
    r"D:\Program Files\Steam",
    r"E:\Program Files (x86)\Steam",
    r"E:\Program Files\Steam",
)


@dataclass(slots=True)
class SteamLocatorService:
    common_paths: tuple[str, ...] = field(default_factory=lambda: DEFAULT_COMMON_STEAM_PATHS)

    def is_valid_steam_path(self, path: str | None) -> bool:
        return app_services.is_existing_steam_path(path)

    def find_in_common_locations(self) -> str | None:
        for path in self.common_paths:
            candidate = os.path.join(path, "steam.exe")
            if self.is_valid_steam_path(candidate):
                return candidate
        return None

    def get_available_drives(self) -> list[str]:
        try:
            drive_bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        except (AttributeError, OSError) as exc:
            app_services.log_error(f"Error getting drives: {exc}")
            return []

        drives = []
        for index in range(26):
            if drive_bitmask & (1 << index):
                drives.append(f"{chr(ord('A') + index)}:\\")
        return drives

    def find_on_drive(self, drive: str) -> str | None:
        if not os.path.exists(drive):
            return None

        root_candidate = os.path.join(drive, "steam.exe")
        if self.is_valid_steam_path(root_candidate):
            return root_candidate

        try:
            for entry in scandir(drive):
                if not entry.is_dir():
                    continue

                candidate = os.path.join(entry.path, "steam.exe")
                if self.is_valid_steam_path(candidate):
                    return candidate
        except FileNotFoundError:
            app_services.log_error(f"FileNotFoundError scanning drive {drive}")
        except OSError as exc:
            app_services.log_error(f"Error scanning drive {drive}: {exc}")
        return None

    def find_steam_path(self, include_all_drives: bool = True, max_workers: int | None = None) -> str | None:
        common_path = self.find_in_common_locations()
        if common_path or not include_all_drives:
            return common_path

        drives = self.get_available_drives()
        if not drives:
            return None

        worker_count = max_workers or min(len(drives), 8) or 1
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(self.find_on_drive, drive): drive for drive in drives}
            for future in as_completed(futures):
                try:
                    steam_path = future.result()
                except OSError as exc:
                    app_services.log_error(f"Error searching drive {futures[future]}: {exc}")
                    continue

                if steam_path:
                    return steam_path

        return None
