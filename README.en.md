# RePKG_GUI

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Based on RePKG](https://img.shields.io/badge/Based%20on-RePKG-5C2D91)](https://github.com/notscuffed/repkg)
[![GitHub stars](https://img.shields.io/github/stars/FLmhp/RePKG_GUI?style=social)](https://github.com/FLmhp/RePKG_GUI/stargazers)

A Windows desktop GUI for RePKG built with PySide6 for browsing, filtering, previewing, and extracting locally installed Wallpaper Engine Workshop wallpapers.

<!-- README-I18N:START -->

[简体中文](./README.md) | **English**

<!-- README-I18N:END -->

## Overview

`RePKG_GUI` is built around [RePKG](https://github.com/notscuffed/repkg). It reads the local Steam Workshop directory at `steamapps\workshop\content\431960`, collects wallpaper metadata such as title, tags, type, visibility, project file, preview image, and ID, then runs `RePKG.exe` from the repository root or the packaged release directory to export assets.

The current desktop UI is in Chinese. The actual workflow is:

1. Locate or manually choose `steam.exe`
2. Scan locally downloaded Wallpaper Engine Workshop items
3. Browse, filter, preview, and select entries in list or thumbnail mode
4. Run `RePKG.exe extract` on the selected `scene.pkg` files

> [!IMPORTANT]
> This is a **Windows-only** desktop tool. It depends on local Steam / Wallpaper Engine data and requires each target item to contain a `scene.pkg` file.

## Current Features

- Automatically search for or manually select `steam.exe`
- Generate `runtime\info.csv` from the local Workshop directory
- Display wallpaper `title`, `tags`, `type`, `visibility`, `file`, `id`, and preview metadata
- Provide both **list mode** and **thumbnail mode**
- Filter by **title / tag / type**
- Refresh local Workshop data directly from the main window without restarting the app
- Sort table columns, reset filters, select all, preview, extract one item, or extract in batch
- Preview common `preview.*` files such as `preview.jpg`, `preview.jpeg`, `preview.gif`, and `preview.png`
- Support these RePKG extraction options:
  - `--no-tex-convert`
  - `-c` (copy `project.json` and preview files)
  - `--overwrite`
- Support three output modes, with subfolders based on wallpaper title or wallpaper ID
- Batch extraction now runs concurrently in the background; by default the worker count is derived from CPU cores and can be overridden in Settings
- The Settings page supports theme presets and custom theme colors, and persists those fields to `runtime\config.json`
- The Settings, Help, and About pages now provide structured guidance and synchronized RePKG `v0.4.0-alpha` metadata
- Show a status bar for refresh, filtering, selection, output mode, and extraction feedback
- Read and write `runtime\config.json`, and write runtime logs to `runtime\logs.txt` / `runtime\errors.txt`

## Requirements

- Windows
- Steam installed
- Wallpaper Engine installed, with the target Workshop items already downloaded locally
- Python 3.11 - 3.14
- `RePKG.exe` available in the repository root
- [uv](https://docs.astral.sh/uv/) recommended for local packaging

Recommended `uv` workflow:

```powershell
uv sync
uv run python -m repkg_gui
```

You can also keep using the traditional `pip` flow:

```powershell
pip install -r requirements.txt
```

`uv sync` / `pip install -r requirements.txt` install the dependencies required by the current PySide6 desktop app.

## Quick Start

```powershell
python -m repkg_gui
```

This is the same PySide6 entrypoint used by the packaged release.

On first launch:

1. If `runtime\config.json` does not contain a valid `steam_path`, the app opens a path selection window.
2. You can browse for `steam.exe` manually or double-click the input box to trigger auto-discovery.
3. After the path is confirmed, the app scans the local Workshop directory and generates `runtime\info.csv`.
4. Use the main window to refresh data, filter, preview, and extract wallpaper assets.

## Validation and Tests

The repository still uses `unittest`, with added PySide6-friendly smoke checks that can run without a live desktop session. In Windows PowerShell:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m compileall -q app_services.py repkg_gui test.py
python -c "from repkg_gui.ui.main_window import MainWindow; assert MainWindow.__name__ == 'MainWindow'; print('PySide6 main window import smoke test passed')"
python -m unittest test.py
```

`test.py` now covers shared services plus current PySide6 service / controller / worker behavior that can be validated headlessly.

## Packaging and Release

This repository now includes a `uv + PyInstaller + GitHub Actions Release` pipeline. Release bundles are built for the `repkg_gui` PySide6 desktop app while still bundling `RePKG.exe` and `nekomusume.png`.

Build the release bundle locally:

```powershell
uv sync --extra build
.\scripts\build-release.ps1 -ReleaseTag v2.0.0
```

The build creates:

- `dist\RePKG_GUI\` - the PyInstaller one-dir distribution
- `dist\RePKG_GUI-v2.0.0-windows.zip` - the archive ready for GitHub Release uploads

Publish the GitHub Release automatically:

```powershell
git tag v2.0.0
git push origin v2.0.0
```

After pushing a `v*` tag, GitHub Actions will:

1. install Python and `uv`
2. sync dependencies, byte-compile the Python sources, and smoke-test the PySide6 main window import
3. run the existing test suite
4. build `RePKG_GUI.exe` with `PyInstaller`
5. verify the packaged bundle still contains `RePKG.exe` and `nekomusume.png`
6. zip the distribution directory and publish the matching GitHub Release

## Output Modes

These descriptions map to the exact option labels shown in the current GUI:

| GUI option | Behavior |
| --- | --- |
| `分别输出至源文件所在文件夹` | Export into the `output` subfolder inside each Workshop item directory |
| `在指定文件夹中集中输出` | Export everything into one shared target directory |
| `在指定文件夹中输出至单独的文件夹` | Export each wallpaper into its own subfolder under the chosen directory |

With the third mode, you can also choose whether the subfolder name uses:

- the wallpaper title
- the wallpaper ID

## Key Files In This Repository

| File | Purpose |
| --- | --- |
| `repkg_gui\` | Current PySide6 application package containing UI, controllers, services, workers, and domain models |
| `app_services.py` | Shared services for config, logging, Workshop scanning, and extraction commands |
| `repkg_gui\app_metadata.py` | App version, author, and RePKG metadata |
| `RePKG.exe` | Command-line binary that performs the actual `extract` operation |
| `config.example.json` | Sample configuration template |
| `requirements.txt` | Python dependency list |
| `pyproject.toml` | `uv` project metadata and dependency declarations |
| `uv.lock` | `uv` lockfile for reproducible release dependencies |
| `RePKG_GUI.spec` | PyInstaller build configuration |
| `scripts\build-release.ps1` | PowerShell script for local release zip creation |
| `.github\workflows\release.yml` | Tag-based GitHub Release automation |
| `test.py` | `unittest` entry point covering shared services and current headless PySide6 core behavior |
| `runtime\` | Local runtime directory created after launch and not committed to the repo |
| `nekomusume.png` | Image asset used in the About tab |

## Runtime File Layout

- The app now writes runtime files under `runtime\` instead of the repository root.
- If legacy `config.json`, `info.csv`, `logs.txt`, or `errors.txt` files are found in the repository root, the app migrates them into `runtime\` and continues from there.
- `config.example.json` is the committed template; the actual runtime configuration lives in `runtime\config.json`.
- `runtime\config.json` currently persists `steam_path`, `output_path`, `batch_extract_workers`, `theme_preset`, `theme_background`, `theme_surface`, `theme_accent`, and `theme_text`.
- The following extraction options live only in the current app session and are not written to `runtime\config.json`: output mode, `--no-tex-convert`, title/ID subfolder naming, copying `project.json` / preview files, and overwriting existing files.
- Set `batch_extract_workers` to `0` to use automatic concurrency. The app will choose a conservative worker count based on CPU cores.
- Locally generated runtime files, IDE settings, and temporary debug files are intentionally excluded from version control via `.gitignore`.

## Known Limitations

- The current GUI text is Chinese-only; this README is bilingual.
- The app is designed for locally downloaded Wallpaper Engine Workshop content only.
- Extraction works only when a target item contains `scene.pkg`.
- Preview loading depends on a common `preview.*` file in the item directory.

## Credits

- [RePKG](https://github.com/notscuffed/repkg) `v0.4.0-alpha` - underlying extraction tool
- Author: FLmhp

## License

[MIT](./LICENSE)
