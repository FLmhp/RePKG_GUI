import os
import re
import webbrowser
from concurrent.futures import ThreadPoolExecutor

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, UnidentifiedImageError

from app_services import (
    CONFIG_FILE,
    DEFAULT_BATCH_EXTRACT_WORKERS,
    DEFAULT_OUTPUT_PATH,
    INFO_CSV_FILE,
    LOCAL_OUTPUT_MODE,
    MAX_BATCH_EXTRACT_WORKERS,
    PROJECT_ROOT,
    REPKG_EXECUTABLE,
    RESOURCE_ROOT,
    SEPARATE_OUTPUT_MODE,
    SHARED_OUTPUT_MODE,
    ExtractionOptions,
    build_extract_command,
    ensure_config_file,
    extract_info_to_csv,
    get_auto_batch_extract_workers,
    get_scene_pkg_path,
    load_config,
    log_error,
    log_success,
    normalize_wallpaper_id,
    normalize_wallpaper_type,
    normalize_preview_path,
    read_config_value,
    read_info_csv,
    resolve_batch_extract_workers,
    run_extract_command,
    write_config_value,
)
from app_state import AppState
from locate import Locate

app_state = AppState()
CONFIG_DISPLAY_PATH = os.path.relpath(CONFIG_FILE, PROJECT_ROOT)
INFO_DISPLAY_PATH = os.path.relpath(INFO_CSV_FILE, PROJECT_ROOT)
REPKG_DISPLAY_PATH = os.path.relpath(REPKG_EXECUTABLE, PROJECT_ROOT)
APP_VERSION = "1.0.0"
APP_AUTHOR = "FLmhp"
APP_AUTHOR_URL = "https://blog.csdn.net/flMHP?spm=1010.2135.3001.5343"
REPKG_VERSION = "v0.4.0-alpha"
REPKG_AUTHOR = "notscuffed"
REPKG_PROJECT_URL = "https://github.com/notscuffed/repkg"
ABOUT_IMAGE_URL = "https://i.postimg.cc/Kc92tL7f/MEITU-20250210-165522349.jpg"
TAB_TEXT_WRAP = 540
VISIBILITY_LABELS = {
    "public": "公开",
    "private": "私有",
    "friends": "好友可见",
    "unlisted": "未列出",
}


def set_status(message):
    if app_state.status_var is not None:
        app_state.status_var.set(message)


def build_loaded_status(total_count, refreshed=False):
    prefix = "刷新完成，已加载" if refreshed else "已加载"
    return f"{prefix} {total_count} 项壁纸数据。"


def build_filter_status(field, keyword, visible_count, total_count):
    if not keyword:
        return build_loaded_status(total_count)

    return f"已按{field}筛选“{keyword}”，匹配 {visible_count}/{total_count} 项。"


def build_selection_status(selected_count, visible_count):
    if selected_count:
        return f"已选择 {selected_count} 项，当前列表共 {visible_count} 项。"

    return f"当前未选择项目，当前列表共 {visible_count} 项。"


def summarize_extraction_results(success_ids, missing_scene_pkg_ids, failed_items):
    success_count = len(success_ids)
    summary_lines = [f"成功提取 {success_count} 项"]

    if missing_scene_pkg_ids:
        summary_lines.append(f"缺少 scene.pkg: {', '.join(missing_scene_pkg_ids)}")
    if failed_items:
        failure_summary = ", ".join(f"{item_id}({reason})" for item_id, reason in failed_items)
        summary_lines.append(f"执行失败: {failure_summary}")

    status_parts = [f"提取完成：成功 {success_count} 项"]
    if missing_scene_pkg_ids:
        status_parts.append(f"缺少资源 {len(missing_scene_pkg_ids)} 项")
    if failed_items:
        status_parts.append(f"失败 {len(failed_items)} 项")

    return "\n".join(summary_lines), "，".join(status_parts), bool(missing_scene_pkg_ids or failed_items)


def update_selection_status(tree):
    set_status(build_selection_status(len(app_state.selected_items), len(tree.get_children())))


def get_output_mode_description(mode):
    descriptions = {
        LOCAL_OUTPUT_MODE: "提取结果直接放到壁纸原目录下的 output 文件夹里。",
        SHARED_OUTPUT_MODE: "所有提取结果都放到同一个目录里。",
        SEPARATE_OUTPUT_MODE: "在目标目录下按壁纸分开建文件夹，批量导出更清楚。",
    }
    return descriptions.get(mode, "当前输出模式暂时没有说明。")


def format_batch_extract_workers_display(configured_workers):
    resolved_workers = resolve_batch_extract_workers(configured_workers)
    if configured_workers <= 0:
        return f"自动（当前 {resolved_workers} 线程）"
    return f"{resolved_workers} 线程"


def get_batch_extract_workers_description(configured_workers):
    resolved_workers = resolve_batch_extract_workers(configured_workers)
    if configured_workers <= 0:
        return f"当前为自动模式，会按 CPU 核心数决定并发数，当前实际使用 {resolved_workers} 线程。"
    return f"当前手动设置为 {resolved_workers} 线程。填 0 可切回自动模式。"


def parse_batch_extract_workers_input(value):
    text = str(value).strip()
    if not text:
        return DEFAULT_BATCH_EXTRACT_WORKERS
    if not text.isdigit():
        raise ValueError("批量提取并发数只能填写 0 或正整数。")

    parsed_value = int(text)
    if parsed_value > MAX_BATCH_EXTRACT_WORKERS:
        raise ValueError(f"批量提取并发数不能超过 {MAX_BATCH_EXTRACT_WORKERS}。")
    return parsed_value


def get_configured_batch_extract_workers():
    if app_state.batch_extract_workers_var is not None:
        return parse_batch_extract_workers_input(app_state.batch_extract_workers_var.get())
    return load_config().batch_extract_workers


def build_settings_summary(steam_path, output_path, output_mode, batch_extract_workers=DEFAULT_BATCH_EXTRACT_WORKERS):
    steam_display = steam_path or "还没设置"
    output_display = output_path or DEFAULT_OUTPUT_PATH
    return "\n".join(
        [
            f"steam.exe：{steam_display}",
            f"输出模式：{output_mode}",
            f"输出目录：{output_display}",
            f"批量提取并发：{format_batch_extract_workers_display(batch_extract_workers)}",
            f"配置文件：{CONFIG_DISPLAY_PATH}",
        ]
    )


def build_help_sections():
    runtime_dir_display = os.path.relpath(os.path.dirname(CONFIG_FILE), PROJECT_ROOT)
    auto_workers = get_auto_batch_extract_workers()
    return [
        (
            "快速开始",
            [
                "1. 首次启动时，请先在设置页确认 steam.exe 路径。",
                f"2. 路径确认后，程序会扫描 Wallpaper Engine 创意工坊目录并生成 {INFO_DISPLAY_PATH}。",
                "3. 扫描完成后，就能在列表模式或缩略图模式里浏览、筛选和预览壁纸。",
                "4. 提取前看一下输出模式、输出目录和自定义选项。",
            ],
        ),
        (
            "常见操作",
            [
                "1. 顶部“刷新数据”会重新扫一遍本地 Workshop，不用重启。",
                "2. 列表区支持筛选、重置筛选、全选和批量提取。",
                "3. 列表区会显示类型、可见性这些必要信息；右键列表项可以看大图。",
                "4. 批量提取会在后台并发执行，窗口底部状态栏会显示提取状态。",
            ],
        ),
        (
            "设置页说明",
            [
                "1. steam.exe 路径会决定从哪里找本地 Workshop 文件。",
                f"2. “{LOCAL_OUTPUT_MODE}”适合就地导出；“{SHARED_OUTPUT_MODE}”适合集中整理；“{SEPARATE_OUTPUT_MODE}”适合批量分项目保存。",
                "3. 批量提取并发数填 0 表示自动，默认会按 CPU 核心数决定，当前自动值会落在保守范围内。",
                "4. 自定义选项会影响下一次提取，比如是否转换 TEX、复制附带文件、覆盖旧文件。",
                "5. 页面下方的摘要会显示当前路径、输出模式、并发数和配置文件位置。",
            ],
        ),
        (
            "文件位置",
            [
                f"- 运行配置：{CONFIG_DISPLAY_PATH}",
                f"- 壁纸索引：{INFO_DISPLAY_PATH}",
                f"- 日志目录：{runtime_dir_display}",
                f"- 提取工具：{REPKG_DISPLAY_PATH}（基于 {REPKG_VERSION}）",
                f"- 自动并发参考值：当前约 {auto_workers} 线程",
            ],
        ),
        (
            "常见问题与排错",
            [
                f"- 未找到提取工具：请确认 {REPKG_DISPLAY_PATH} 位于仓库根目录。",
                "- 缺少 scene.pkg：这个壁纸目录里没有可提取的主资源包。",
                "- 输出路径为空：集中输出或独立子目录输出时，要先选好输出文件夹。",
                f"- 想看运行日志的话，去 {runtime_dir_display} 目录看 logs.txt 和 errors.txt。",
            ],
        ),
    ]


