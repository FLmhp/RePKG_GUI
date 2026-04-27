# RePKG_GUI

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Based on RePKG](https://img.shields.io/badge/Based%20on-RePKG-5C2D91)](https://github.com/notscuffed/repkg)
[![GitHub stars](https://img.shields.io/github/stars/FLmhp/RePKG_GUI?style=social)](https://github.com/FLmhp/RePKG_GUI/stargazers)

Windows 下基于 RePKG 和 PySide6 的桌面图形界面，用于浏览、筛选、预览并提取本地已安装的 Wallpaper Engine 创意工坊壁纸资源。

<!-- README-I18N:START -->

**简体中文** | [English](./README.en.md)

<!-- README-I18N:END -->

## 简介

`RePKG_GUI` 围绕 [RePKG](https://github.com/notscuffed/repkg) 构建，读取 Steam 本地创意工坊目录 `steamapps\workshop\content\431960`，提取壁纸的标题、标签、类型、可见性、项目文件、预览图和 ID，随后通过仓库根目录或发布包目录中的 `RePKG.exe` 执行资源导出。

应用当前使用中文界面，核心流程是：

1. 定位或手动选择 `steam.exe`
2. 扫描本地已下载的 Wallpaper Engine 创意工坊条目
3. 在列表或缩略图模式中筛选、预览并选中目标
4. 调用 `RePKG.exe extract` 导出对应 `scene.pkg`

> [!IMPORTANT]
> 这是一个 **Windows 专用** 桌面工具，依赖本地 Steam / Wallpaper Engine 数据，并要求待提取项目目录中存在 `scene.pkg`。

## 当前功能

- 自动搜索或手动选择 `steam.exe`
- 从本地创意工坊目录生成 `runtime\info.csv`
- 展示壁纸 `title`、`tags`、`type`、`visibility`、`file`、`id` 与预览图信息
- 支持 **列表模式** 与 **缩略图模式**
- 支持按 **标题 / 标签 / 类型** 筛选
- 主窗口支持直接刷新本地 Workshop 数据，无需重启程序
- 支持表格排序、重置筛选、全选、单个提取与批量提取
- 支持预览常见 `preview.*` 文件，例如 `preview.jpg`、`preview.jpeg`、`preview.gif`、`preview.png`
- 支持以下 RePKG 提取选项：
  - `--no-tex-convert`
  - `-c`（复制 `project.json` 和预览文件）
  - `--overwrite`
- 支持三种输出模式，并可选择使用壁纸标题或壁纸 ID 作为子目录名
- 批量提取已改为后台并发执行，默认按 CPU 核心数自动决定线程数，也可在设置页手动覆盖
- 设置页支持主题预设与自定义主题配色，相关字段会写入 `runtime\config.json`
- 设置页、帮助页和关于页已补充结构化说明，并同步展示 RePKG `v0.4.0-alpha` 元数据
- 底部状态栏会统一反馈刷新、筛选、选择、输出模式和提取结果
- 自动读写 `runtime\config.json`，并记录 `runtime\logs.txt` / `runtime\errors.txt`

## 运行环境

- Windows
- 已安装 Steam
- 已安装 Wallpaper Engine，且目标创意工坊项目已经下载到本地
- Python 3.11 - 3.14
- 仓库根目录下可访问 `RePKG.exe`
- 如需本地打包，建议安装 [uv](https://docs.astral.sh/uv/)

推荐使用 `uv` 安装并运行：

```powershell
uv sync
uv run python -m repkg_gui
```

也可以继续使用传统 `pip` 安装方式：

```powershell
pip install -r requirements.txt
```

`uv sync` / `pip install -r requirements.txt` 会安装当前 PySide6 桌面应用所需依赖。

## 快速开始

```powershell
python -m repkg_gui
```

上面的命令会启动当前打包/发布所使用的 PySide6 应用入口。

首次启动时：

1. 如果 `runtime\config.json` 中没有有效的 `steam_path`，程序会弹出路径选择窗口。
2. 你可以手动浏览 `steam.exe`，也可以双击输入框触发自动搜索。
3. 路径确认后，程序会扫描本地创意工坊目录并生成 `runtime\info.csv`。
4. 在主窗口中刷新数据、筛选、预览并提取壁纸资源。

## 验证与测试

本仓库当前沿用 `unittest`，并补充了适合无桌面环境的 PySide6 导入 / 架构验证。Windows PowerShell 下可执行：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m compileall -q app_services.py repkg_gui test.py
python -c "from repkg_gui.ui.main_window import MainWindow; assert MainWindow.__name__ == 'MainWindow'; print('PySide6 main window import smoke test passed')"
python -m unittest test.py
```

其中 `test.py` 会覆盖共享服务，以及当前 PySide6 service / controller / worker 等无界面核心逻辑。

## 打包与发布

本仓库已提供 `uv + PyInstaller + GitHub Actions Release` 的发布链路，发布包当前面向 `repkg_gui` PySide6 桌面应用构建，并继续捆绑 `RePKG.exe` 和 `nekomusume.png`。

本地构建发布包：

```powershell
uv sync --extra build
.\scripts\build-release.ps1 -ReleaseTag v1.0.0
```

执行后会生成：

- `dist\RePKG_GUI\`：PyInstaller one-dir 分发目录
- `dist\RePKG_GUI-v1.0.0-windows.zip`：可直接上传到 GitHub Release 的压缩包

自动发布 GitHub Release：

```powershell
git tag v1.0.0
git push origin v1.0.0
```

推送 `v*` 标签后，GitHub Actions 会在 Windows runner 上：

1. 安装 Python 和 `uv`
2. 同步依赖、编译检查 Python 源码，并验证 PySide6 主窗口可导入
3. 运行现有测试
4. 使用 `PyInstaller` 构建 `RePKG_GUI.exe`
5. 校验发布目录中仍包含 `RePKG.exe` 与 `nekomusume.png`
6. 将分发目录压缩为 zip 并创建对应的 GitHub Release

## 输出模式

下表对应 GUI 中的实际选项名称：

| GUI 选项 | 行为 |
| --- | --- |
| `分别输出至源文件所在文件夹` | 输出到每个创意工坊项目目录下的 `output` 子目录 |
| `在指定文件夹中集中输出` | 将所有提取结果集中输出到同一个目录 |
| `在指定文件夹中输出至单独的文件夹` | 在指定目录下为每个壁纸创建独立子目录输出 |

当使用第三种模式时，还可以切换为：

- 使用壁纸标题作为子目录名
- 使用壁纸 ID 作为子目录名

## 仓库中的关键文件

| 文件 | 说明 |
| --- | --- |
| `repkg_gui\` | 当前 PySide6 应用包，包含 UI、controller、service、worker 与领域模型 |
| `app_services.py` | 配置、日志、Workshop 扫描与提取命令等共享服务 |
| `repkg_gui\app_metadata.py` | 应用版本、作者与 RePKG 相关元信息 |
| `RePKG.exe` | 实际执行 `extract` 的命令行工具 |
| `config.example.json` | 示例配置模板 |
| `requirements.txt` | Python 依赖清单 |
| `pyproject.toml` | `uv` 项目配置与依赖声明 |
| `uv.lock` | `uv` 锁文件，用于固定发布依赖版本 |
| `RePKG_GUI.spec` | PyInstaller 打包配置 |
| `scripts\build-release.ps1` | 本地构建 zip 发布包的 PowerShell 脚本 |
| `.github\workflows\release.yml` | 基于 tag 的 GitHub Release 自动发布流程 |
| `test.py` | `unittest` 测试入口，覆盖共享服务和当前 PySide6 无界面核心逻辑 |
| `runtime\` | 本地运行时目录，首次运行后生成，不随仓库提交 |
| `nekomusume.png` | “关于”页中使用的图片资源 |

## 运行时文件约定

- 程序默认将运行时文件写入 `runtime\` 目录，而不是仓库根目录。
- 首次运行或后续运行时，如果检测到根目录中的旧 `config.json` / `info.csv` / `logs.txt` / `errors.txt`，程序会迁移其内容到 `runtime\` 目录继续使用。
- 仓库提供 `config.example.json` 作为可提交的配置模板；实际运行配置应使用 `runtime\config.json`。
- `runtime\config.json` 当前持久化字段为 `steam_path`、`output_path`、`batch_extract_workers`、`theme_preset`、`theme_background`、`theme_surface`、`theme_accent`、`theme_text`。
- 以下提取选项只保存在当前程序会话中，不会写入 `runtime\config.json`：输出模式、`--no-tex-convert`、按标题 / ID 建子目录、复制 `project.json` / 预览文件、覆盖现有文件。
- `batch_extract_workers` 填 `0` 表示自动并发，程序会按 CPU 核心数选择一个保守的线程数。
- 仓库不会保留本地生成的运行时文件、IDE 配置和临时调试文件；这些内容已通过 `.gitignore` 排除。

## 已知限制

- 当前 GUI 文案为中文，README 提供中英双语说明。
- 仅面向本地已下载的 Wallpaper Engine 创意工坊内容。
- 仅当项目目录中存在 `scene.pkg` 时才能提取。
- 预览图读取依赖作品目录中的常见 `preview.*` 文件。

## 致谢

- [RePKG](https://github.com/notscuffed/repkg) `v0.4.0-alpha` - 底层提取工具
- 作者：FLmhp

## License

[MIT](./LICENSE)
