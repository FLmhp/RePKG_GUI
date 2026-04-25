# RePKG_GUI

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Based on RePKG](https://img.shields.io/badge/Based%20on-RePKG-5C2D91)](https://github.com/notscuffed/repkg)
[![GitHub stars](https://img.shields.io/github/stars/FLmhp/RePKG_GUI?style=social)](https://github.com/FLmhp/RePKG_GUI/stargazers)

Windows 下基于 Tkinter 的 RePKG 图形界面，用于浏览、筛选并提取本地已安装的 Wallpaper Engine 创意工坊壁纸资源。

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
- 设置页、帮助页和关于页已补充结构化说明，并同步展示 RePKG `v0.4.0-alpha` 元数据
- 底部状态栏会统一反馈刷新、筛选、选择、输出模式和提取结果
- 自动读写 `runtime\config.json`，并记录 `runtime\logs.txt` / `runtime\errors.txt`

## 运行环境

- Windows
- 已安装 Steam
- 已安装 Wallpaper Engine，且目标创意工坊项目已经下载到本地
- Python 3.x
- 仓库根目录下可访问 `RePKG.exe`
- 如需本地打包，建议安装 [uv](https://docs.astral.sh/uv/)

推荐使用 `uv` 安装并运行：

```powershell
uv sync
uv run python main.py
```

也可以继续使用传统 `pip` 安装方式：

```powershell
pip install -r requirements.txt
```

`tkinter` 通常随 Windows 版 Python 一起提供，无需单独安装。

## 快速开始

```powershell
python main.py
```

首次启动时：

1. 如果 `runtime\config.json` 中没有有效的 `steam_path`，程序会弹出路径选择窗口。
2. 你可以手动浏览 `steam.exe`，也可以双击输入框触发自动搜索。
3. 路径确认后，程序会扫描本地创意工坊目录并生成 `runtime\info.csv`。
4. 在主窗口中刷新数据、筛选、预览并提取壁纸资源。

## 打包与发布

本仓库已提供 `uv + PyInstaller + GitHub Actions Release` 的发布链路。

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
2. 同步依赖并运行现有测试
3. 使用 `PyInstaller` 构建 `RePKG_GUI.exe`
4. 将分发目录压缩为 zip
5. 创建并发布对应的 GitHub Release

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
| `main.py` | GUI 主入口，负责扫描、筛选、预览和提取流程 |
| `app_services.py` | 配置、日志、Workshop 扫描与提取命令等共享服务 |
| `app_state.py` | 主界面共享状态对象 |
| `locate.py` | `steam.exe` 定位窗口与自动搜索逻辑 |
| `RePKG.exe` | 实际执行 `extract` 的命令行工具 |
| `config.example.json` | 示例配置模板 |
| `requirements.txt` | Python 依赖清单 |
| `pyproject.toml` | `uv` 项目配置与依赖声明 |
| `uv.lock` | `uv` 锁文件，用于固定发布依赖版本 |
| `RePKG_GUI.spec` | PyInstaller 打包配置 |
| `scripts\build-release.ps1` | 本地构建 zip 发布包的 PowerShell 脚本 |
| `.github\workflows\release.yml` | 基于 tag 的 GitHub Release 自动发布流程 |
| `runtime\` | 本地运行时目录，首次运行后生成，不随仓库提交 |
| `nekomusume.png` | “关于”页中使用的图片资源 |

## 运行时文件约定

- 程序默认将运行时文件写入 `runtime\` 目录，而不是仓库根目录。
- 首次运行或后续运行时，如果检测到根目录中的旧 `config.json` / `info.csv` / `logs.txt` / `errors.txt`，程序会迁移其内容到 `runtime\` 目录继续使用。
- 仓库提供 `config.example.json` 作为可提交的配置模板；实际运行配置应使用 `runtime\config.json`。
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