def load_resized_photo_image(image_path, max_width, max_height=None):
    with Image.open(image_path) as image:
        original_width, original_height = image.size

        scale_factor = 1.0
        if max_width is not None and original_width:
            scale_factor = min(scale_factor, max_width / original_width)
        if max_height is not None and original_height:
            scale_factor = min(scale_factor, max_height / original_height)

        new_width = max(int(original_width * scale_factor), 1)
        new_height = max(int(original_height * scale_factor), 1)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        return ImageTk.PhotoImage(resized_image), new_width, new_height


def read_path_from_file(key):
    """
    从 config.json 文件中读取指定键的路径。

    :param key: 键名（"steam_path" 或 "output_path"）
    :return: 有效的路径或 None
    """
    return read_config_value(key)


def load_wallpaper_dataframe():
    """
    刷新 info.csv 并返回对应的 DataFrame。
    """
    try:
        extract_info_to_csv()
    except ValueError as exc:
        messagebox.showwarning("路径未找到", str(exc))
        log_error(str(exc))
        return None
    except FileNotFoundError as exc:
        messagebox.showwarning("目录不存在", str(exc))
        log_error(str(exc))
        return None
    except OSError as exc:
        messagebox.showwarning("读取文件失败", f"扫描创意工坊目录时发生错误: {exc}")
        log_error(f"扫描创意工坊目录时发生错误: {exc}")
        return None

    df = read_info_csv(INFO_CSV_FILE)
    if df is None:
        messagebox.showwarning("读取 CSV 文件失败", f"无法读取 {INFO_DISPLAY_PATH} 文件")
    return df


def write_output_path_to_file(output_path):
    """
    将输出路径写入 config.json 文件。

    :param output_path: 输出路径
    """
    try:
        write_config_value("output_path", output_path)
    except FileNotFoundError:
        log_error(f"{CONFIG_DISPLAY_PATH} 文件未找到")
    except (OSError, ValueError) as e:
        log_error(f"写入 {CONFIG_DISPLAY_PATH} 文件时发生错误: {e}")
        messagebox.showwarning("写入文件失败", f"写入文件 {CONFIG_DISPLAY_PATH} 时发生错误: {e}")

def sort_column(tree, col, reverse):
    """
    根据列标题排序树形视图中的数据。
    
    :param tree: Treeview 对象
    :param col: 列名
    :param reverse: 是否反向排序
    """
    try:
        items = [(tree.set(item_key, col), item_key) for item_key in tree.get_children("")]
        items.sort(reverse=reverse)

        for index, (_, item_key) in enumerate(items):
            tree.move(item_key, "", index)
            tree.set(item_key, "index", index + 1)

        tree.heading(col, command=lambda: sort_column(tree, col, not reverse))
        log_success(f"成功排序列: {col}")
    except (tk.TclError, ValueError) as exc:
        log_error(f"排序列 {col} 时发生错误: {exc}")


def format_tags_for_display(tags):
    if not isinstance(tags, list):
        return ""
    return ", ".join(tags)


def format_visibility_for_display(visibility):
    normalized_visibility = str(visibility).strip().lower()
    if not normalized_visibility:
        return "未标注"
    return VISIBILITY_LABELS.get(normalized_visibility, normalized_visibility)


def build_wallpaper_metadata_summary(record):
    type_display = normalize_wallpaper_type(record.get("type", "")) or "未标注"
    visibility_display = format_visibility_for_display(record.get("visibility", ""))
    project_file = str(record.get("file", "")).strip() or "未标注"
    preview_path = normalize_preview_path(record.get("preview", ""))
    preview_display = os.path.basename(preview_path) if preview_path else "未找到"
    return "\n".join(
        [
            f"类型：{type_display}",
            f"可见性：{visibility_display}",
            f"项目文件：{project_file}",
            f"预览文件：{preview_display}",
        ]
    )


def get_tree_item_id(item_values):
    if not item_values:
        return ""
    return normalize_wallpaper_id(item_values[-1])


def insert_rows_into_tree(tree, df):
    for item in tree.get_children():
        tree.delete(item)

    for index, row in df.iterrows():
        tags_display = format_tags_for_display(row["tags"])
        type_display = normalize_wallpaper_type(row["type"])
        visibility_display = format_visibility_for_display(row.get("visibility", ""))
        tree.insert(
            "",
            tk.END,
            values=(
                index + 1,
                row["title"],
                tags_display,
                type_display,
                visibility_display,
                normalize_wallpaper_id(row["id"]),
            ),
        )

def on_click(event):
    tree = event.widget
    # 获取当前选中的项
    selected_item = tree.identify_row(event.y)
    if selected_item:
        # 取消选择
        tree.selection_remove(selected_item)

def create_thumbnail_mode(preview_frame, df, mode_frame):
    """
    创建缩略图模式的显示。
    
    :param preview_frame: 预览框架
    :param df: 包含信息的 DataFrame
    :param mode_frame: 模式切换框架
    """
    # 清除 preview_frame 中除了 mode_frame 之外的所有子组件
    for widget in preview_frame.winfo_children():
        if widget is not mode_frame:
            widget.destroy()

    # 创建左侧区域（缩略图和滚动条）
    left_frame = tk.Frame(preview_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 创建右侧区域（预览图、标题、按钮）
    right_frame = tk.Frame(preview_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=10, pady=10)

    # 创建滚动条框架
    scroll_frame = tk.Frame(left_frame)
    scroll_frame.pack(side=tk.RIGHT, fill=tk.Y)

    # 创建滚动条
    scrollbar = tk.Scrollbar(scroll_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 创建画布
    canvas = tk.Canvas(left_frame, yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 配置滚动条
    scrollbar.config(command=canvas.yview)

    # 创建内部框架
    inner_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)

    # 更新画布的滚动区域
    def update_scroll_region(event):
        _ = event
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner_frame.bind("<Configure>", update_scroll_region)

    # 绑定鼠标滚轮事件
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def show_thumbnail_details(event, path, title, wallpaper_id):
        _ = event
        on_thumbnail_click(right_frame, path, title, wallpaper_id, df)

    canvas.bind("<MouseWheel>", on_mousewheel)
    inner_frame.bind("<MouseWheel>", on_mousewheel)

    # 加载并显示缩略图
    first_preview_path = None
    first_title = None
    first_id = None

    for index, row in df.iterrows():
        preview_path = row["preview"]
        if preview_path and os.path.exists(preview_path):
            try:
                photo, _, _ = load_resized_photo_image(preview_path, 150, 150)
                label = tk.Label(inner_frame, image=photo)
                label.image = photo  # 保存对图像的引用
                label.grid(row=index // 3, column=index % 3, padx=10, pady=10)
                label.bind(
                    "<Button-1>",
                    lambda event, path=preview_path, title=row["title"], wallpaper_id=row["id"]: show_thumbnail_details(
                        event, path, title, wallpaper_id
                    ),
                )
                label.bind("<MouseWheel>", on_mousewheel)

                # 记录第一张图片的信息
                if first_preview_path is None:
                    first_preview_path = preview_path
                    first_title = row["title"]
                    first_id = row["id"]
            except (FileNotFoundError, OSError, UnidentifiedImageError) as exc:
                log_error(f"加载图像 {preview_path} 时发生错误: {exc}")

    # 如果有第一张图片，则默认展示
    if first_preview_path:
        on_thumbnail_click(right_frame, first_preview_path, first_title, first_id, df)
    else:
        tk.Label(right_frame, text="当前没有可用的预览图", justify="center").pack(pady=20)
        set_status("已切换到缩略图模式，但当前数据中没有可用的预览图。")

def on_thumbnail_click(right_frame, preview_path, title, id, df):
    """
    处理缩略图点击事件，展示缩放后的预览图、标题，并添加提取按钮和打开文件夹按钮。

    :param right_frame: 右侧区域框架
    :param preview_path: 预览图路径
    :param title: 标题
    :param id: 壁纸ID
    """
    # 清除右侧区域的所有子组件
    for widget in right_frame.winfo_children():
        widget.destroy()

    # 加载并显示缩放后的预览图
    try:
        photo, _, _ = load_resized_photo_image(preview_path, 200)
    except (FileNotFoundError, OSError, UnidentifiedImageError) as exc:
        messagebox.showerror("错误", f"无法加载图像：{exc}")
        set_status(f"预览加载失败：{exc}")
        return

    # 创建标签显示图像
    label = tk.Label(right_frame, image=photo)
    label.image = photo  # 保存对图像的引用
    label.pack(pady=10)

    # 创建标签显示标题（自动换行）
    title_label = tk.Label(right_frame, text=title, wraplength=200, justify="center")
    title_label.pack(pady=10)

    matching_row = find_matching_row(df, id)
    if matching_row is not None:
        tk.Label(
            right_frame,
            text=build_wallpaper_metadata_summary(matching_row),
            wraplength=220,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(0, 10))

    # 创建提取按钮
    extract_button = tk.Button(right_frame, text="提取", command=lambda: extract_wallpaper(id, df))
    extract_button.pack(pady=5)

    # 创建打开文件夹按钮
    open_folder_button = tk.Button(right_frame, text="打开文件夹", command=lambda: open_folder(os.path.dirname(preview_path)))
    open_folder_button.pack(pady=5)

def get_extraction_options():
    steam_path = read_path_from_file("steam_path")
    if not steam_path:
        messagebox.showwarning("路径未找到", f"{CONFIG_DISPLAY_PATH} 中 steam_path 未找到或无效")
        log_error(f"{CONFIG_DISPLAY_PATH} 中 steam_path 未找到或无效")
        return None

    if app_state.output_path_var is None or app_state.output_mode_var is None:
        messagebox.showwarning("输出设置未就绪", "输出配置尚未初始化完成")
        log_error("输出配置尚未初始化完成")
        return None

    output_path = app_state.output_path_var.get().strip()
    output_mode = app_state.output_mode_var.get()
    if output_mode != LOCAL_OUTPUT_MODE and not output_path:
        messagebox.showwarning("输出路径为空", "请选择有效的输出路径")
        log_error("输出路径为空")
        return None

    return ExtractionOptions(
        steam_path=steam_path,
        output_path=output_path or DEFAULT_OUTPUT_PATH,
        output_mode=output_mode,
        not_convert_tex_to_image=app_state.not_convert_tex_to_image_var.get() if app_state.not_convert_tex_to_image_var else False,
        use_wallpaper_name_as_subdir=app_state.use_wallpaper_name_as_subdir_var.get() if app_state.use_wallpaper_name_as_subdir_var else True,
        copy_project_json_and_preview=app_state.copy_project_json_and_preview_var.get() if app_state.copy_project_json_and_preview_var else False,
        overwrite_files=app_state.overwrite_files_var.get() if app_state.overwrite_files_var else True,
    )


def find_matching_row(df, item_id):
    matching_rows = df[df["id"].astype(str) == str(item_id)]
    if matching_rows.empty:
        return None
    return matching_rows.iloc[0]


def prepare_extraction_requests(item_ids, df, options):
    title_map = {
        normalize_wallpaper_id(row.id): row.title for row in df.itertuples(index=False)
    }
    valid_requests = []
    missing_scene_pkg_ids = []
    failed_items = []

    for item_id in item_ids:
        normalized_item_id = normalize_wallpaper_id(item_id)
        scene_pkg_path = get_scene_pkg_path(options.steam_path, normalized_item_id)
        if not os.path.exists(scene_pkg_path):
            missing_scene_pkg_ids.append(normalized_item_id)
            continue

        title = title_map.get(normalized_item_id)
        if title is None:
            failed_items.append((normalized_item_id, "未找到对应的壁纸信息"))
            log_error(f"未找到 ID 为 {normalized_item_id} 的项目")
            continue

        valid_requests.append((normalized_item_id, title))

    return valid_requests, missing_scene_pkg_ids, failed_items


def execute_single_extraction_task(item_id, title, options):
    try:
        command = build_extract_command(options, item_id, title)
        result = run_extract_command(command)
    except ValueError as exc:
        log_error(str(exc))
        return {"item_id": str(item_id), "success": False, "error": str(exc)}
    except OSError as exc:
        log_error(f"执行命令时发生错误: {exc}")
        return {"item_id": str(item_id), "success": False, "error": str(exc)}

    if result.returncode == 0:
        log_success(f"成功提取壁纸ID: {item_id} 并执行命令")
        return {"item_id": str(item_id), "success": True, "error": ""}

    error_message = result.stderr.strip() or result.stdout.strip() or "未知错误"
    log_error(f"提取壁纸ID {item_id} 失败: {error_message}")
    return {"item_id": str(item_id), "success": False, "error": error_message}


def execute_extraction(item_ids, df, show_progress=False):
    options = get_extraction_options()
    if options is None:
        return

    if not os.path.exists(REPKG_EXECUTABLE):
        messagebox.showerror("提取失败", f"未找到提取工具：{REPKG_DISPLAY_PATH}")
        log_error(f"未找到提取工具：{REPKG_DISPLAY_PATH}")
        return

    try:
        configured_workers = get_configured_batch_extract_workers()
    except ValueError as exc:
        messagebox.showwarning("并发设置无效", str(exc))
        set_status("批量提取未开始：并发设置无效。")
        return

    progress_root = None
    progress_bar = None
    progress_label = None
    if show_progress:
        progress_root = tk.Toplevel()
        progress_root.title("提取进度")
        progress_root.geometry("400x100")
        progress_root.resizable(False, False)
        progress_root.protocol("WM_DELETE_WINDOW", lambda: None)

        progress_bar = ttk.Progressbar(progress_root, orient="horizontal", length=300, mode="determinate")
        progress_bar.pack(pady=20)
        progress_label = tk.Label(progress_root, text="0%")
        progress_label.pack()
        progress_root.update_idletasks()
        center_window(progress_root)

    def update_progress(current, total):
        if progress_root is None:
            return
        progress = (current / total) * 100
        progress_bar["value"] = progress
        progress_label.config(text=f"{int(progress)}%")
        progress_root.update_idletasks()

    total_items = len(item_ids)
    success_ids = []
    valid_requests, missing_scene_pkg_ids, failed_items = prepare_extraction_requests(item_ids, df, options)
    processed_items = len(missing_scene_pkg_ids) + len(failed_items)
    worker_count = min(resolve_batch_extract_workers(configured_workers), max(len(valid_requests), 1))
    set_status(f"正在提取 {total_items} 项壁纸（并发 {worker_count} 线程）...")

    def finish_extraction():
        if progress_root is not None and progress_root.winfo_exists():
            progress_root.destroy()

        summary_message, status_message, has_warning = summarize_extraction_results(
            success_ids, missing_scene_pkg_ids, failed_items
        )
        set_status(status_message)
        if has_warning:
            messagebox.showwarning("提取完成", summary_message)
        else:
            messagebox.showinfo("提取完成", summary_message)

    update_progress(processed_items, total_items)

    if not valid_requests:
        finish_extraction()
        return

    if show_progress and len(valid_requests) > 1:
        executor = ThreadPoolExecutor(max_workers=worker_count)
        futures = {
            executor.submit(execute_single_extraction_task, item_id, title, options): item_id
            for item_id, title in valid_requests
        }

        def poll_futures():
            nonlocal processed_items
            completed_futures = [future for future in list(futures) if future.done()]

            for future in completed_futures:
                item_id = futures.pop(future)
                try:
                    result = future.result()
                except OSError as exc:
                    failed_items.append((str(item_id), str(exc)))
                    log_error(f"异步提取 {item_id} 时发生错误: {exc}")
                else:
                    if result["success"]:
                        success_ids.append(result["item_id"])
                    else:
                        failed_items.append((result["item_id"], result["error"]))

                processed_items += 1
                update_progress(processed_items, total_items)

            if futures:
                if progress_root is not None and progress_root.winfo_exists():
                    progress_root.after(100, poll_futures)
                return

            executor.shutdown(wait=False)
            finish_extraction()

        if progress_root is not None:
            progress_root.after(100, poll_futures)
        else:
            poll_futures()
        return

    for item_id, title in valid_requests:
        result = execute_single_extraction_task(item_id, title, options)
        if result["success"]:
            success_ids.append(result["item_id"])
        else:
            failed_items.append((result["item_id"], result["error"]))
        processed_items += 1
        update_progress(processed_items, total_items)

    finish_extraction()


def extract_wallpaper(id, df):
    """
    将被点击的预览图对应的壁纸的ID根据功能选项构造提取命令并在后台执行。

    :param id: 壁纸ID
    """
    execute_extraction([id], df)

def toggle_mode(preview_frame, df, mode_var, mode_frame):
    """
    在列表模式和缩略图模式之间切换。
    
    :param preview_frame: 预览框架
    :param df: 包含信息的 DataFrame
    :param mode_var: 模式变量
    :param mode_frame: 模式切换框架
    """
    mode = mode_var.get()
    tree = app_state.current_tree_widget
    extract_button = app_state.current_extract_button

    if mode == "列表模式":
        # 清除 preview_frame 中除了 mode_frame 之外的所有子组件
        for widget in preview_frame.winfo_children():
            if widget is not mode_frame:
                widget.destroy()

        # 创建 Treeview 对象
        tree = create_top_preview_frame(preview_frame, df)
        app_state.current_tree_widget = tree

        # 绑定右键点击事件
        tree.bind("<Button-3>", lambda event: on_right_click(tree, event, df))

        # 重新创建筛选框架
        extract_button = create_bottom_preview_frame(preview_frame, tree, df)
        app_state.current_extract_button = extract_button

        # 显示开始提取按钮
        extract_button.pack(side=tk.BOTTOM, padx=5, pady=5)
        update_selection_status(tree)

    elif mode == "缩略图模式":
        if tree is not None:
            tree.pack_forget()
        create_thumbnail_mode(preview_frame, df, mode_frame)

        # 隐藏开始提取按钮
        if extract_button is not None:
            extract_button.pack_forget()
        if any(normalize_preview_path(value) and os.path.exists(normalize_preview_path(value)) for value in df["preview"]):
            set_status("已切换到缩略图模式，可点击缩略图查看、提取或打开对应文件夹。")

def create_top_preview_frame(preview_frame, df):
    """
    创建预览上部框架（信息表格）。
    
    :param preview_frame: 预览框架
    :param df: 包含信息的 DataFrame
    """
    # 创建 Treeview 对象
    tree = ttk.Treeview(
        preview_frame,
        columns=("index", "title", "tags", "type", "visibility", "id"),
        show='headings',
        selectmode=tk.EXTENDED,
    )

    # 设置列标题和排序功能
    tree.heading("index", text="序号")
    tree.heading("title", text="标题", command=lambda: sort_column(tree, "title", False))
    tree.heading("tags", text="标签", command=lambda: sort_column(tree, "tags", False))
    tree.heading("type", text="类型", command=lambda: sort_column(tree, "type", False))
    tree.heading("visibility", text="可见性", command=lambda: sort_column(tree, "visibility", False))
    tree.heading("id", text="ID", command=lambda: sort_column(tree, "id", False))

    # 设置列宽度和对齐方式
    tree.column("index", width=50, anchor=tk.CENTER)
    tree.column("title", width=200, anchor=tk.CENTER)
    tree.column("tags", width=80, anchor=tk.CENTER)
    tree.column("type", width=50, anchor=tk.CENTER)
    tree.column("visibility", width=80, anchor=tk.CENTER)
    tree.column("id", width=100, anchor=tk.CENTER)

    # 插入数据到 Treeview
    insert_rows_into_tree(tree, df)

    tree.pack(expand=True, fill=tk.BOTH)

    # 绑定单击事件
    tree.bind("<Button-1>", lambda event: on_tree_select(tree, event))
    tree.bind("<ButtonRelease-1>", on_click)
    tree.bind("<Button-3>", lambda event: on_right_click(tree, event, df))

    return tree

def create_bottom_preview_frame(preview_frame, tree, df):
    """
    创建预览下部框架（标签筛选）。
    
    :param preview_frame: 预览框架
    :param tree: Treeview 对象
    :param df: 包含信息的 DataFrame
    """
    # 创建预览下部框架（标签筛选）
    bottom_preview_frame = tk.Frame(preview_frame)
    bottom_preview_frame.pack(side=tk.BOTTOM, fill=tk.X)

    # 创建筛选字段选择框和关键词输入框的容器
    filter_frame = tk.Frame(bottom_preview_frame)
    filter_frame.pack(side=tk.TOP, fill=tk.X)

    left_filter_frame = tk.Frame(filter_frame)
    left_filter_frame.pack(side='left', fill=tk.X)

    # 创建筛选字段选择框
    filter_field_label = tk.Label(left_filter_frame, text="筛选字段：")
    filter_field_label.pack(side=tk.LEFT, padx=5, pady=5)

    filter_field_var = tk.StringVar(value="标题")
    filter_field_combobox = ttk.Combobox(left_filter_frame, textvariable=filter_field_var, values=["标题", "标签", "类型"], state='readonly')
    filter_field_combobox.pack(side=tk.LEFT, padx=5, pady=5)

    # 创建关键词输入框
    keyword_label = tk.Label(left_filter_frame, text="关键词：")
    keyword_label.pack(side=tk.LEFT, padx=5, pady=5)

    keyword_var = tk.StringVar()
    keyword_entry = tk.Entry(left_filter_frame, textvariable=keyword_var, width=20)
    keyword_entry.pack(side=tk.LEFT, padx=5, pady=5)

    def apply_current_filter(event=None):
        _ = event
        on_confirm_filter(tree, filter_field_var.get(), keyword_var.get(), df)

    # 创建确认按钮
    confirm_button = tk.Button(filter_frame, text="确认", command=apply_current_filter)
    confirm_button.pack(side=tk.LEFT, padx=5, pady=5)

    reset_filter_button = tk.Button(
        filter_frame,
        text="重置筛选",
        command=lambda: reset_filter(tree, filter_field_var, keyword_var, df),
    )
    reset_filter_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 创建全选按钮
    select_all_button = tk.Button(filter_frame, text="全选", command=lambda: select_all_items(tree))
    select_all_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 定义 keyword_entry 和 keyword_combobox
    app_state.keyword_entry_widget = keyword_entry
    app_state.keyword_combobox_widget = None

    # 定义更新关键词输入框的函数
    def update_keyword_input(*args):
        _ = args
        field = filter_field_var.get()
        keyword_var.set("")
        insert_rows_into_tree(tree, df)

        for widget in left_filter_frame.winfo_children():
            if widget in [app_state.keyword_entry_widget, app_state.keyword_combobox_widget] and widget is not None:
                widget.pack_forget()
                widget.destroy()

        if field in ["标签", "类型"]:
            values = set()
            if field == "标签":
                for tag_list in df["tags"]:
                    if isinstance(tag_list, list):
                        values.update(tag_list)
            else:
                for type_value in df["type"]:
                    normalized_type = normalize_wallpaper_type(type_value)
                    if normalized_type:
                        values.add(normalized_type)
            values = sorted(values)

            app_state.keyword_combobox_widget = ttk.Combobox(left_filter_frame, textvariable=keyword_var, values=values, state='readonly')
            app_state.keyword_combobox_widget.pack(side=tk.LEFT, padx=5, pady=5)
            app_state.keyword_combobox_widget.bind("<<ComboboxSelected>>", apply_current_filter)
        else:
            app_state.keyword_entry_widget = tk.Entry(left_filter_frame, textvariable=keyword_var, width=20)
            app_state.keyword_entry_widget.pack(side=tk.LEFT, padx=5, pady=5)
            app_state.keyword_entry_widget.bind("<Return>", apply_current_filter)

        # 清除选中的项目
        app_state.selected_items.clear()
        set_status(f"筛选字段已切换为{field}，当前共 {len(df)} 项壁纸。")

    # 绑定筛选字段变化事件
    filter_field_var.trace_add("write", update_keyword_input)

    # 创建开始提取按钮
    extract_button = tk.Button(bottom_preview_frame, text="开始提取", command=lambda: extract_wallpapers(df))
    extract_button.pack(side=tk.BOTTOM, padx=5, pady=5)

    return extract_button

def select_all_items(tree):
    """
    将 Treeview 中的所有项目加入 app_state.selected_items 并添加选中标签改变背景颜色。
    
    :param tree: Treeview 对象
    """
    for item in tree.get_children():
        item_values = tree.item(item, "values")
        selected_id = get_tree_item_id(item_values)
        if selected_id not in app_state.selected_items:
            app_state.selected_items.add(selected_id)
            tree.item(item, tags=('selected',))  # 添加选中标签
        
    # 配置选中标签的样式
    tree.tag_configure('selected', background='lightblue')
    update_selection_status(tree)


def reset_filter(tree, filter_field_var, keyword_var, df):
    filter_field_var.set("标题")
    keyword_var.set("")
    insert_rows_into_tree(tree, df)
    app_state.selected_items.clear()
    set_status(f"已重置筛选，显示全部 {len(df)} 项壁纸。")

def on_confirm_filter(tree, field, keyword, df):
    """
    确认筛选按钮点击事件处理函数。
    
    :param tree: Treeview 对象
    :param field: 筛选字段
    :param keyword: 关键词
    :param df: 包含信息的 DataFrame
    """
    keyword = keyword.strip()
    if not keyword:
        insert_rows_into_tree(tree, df)
        app_state.selected_items.clear()
        set_status(build_loaded_status(len(df)))
        return

    field_dict = {"标题": "title", "标签": "tags", "类型": "type"}
    if field not in field_dict:
        messagebox.showwarning("错误", "筛选字段无效")
        set_status("筛选失败：筛选字段无效。")
        return

    if field == "标签":
        tags = set()
        for tag_list in df["tags"]:
            if isinstance(tag_list, list):
                tags.update(tag.lower() for tag in tag_list)
        unique_tags = sorted(set(tag.capitalize() for tag in tags))

        if app_state.keyword_combobox_widget is not None:
            app_state.keyword_combobox_widget['values'] = unique_tags
            app_state.keyword_combobox_widget.pack(side=tk.LEFT, padx=5, pady=5)

        if keyword.lower() not in tags:
            keyword = re.sub(r'[^a-zA-Z0-9\s]', '', keyword)
            if keyword.lower() not in tags:
                messagebox.showwarning("错误", f"标签 '{keyword}' 不存在")
                set_status(f"筛选失败：标签“{keyword}”不存在。")
                return

        filtered_df = df[df["tags"].apply(lambda x: any(tag.lower() == keyword.lower() for tag in x))]
    else:
        filtered_df = df[df[field_dict[field]].astype(str).str.contains(keyword, case=False, na=False)]

    for item in tree.get_children():
        tree.delete(item)
    for new_index, row in enumerate(filtered_df.itertuples(index=False), start=1):
        tree.insert(
            "",
            tk.END,
            values=(
                new_index,
                row.title,
                format_tags_for_display(row.tags),
                normalize_wallpaper_type(row.type),
                format_visibility_for_display(getattr(row, "visibility", "")),
                normalize_wallpaper_id(row.id),
            ),
        )

    # 清除选中的项目
    app_state.selected_items.clear()
    if filtered_df.empty:
        set_status(f"已按{field}筛选“{keyword}”，未匹配到结果。")
    else:
        set_status(build_filter_status(field, keyword, len(filtered_df), len(df)))

def on_right_click(tree, event, df):
    """
    右键点击事件处理函数。
    
    :param tree: Treeview 对象
    :param event: 事件对象
    :param df: 包含信息的 DataFrame
    """
    item = tree.identify_row(event.y)
    if item:
        item_values = tree.item(item, "values")
        selected_id = get_tree_item_id(item_values)

        if not isinstance(selected_id, str) or not selected_id.strip():
            messagebox.showwarning("无效 ID", "选中的项目没有有效的 ID")
            return

        matching_row = find_matching_row(df, selected_id)
        if matching_row is None:
            messagebox.showwarning("未找到匹配项", f"未找到 ID 为 {selected_id} 的项目")
            return

        preview_path = normalize_preview_path(matching_row["preview"])
        if preview_path and os.path.exists(preview_path):
            open_image(preview_path)
        elif not preview_path:
            messagebox.showwarning("预览文件缺失", f"ID 为 {selected_id} 的项目没有预览文件")
        else:
            messagebox.showwarning("文件不存在", f"预览文件路径 {preview_path} 不存在")

def create_notebook_tabs(root):
    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill=tk.BOTH)

    installed_wallpapers_tab = ttk.Frame(notebook)
    settings_tab = ttk.Frame(notebook)
    help_tab = ttk.Frame(notebook)
    about_tab = ttk.Frame(notebook)

    notebook.add(installed_wallpapers_tab, text="已安装壁纸")
    notebook.add(settings_tab, text="设置")
    notebook.add(help_tab, text="帮助")
    notebook.add(about_tab, text="关于")
    return installed_wallpapers_tab, settings_tab, help_tab, about_tab


def create_external_link(parent, text, url):
    link_label = tk.Label(parent, text=text, fg="blue", cursor="hand2", font=("Helvetica", 10, "underline"))

    def open_link(event):
        _ = event
        webbrowser.open_new(url)

    link_label.bind("<Button-1>", open_link)
    return link_label


def create_scrollable_tab_content(tab):
    container = tk.Frame(tab)
    container.pack(expand=True, fill=tk.BOTH)

    canvas = tk.Canvas(container, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    content_frame = tk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)

    def sync_scroll_region(event):
        _ = event
        canvas.configure(scrollregion=canvas.bbox("all"))

    def sync_content_width(event):
        _ = event
        canvas.itemconfigure(window_id, width=canvas.winfo_width())

    content_frame.bind("<Configure>", sync_scroll_region)
    canvas.bind("<Configure>", sync_content_width)
    return content_frame, canvas


def bind_mousewheel_to_page(root_widget, canvas):
    def on_mousewheel(event):
        canvas.yview_scroll(int(-event.delta / 120), "units")

    def bind_widget_tree(widget):
        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        for child in widget.winfo_children():
            bind_widget_tree(child)

    bind_widget_tree(root_widget)


def create_mode_controls(mode_frame, preview_frame, df, root):
    mode_var = tk.StringVar(value="列表模式")

    tk.Radiobutton(
        mode_frame,
        text="列表模式",
        variable=mode_var,
        value="列表模式",
        indicatoron=0,
        command=lambda: toggle_mode(preview_frame, df, mode_var, mode_frame),
    ).pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    tk.Radiobutton(
        mode_frame,
        text="缩略图模式",
        variable=mode_var,
        value="缩略图模式",
        indicatoron=0,
        command=lambda: toggle_mode(preview_frame, df, mode_var, mode_frame),
    ).pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    tk.Button(mode_frame, text="刷新数据", command=lambda: refresh_wallpaper_data(root)).pack(
        side=tk.RIGHT, padx=5, pady=5
    )


def create_settings_tab_content(settings_tab, root, output_path):
    setting_frame, settings_canvas = create_scrollable_tab_content(settings_tab)
    config = load_config()

    top_setting_frame = ttk.LabelFrame(setting_frame, text="steam.exe路径", padding=(10, 10))
    top_setting_frame.pack(fill=tk.X, padx=10, pady=10)

    ttk.Label(
        top_setting_frame,
        text="这里填的是 steam.exe 路径。程序会按这个路径去找 Wallpaper Engine 的本地创意工坊目录。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))

    steam_path = config.steam_path
    steam_path_var = tk.StringVar(value=steam_path)
    steam_path_row = tk.Frame(top_setting_frame)
    steam_path_row.pack(fill=tk.X)
    tk.Entry(steam_path_row, textvariable=steam_path_var, width=50, state="readonly").pack(side=tk.LEFT, padx=5, pady=5)
    tk.Button(steam_path_row, text="更改路径", command=lambda: on_change_path(root, steam_path_var)).pack(
        side=tk.LEFT, padx=5, pady=5
    )

    ttk.Label(
        top_setting_frame,
        text=f"配置文件在 {CONFIG_DISPLAY_PATH}，扫描后的壁纸索引会写到 {INFO_DISPLAY_PATH}。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(6, 0))

    middle_setting_frame = ttk.LabelFrame(setting_frame, text="自定义选项", padding=(10, 10))
    middle_setting_frame.pack(fill=tk.X, padx=10, pady=10)

    ttk.Label(
        middle_setting_frame,
        text="这些选项会直接影响下一次提取。先看输出模式，再决定要不要转换 TEX、复制附带文件和覆盖旧文件。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))

    app_state.not_convert_tex_to_image_var = add_feature_option(
        middle_setting_frame, "不把TEX文件转换为图像", default_value=False
    )
    app_state.use_wallpaper_name_as_subdir_var = add_feature_option(
        middle_setting_frame, "使用壁纸名作为子目录名称而不是壁纸ID", default_value=True
    )
    app_state.copy_project_json_and_preview_var = add_feature_option(
        middle_setting_frame, "复制壁纸目录中的project.json和预览文件到输出目录对应子文件夹", default_value=False
    )
    app_state.overwrite_files_var = add_feature_option(
        middle_setting_frame, "覆盖所有现有文件", default_value=True
    )

    bottom_setting_frame = ttk.LabelFrame(setting_frame, text="输出路径及模式", padding=(10, 10))
    bottom_setting_frame.pack(fill=tk.X, padx=10, pady=10)

    ttk.Label(
        bottom_setting_frame,
        text="先选输出目录，再选输出模式。提取结果是集中放、原地放，还是按壁纸分文件夹，都由这里控制。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))

    output_path_frame = tk.Frame(bottom_setting_frame)
    output_path_frame.pack(side=tk.TOP, fill=tk.X)

    tk.Label(output_path_frame, text="输出路径：").pack(side=tk.LEFT, padx=5, pady=5)

    app_state.output_path_var = tk.StringVar(value=output_path or DEFAULT_OUTPUT_PATH)
    tk.Entry(output_path_frame, textvariable=app_state.output_path_var, width=50).pack(
        side=tk.LEFT, padx=5, pady=5
    )

    tk.Button(output_path_frame, text="选择输出文件夹", command=on_select_output_path).pack(
        side=tk.LEFT, padx=5, pady=5
    )
    tk.Button(
        output_path_frame,
        text="打开输出文件夹",
        command=lambda: open_folder(app_state.output_path_var.get()),
    ).pack(side=tk.LEFT, padx=5, pady=5)

    output_mode_frame = tk.Frame(bottom_setting_frame)
    output_mode_frame.pack(side=tk.TOP, fill=tk.X)

    tk.Label(output_mode_frame, text="输出模式：").pack(side=tk.LEFT, padx=5, pady=5)

    style = ttk.Style()
    style.configure("TCombobox", postoffset=(0, 0, 40, 0))

    app_state.output_mode_var = tk.StringVar(value=SEPARATE_OUTPUT_MODE)
    ttk.Combobox(
        output_mode_frame,
        textvariable=app_state.output_mode_var,
        values=[LOCAL_OUTPUT_MODE, SHARED_OUTPUT_MODE, SEPARATE_OUTPUT_MODE],
        style="TCombobox",
        width=40,
        state="readonly",
    ).pack(side=tk.LEFT, padx=5, pady=5)

    output_mode_description_var = tk.StringVar(value=get_output_mode_description(app_state.output_mode_var.get()))
    ttk.Label(
        bottom_setting_frame,
        textvariable=output_mode_description_var,
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(6, 0))

    batch_workers_frame = tk.Frame(bottom_setting_frame)
    batch_workers_frame.pack(side=tk.TOP, fill=tk.X, pady=(8, 0))

    tk.Label(batch_workers_frame, text="批量提取并发：").pack(side=tk.LEFT, padx=5, pady=5)
    app_state.batch_extract_workers_var = tk.StringVar(value=str(config.batch_extract_workers))
    batch_workers_spinbox = tk.Spinbox(
        batch_workers_frame,
        from_=0,
        to=MAX_BATCH_EXTRACT_WORKERS,
        textvariable=app_state.batch_extract_workers_var,
        width=8,
    )
    batch_workers_spinbox.pack(side=tk.LEFT, padx=5, pady=5)

    batch_workers_description_var = tk.StringVar(
        value=get_batch_extract_workers_description(config.batch_extract_workers)
    )
    ttk.Label(
        bottom_setting_frame,
        textvariable=batch_workers_description_var,
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(4, 0))

    summary_frame = ttk.LabelFrame(setting_frame, text="当前配置摘要", padding=(10, 10))
    summary_frame.pack(fill=tk.X, padx=10, pady=10)
    settings_summary_var = tk.StringVar(
        value=build_settings_summary(
            steam_path_var.get(),
            app_state.output_path_var.get(),
            app_state.output_mode_var.get(),
            config.batch_extract_workers,
        )
    )
    ttk.Label(
        summary_frame,
        textvariable=settings_summary_var,
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=5)

    def get_summary_batch_workers():
        try:
            return parse_batch_extract_workers_input(app_state.batch_extract_workers_var.get())
        except ValueError:
            return load_config().batch_extract_workers

    def handle_output_mode_change(*args):
        _ = args
        on_output_mode_change(read_path_from_file("output_path") or DEFAULT_OUTPUT_PATH)
        output_mode_description_var.set(get_output_mode_description(app_state.output_mode_var.get()))
        settings_summary_var.set(
            build_settings_summary(
                steam_path_var.get(),
                app_state.output_path_var.get(),
                app_state.output_mode_var.get(),
                get_summary_batch_workers(),
            )
        )

    def update_settings_summary(*args):
        _ = args
        settings_summary_var.set(
            build_settings_summary(
                steam_path_var.get(),
                app_state.output_path_var.get(),
                app_state.output_mode_var.get(),
                get_summary_batch_workers(),
            )
        )

    def save_batch_extract_workers(*args):
        _ = args
        try:
            configured_workers = parse_batch_extract_workers_input(app_state.batch_extract_workers_var.get())
        except ValueError as exc:
            messagebox.showwarning("并发设置无效", str(exc))
            app_state.batch_extract_workers_var.set(str(load_config().batch_extract_workers))
            return

        write_config_value("batch_extract_workers", configured_workers)
        normalized_workers = load_config().batch_extract_workers
        app_state.batch_extract_workers_var.set(str(normalized_workers))
        batch_workers_description_var.set(get_batch_extract_workers_description(normalized_workers))
        settings_summary_var.set(
            build_settings_summary(
                steam_path_var.get(),
                app_state.output_path_var.get(),
                app_state.output_mode_var.get(),
                normalized_workers,
            )
        )
        set_status(f"批量提取并发已更新为：{format_batch_extract_workers_display(normalized_workers)}")

    app_state.output_mode_var.trace_add("write", handle_output_mode_change)
    app_state.output_path_var.trace_add("write", update_settings_summary)
    batch_workers_spinbox.configure(command=save_batch_extract_workers)
    batch_workers_spinbox.bind("<FocusOut>", save_batch_extract_workers)
    batch_workers_spinbox.bind("<Return>", save_batch_extract_workers)
    bind_mousewheel_to_page(setting_frame, settings_canvas)


def create_about_tab_content(about_tab):
    content_frame, about_canvas = create_scrollable_tab_content(about_tab)

    about_frame = ttk.LabelFrame(content_frame, text="RePKG_GUI", padding=(10, 10))
    about_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    ttk.Label(
        about_frame,
        text="这是一个给 Wallpaper Engine 本地创意工坊壁纸用的小工具，主要做扫描、筛选、预览和提取。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))
    ttk.Label(about_frame, text=f"版本：{APP_VERSION}").pack(anchor=tk.W, padx=5, pady=5)
    ttk.Label(about_frame, text=f"作者：{APP_AUTHOR}").pack(anchor=tk.W, padx=5, pady=5)

    author_frame = tk.Frame(about_frame)
    author_frame.pack(anchor=tk.W, padx=5, pady=(4, 8))
    ttk.Label(author_frame, text="作者主页：").pack(side=tk.LEFT, padx=0, pady=0)
    create_external_link(author_frame, "CSDN", APP_AUTHOR_URL).pack(side=tk.LEFT, padx=0, pady=0)

    repkg_frame = ttk.LabelFrame(content_frame, text="RePKG 依赖信息", padding=(10, 10))
    repkg_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    ttk.Label(
        repkg_frame,
        text="实际提取靠的是程序发布包内随附的 RePKG.exe，这里放的是当前适配的版本信息。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))
    ttk.Label(repkg_frame, text=f"版本：{REPKG_VERSION}").pack(anchor=tk.W, padx=5, pady=5)
    ttk.Label(repkg_frame, text=f"作者：{REPKG_AUTHOR}").pack(anchor=tk.W, padx=5, pady=5)

    repkg_link_row = tk.Frame(repkg_frame)
    repkg_link_row.pack(anchor=tk.W, padx=5, pady=(4, 0))
    ttk.Label(repkg_link_row, text="项目地址：").pack(side=tk.LEFT, padx=0, pady=0)
    create_external_link(repkg_link_row, REPKG_PROJECT_URL, REPKG_PROJECT_URL).pack(side=tk.LEFT, padx=0, pady=0)

    support_frame = ttk.LabelFrame(content_frame, text="支持作者", padding=(10, 10))
    support_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    ttk.Label(
        support_frame,
        text="点击下方图片可以跳转至收款码页面。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))

    try:
        photo, _, _ = load_resized_photo_image(os.path.join(RESOURCE_ROOT, "nekomusume.png"), 200, 200)
    except (FileNotFoundError, OSError, UnidentifiedImageError) as exc:
        messagebox.showerror("错误", f"无法加载图像：{exc}")
        return

    link = tk.Label(support_frame, image=photo, cursor="hand2")
    link.image = photo
    link.pack(anchor=tk.W, padx=5, pady=5)

    def open_about_image(event):
        _ = event
        webbrowser.open_new(ABOUT_IMAGE_URL)

    link.bind("<Button-1>", open_about_image)
    bind_mousewheel_to_page(content_frame, about_canvas)

def create_help_tab_content(help_tab):
    content_frame, help_canvas = create_scrollable_tab_content(help_tab)

    help_frame = ttk.LabelFrame(content_frame, text="使用帮助", padding=(10, 10))
    help_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    ttk.Label(
        help_frame,
        text=f"下面的说明基于当前界面能力整理，并与 RePKG {REPKG_VERSION} 的使用上下文保持同步。",
        justify=tk.LEFT,
        wraplength=TAB_TEXT_WRAP,
    ).pack(anchor=tk.W, padx=5, pady=(0, 8))

    for section_title, section_lines in build_help_sections():
        section_frame = ttk.LabelFrame(help_frame, text=section_title, padding=(10, 8))
        section_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(
            section_frame,
            text="\n".join(section_lines),
            justify=tk.LEFT,
            wraplength=TAB_TEXT_WRAP,
        ).pack(anchor=tk.W)
    bind_mousewheel_to_page(content_frame, help_canvas)

def create_main_window(df, output_path, root=None, initial_status=None):
    """
    创建并显示主窗口，包含信息表格、标签筛选、路径设置和输出模式选择等功能。

    :param df: 包含信息的 DataFrame
    :param output_path: 输出路径
    """
    app_state.selected_items.clear()
    app_state.current_tree_widget = None
    app_state.current_extract_button = None

    # 创建主窗口
    is_new_root = root is None
    if root is None:
        root = tk.Tk()
    else:
        for widget in root.winfo_children():
            widget.destroy()

    root.title("RePKG_GUI")
    root.geometry("800x600")  # 设置窗口大小
    root.resizable(False, False)  # 禁止调整窗口大小

    installed_wallpapers_tab, settings_tab, help_tab, about_tab = create_notebook_tabs(root)

    # 创建预览框架（已安装壁纸选项卡）
    preview_frame = tk.Frame(installed_wallpapers_tab)
    preview_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    # 创建模式切换框架
    mode_frame = tk.Frame(preview_frame)
    mode_frame.pack(side=tk.TOP, fill=tk.X)

    create_mode_controls(mode_frame, preview_frame, df, root)

    # 创建预览上部框架（信息表格）
    tree = create_top_preview_frame(preview_frame, df)
    app_state.current_tree_widget = tree

    # 创建预览下部框架（标签筛选）
    extract_button = create_bottom_preview_frame(preview_frame, tree, df)
    app_state.current_extract_button = extract_button

    create_settings_tab_content(settings_tab, root, output_path)

    app_state.status_var = tk.StringVar(value=initial_status or build_loaded_status(len(df)))
    status_label = ttk.Label(root, textvariable=app_state.status_var, anchor=tk.W, relief=tk.SUNKEN)
    status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))

    # 强制更新窗口布局
    root.update_idletasks()

    # 确保窗口居中
    center_window(root)

    create_help_tab_content(help_tab)
    create_about_tab_content(about_tab)

    if is_new_root:
        root.mainloop()

    return root

def on_tree_select(tree, event):
    """
    处理 Treeview 的单击事件，实现多选功能，并改变选中行的背景颜色。
    """
    region = tree.identify_region(event.x, event.y)
    if region == "cell":
        item = tree.identify_row(event.y)
        if item:
            item_values = tree.item(item, "values")
            selected_id = get_tree_item_id(item_values)
            if selected_id in app_state.selected_items:
                app_state.selected_items.remove(selected_id)
                tree.selection_remove(item)
                tree.item(item, tags=())  # 移除选中标签
            else:
                app_state.selected_items.add(selected_id)
                tree.selection_add(item)
                tree.item(item, tags=('selected',))  # 添加选中标签

    # 配置选中标签的样式
    tree.tag_configure('selected', background='lightblue')
    update_selection_status(tree)

def extract_wallpapers(df):
    """
    根据当前选择批量提取壁纸。
    """
    if not app_state.selected_items:
        messagebox.showwarning("未选择项目", "请先选择要提取的项目")
        set_status("请先选择至少一个项目后再开始提取。")
        return

    execute_extraction(sorted(app_state.selected_items), df, show_progress=True)

def on_output_mode_change(original_output_path):
    """
    处理输出模式变化。

    :param original_output_path: 原始输出路径
    """
    if app_state.output_mode_var is None or app_state.output_path_var is None:
        return

    mode = app_state.output_mode_var.get()
    if mode == LOCAL_OUTPUT_MODE:
        app_state.output_path_var.set(DEFAULT_OUTPUT_PATH)
    else:
        app_state.output_path_var.set(original_output_path)

    set_status(f"输出模式已切换为：{mode}")

def open_image(file_path):
    # 检查文件是否存在
    if not os.path.exists(file_path):
        messagebox.showerror("错误", "文件不存在！")
        return

    # 检查文件类型
    if not file_path.lower().endswith(('.jpg', '.gif')):
        messagebox.showerror("错误", "不支持的文件类型！仅支持 .jpg 和 .gif 文件。")
        return

    # 创建 Tkinter 窗口
    preview = tk.Toplevel()  # 使用 Toplevel 而不是 Tk，以避免多个主窗口
    preview.title("图像查看器")

    # 获取屏幕宽度和高度
    screen_width = preview.winfo_screenwidth()
    screen_height = preview.winfo_screenheight()

    # 计算最大允许的宽度和高度（屏幕宽度和高度的0.618倍）
    max_width = int(screen_width * 0.618)
    max_height = int(screen_height * 0.618)

    try:
        photo, new_width, new_height = load_resized_photo_image(file_path, max_width, max_height)
    except (FileNotFoundError, OSError, UnidentifiedImageError) as exc:
        messagebox.showerror("错误", f"无法加载图像：{exc}")
        set_status(f"图像查看失败：{exc}")
        return

    # 创建标签显示图像
    label = tk.Label(preview, image=photo)
    label.image = photo  # 保存对图像的引用
    label.pack()

    # 设置窗口大小
    preview.geometry(f"{new_width}x{new_height}")  # 修改为新的宽度和高度

    preview.update_idletasks()  # 强制更新窗口布局
    # 将窗口居中
    center_window(preview)

    set_status(f"已打开预览图：{os.path.basename(file_path)}")

def open_folder(folder_path):
    """
    打开指定的文件夹路径。

    :param folder_path: 文件夹路径
    """
    if not folder_path:
        messagebox.showwarning("打开文件夹失败", "文件夹路径为空")
        set_status("打开文件夹失败：文件夹路径为空。")
        return

    normalized_path = os.path.normpath(folder_path)
    if not os.path.exists(normalized_path):
        messagebox.showwarning("打开文件夹失败", f"文件夹不存在: {normalized_path}")
        set_status(f"打开文件夹失败：{normalized_path} 不存在。")
        return

    try:
        os.startfile(normalized_path)
        set_status(f"已打开文件夹：{normalized_path}")
    except OSError as exc:
        messagebox.showwarning("打开文件夹失败", f"无法打开文件夹: {exc}")
        set_status(f"打开文件夹失败：{exc}")

def on_change_path(root, steam_path_var):
    """
    更改 steam.exe 路径。

    :param root: 窗口根对象
    :param steam_path_var: steam.exe 路径变量
    """
    # 关闭当前根窗口
    root.destroy()

    # 启动GUI让用户手动选择或搜索路径
    select_root = tk.Tk()
    select_root.title("选择 steam.exe 路径")
    select_root.geometry("400x300")  # 设置选择窗口大小
    select_root.resizable(False, False)  # 禁止调整窗口大小

    # 设置圆角窗口
    app = Locate(select_root, on_path_selected, steam_path_var)

    app.root.protocol("WM_DELETE_WINDOW", select_root.destroy)  # 关闭选择窗口时退出应用
    app.root.mainloop()

def on_select_output_path():
    """
    选择输出路径。
    """
    file_path = filedialog.askdirectory()
    if file_path and app_state.output_path_var is not None:
        app_state.output_path_var.set(file_path)
        write_output_path_to_file(file_path)
        set_status(f"输出路径已更新为：{os.path.normpath(file_path)}")


def refresh_wallpaper_data(root):
    set_status("正在刷新壁纸数据...")
    df = load_wallpaper_dataframe()
    if df is None:
        set_status("刷新失败，请检查 steam 路径和创意工坊目录。")
        return

    output_path = read_path_from_file("output_path") or DEFAULT_OUTPUT_PATH
    create_main_window(df, output_path, root=root, initial_status=build_loaded_status(len(df), refreshed=True))

def add_feature_option(frame, feature_name, default_value=False):
    """
    添加功能选项。

    :param frame: 父框架
    :param feature_name: 功能名称
    :param default_value: 默认是否勾选（True 或 False）
    """
    feature_frame = tk.Frame(frame)
    feature_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    feature_var = tk.BooleanVar(value=default_value)

    feature_checkbutton = ttk.Checkbutton(feature_frame, text=feature_name, variable=feature_var)
    feature_checkbutton.pack(side=tk.LEFT, padx=5, pady=5)

    return feature_var  # 返回 BooleanVar 实例以便后续操作

def center_window(root):
    """
    将窗口居中。

    :param root: 窗口根对象
    """
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_width()
    window_height = root.winfo_height()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f'{window_width}x{window_height}+{x}+{y}')

def main():
    """
    主函数，程序入口。
    """
    ensure_config_file()

    # 读取 steam_path 从 config.json 文件
    steam_path = read_path_from_file("steam_path")
    if steam_path:
        df = load_wallpaper_dataframe()
        if df is not None:
            # 读取 output_path 从 config.json 文件
            output_path = read_path_from_file("output_path") or DEFAULT_OUTPUT_PATH
            create_main_window(df, output_path)
    else:
        # 路径无效，启动GUI让用户手动选择或搜索路径
        select_root = tk.Tk()
        select_root.title("选择 steam.exe 路径")
        select_root.geometry("400x300")  # 设置选择窗口大小
        select_root.resizable(False, False)  # 禁止调整窗口大小

        # 设置圆角窗口
        app = Locate(select_root, on_path_selected)

        app.root.protocol("WM_DELETE_WINDOW", select_root.destroy)  # 关闭选择窗口时退出应用
        app.root.mainloop()

        # 如果用户关闭选择窗口而没有选择路径，直接退出应用
        if not read_path_from_file("steam_path"):
            return

def on_path_selected(app, steam_path_var=None):
    """
    处理路径选择结果。

    :param app: Locate 应用实例
    :param steam_path_var: steam.exe 路径变量
    """
    path = app.entry.get()
    if path and path.lower().endswith("steam.exe") and os.path.exists(path):
        try:
            write_config_value("steam_path", path)
            if steam_path_var is not None:
                steam_path_var.set(path)
            app.root.destroy()  # 关闭选择窗口

            df = load_wallpaper_dataframe()
            if df is not None:
                # 读取 output_path
                output_path = read_path_from_file("output_path") or DEFAULT_OUTPUT_PATH
                create_main_window(df, output_path)
        except FileNotFoundError:
            log_error(f"{CONFIG_DISPLAY_PATH} 文件未找到")
        except (OSError, ValueError) as exc:
            log_error(f"写入 {CONFIG_DISPLAY_PATH} 文件时发生错误: {exc}")
            messagebox.showerror("写入文件失败", f"写入文件 {CONFIG_DISPLAY_PATH} 时发生错误: {exc}")
    else:
        messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")

if __name__ == "__main__":
    main()
