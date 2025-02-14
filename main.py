# 导入标准库
import csv
import datetime
import json
import os
import re
import ast
import webbrowser

# 导入第三方库
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# 导入自定义模块
from Locate import Locate

# 定义 selected_items 集合
selected_items = set()

def log_success(message):
    """
    将成功信息写入 logs.txt 文件并包含时间戳。
    :param message: 成功信息
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("logs.txt", "a") as log_file:
            log_file.write(f"{timestamp} - SUCCESS: {message}\n")
    except Exception as e:
        log_error(f"Error logging success: {e}")

def log_error(message):
    """
    将错误信息写入 errors.txt 文件并包含时间戳。

    :param message: 错误信息
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("errors.txt", "a") as log_file:
            log_file.write(f"{timestamp} - {message}\n")
    except Exception as e:
        messagebox.showwarning("日志错误", f"Error logging error: {e}")

def extract_info_to_csv():
    """
    从指定路径提取信息并写入 info.csv 文件。
    """
    # 定义要提取的字段
    fields_to_extract = ["preview", "tags", "title", "type", "id"]  # 增加 id 字段

    # 从 config.json 文件中读取 steam_path
    steam_path = read_path_from_file("steam_path")
    if not steam_path:
        messagebox.showwarning("路径未找到", "config.json 中 steam_path 未找到或无效")
        log_error("config.json 中 steam_path 未找到或无效")
        return

    # 替换路径中的 steam.exe 为 steamapps\workshop\content\431960
    directory = os.path.join(os.path.dirname(steam_path), "steamapps", "workshop", "content", "431960")

    # 检查目录是否存在
    if not os.path.exists(directory):
        messagebox.showwarning("目录不存在", f"目录 {directory} 不存在")
        log_error(f"目录 {directory} 不存在")
        return

    # 存储提取信息的列表
    extracted_info = []

    # 遍历目录中的所有子文件夹
    for foldername in os.listdir(directory):
        folder_path = os.path.join(directory, foldername)
        if os.path.isdir(folder_path):
            # 提取 id 字段
            extracted_data = {"id": foldername}

            # 查找 preview.jpg 或 preview.gif 文件
            preview_file = None
            for filename in os.listdir(folder_path):
                if filename.lower() in ["preview.jpg", "preview.gif"]:
                    preview_file = os.path.join(folder_path, filename)
                    break
            extracted_data["preview"] = preview_file

            # 遍历子文件夹中的所有文件
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(folder_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            data = json.load(file)
                            # 提取所需字段
                            for field in fields_to_extract:
                                if field not in extracted_data:
                                    extracted_data[field] = data.get(field, "None")
                            # 标准化标签和类型字段
                            if extracted_data.get("tags"):
                                extracted_data["tags"] = [tag.capitalize() for tag in extracted_data["tags"]]
                            if extracted_data.get("type"):
                                extracted_data["type"] = extracted_data["type"].capitalize()
                            extracted_info.append(extracted_data)
                    except Exception as e:
                        messagebox.showwarning("读取文件失败", f"读取文件 {file_path} 时发生错误: {e}")
                        log_error(f"读取文件 {file_path} 时发生错误: {e}")

    # 将提取的信息写入当前工作目录下的 info.csv 文件
    csv_file_path = os.path.join(os.getcwd(), "info.csv")
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=fields_to_extract)
            csv_writer.writeheader()
            csv_writer.writerows(extracted_info)
    except Exception as e:
        messagebox.showwarning("写入文件失败", f"写入文件 {csv_file_path} 时发生错误: {e}")
        log_error(f"写入文件 {csv_file_path} 时发生错误: {e}")

def read_path_from_file(key):
    """
    从 config.json 文件中读取指定键的路径，并检查路径是否有效。
    
    :param key: 键名（"steam_path" 或 "output_path"）
    :return: 有效的路径或 None
    """
    try:
        with open("config.json", 'r', encoding='utf-8') as file:
            config = json.load(file)
            path = config.get(key, "")
            if path:
                log_success(f"成功读取路径: {path}")
                return path
            else:
                log_error(f"config.json 中 {key} 内容为空")
                return None
    except FileNotFoundError:
        log_error("config.json 文件未找到")
    except json.JSONDecodeError:
        log_error("config.json 文件格式错误")
    except Exception as e:
        log_error(f"读取 config.json 文件时发生错误: {e}")
    return None
def parse_tags(tags_str):
    """
    解析标签字符串为列表。
    
    :param tags_str: 标签字符串
    :return: 标签列表
    """
    try:
        tags = ast.literal_eval(tags_str)
        if isinstance(tags, list):
            return tags
        else:
            log_error(f"解析标签失败，返回空列表: {tags_str}")
            return []
    except (ValueError, SyntaxError):
        log_error(f"解析标签失败，返回空列表: {tags_str}")
        return []

def read_info_csv(file_path):
    """
    读取 CSV 文件并返回 DataFrame。
    
    :param file_path: CSV 文件路径
    :return: DataFrame 或 None
    """
    try:
        df = pd.read_csv(file_path, converters={'tags': parse_tags, 'type': lambda x: x.capitalize()})
        log_success(f"成功读取 CSV 文件: {file_path}")
        return df
    except FileNotFoundError:
        log_error(f"文件 {file_path} 未找到")
        messagebox.showwarning("文件未找到", f"未找到文件: {file_path}")
    except pd.errors.EmptyDataError:
        log_error(f"文件 {file_path} 为空")
        messagebox.showwarning("文件为空", f"文件 {file_path} 为空")
    except pd.errors.ParserError:
        log_error(f"无法解析文件 {file_path}")
        messagebox.showwarning("解析错误", f"无法解析文件 {file_path}")
    except Exception as e:
        log_error(f"读取文件 {file_path} 时发生错误: {e}")
        messagebox.showwarning("读取文件失败", f"读取文件 {file_path} 时发生错误: {e}")
    return None

def sort_column(tree, col, reverse):
    """
    根据列标题排序树形视图中的数据。
    
    :param tree: Treeview 对象
    :param col: 列名
    :param reverse: 是否反向排序
    """
    try:
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        l.sort(reverse=reverse)

        # 重新排列项
        for index, (val, k) in enumerate(l):
            tree.move(k, '', index)
            tree.set(k, "index", index + 1)  # 更新序号列

        # 切换排序顺序
        tree.heading(col, command=lambda: sort_column(tree, col, not reverse))
        log_success(f"成功排序列: {col}")
    except Exception as e:
        log_error(f"排序列 {col} 时发生错误: {e}")

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
    inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # 绑定鼠标滚轮事件
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
                image = Image.open(preview_path)
                # 缩放图像
                image = image.resize((150, 150), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                label = tk.Label(inner_frame, image=photo)
                label.image = photo  # 保存对图像的引用
                label.grid(row=index // 3, column=index % 3, padx=10, pady=10)
                label.bind("<Button-1>", lambda event, path=preview_path, title=row["title"], id=row["id"]: on_thumbnail_click(right_frame, path, title, id))
                label.bind("<MouseWheel>", on_mousewheel)

                # 记录第一张图片的信息
                if first_preview_path is None:
                    first_preview_path = preview_path
                    first_title = row["title"]
                    first_id = row["id"]
            except Exception as e:
                log_error(f"加载图像 {preview_path} 时发生错误: {e}")

    # 如果有第一张图片，则默认展示
    if first_preview_path:
        on_thumbnail_click(right_frame, first_preview_path, first_title, first_id)

def on_thumbnail_click(right_frame, preview_path, title, id):
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
        image = Image.open(preview_path)
        # 获取原始图像的宽度和高度
        original_width, original_height = image.size
        
        # 计算缩放比例（假设最大宽度为300）
        max_width = 200
        scale_factor = min(max_width / original_width, 1.0)
        
        # 计算新的宽度和高度
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        # 缩放图像
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # 创建 PhotoImage 对象
        photo = ImageTk.PhotoImage(resized_image)
    except Exception as e:
        messagebox.showerror("错误", f"无法加载图像：{e}")
        return

    # 创建标签显示图像
    label = tk.Label(right_frame, image=photo)
    label.image = photo  # 保存对图像的引用
    label.pack(pady=10)

    # 创建标签显示标题（自动换行）
    title_label = tk.Label(right_frame, text=title, wraplength=200, justify="center")
    title_label.pack(pady=10)

    # 创建提取按钮
    extract_button = tk.Button(right_frame, text="提取", command=lambda: extract_wallpaper(id))
    extract_button.pack(pady=5)

    # 创建打开文件夹按钮
    open_folder_button = tk.Button(right_frame, text="打开文件夹", command=lambda: open_folder(os.path.dirname(preview_path)))
    open_folder_button.pack(pady=5)

def extract_wallpaper(id):
    """
    将被点击的预览图对应的壁纸的ID写入oc.txt。

    :param id: 壁纸ID
    """
    try:
        with open("oc.txt", "a") as file:
            file.write(f"{id}\n")
        messagebox.showinfo("提取成功", f"壁纸ID {id} 已成功写入 oc.txt")
        log_success(f"成功提取壁纸ID: {id}")
    except Exception as e:
        messagebox.showerror("提取失败", f"写入 oc.txt 时发生错误: {e}")
        log_error(f"写入 oc.txt 时发生错误: {e}")

def toggle_mode(tree, preview_frame, df, mode_var, mode_frame, extract_button):
    """
    在列表模式和缩略图模式之间切换。
    
    :param tree: Treeview 对象
    :param preview_frame: 预览框架
    :param df: 包含信息的 DataFrame
    :param mode_var: 模式变量
    :param mode_frame: 模式切换框架
    :param extract_button: 开始提取按钮
    """
    mode = mode_var.get()
    if mode == "列表模式":
        # 清除 preview_frame 中除了 mode_frame 之外的所有子组件
        for widget in preview_frame.winfo_children():
            if widget is not mode_frame:
                widget.destroy()

        # 创建 Treeview 对象
        tree = create_top_preview_frame(preview_frame, df, tree)

        # 绑定右键点击事件
        tree.bind("<Button-3>", lambda event: on_right_click(tree, event, df))

        # 重新创建筛选框架
        extract_button = create_bottom_preview_frame(preview_frame, tree, df)

        # 显示开始提取按钮
        extract_button.pack(side=tk.BOTTOM, padx=5, pady=5)

    elif mode == "缩略图模式":
        tree.pack_forget()
        create_thumbnail_mode(preview_frame, df, mode_frame)

        # 隐藏开始提取按钮
        extract_button.pack_forget()

def create_top_preview_frame(preview_frame, df, tree):
    """
    创建预览上部框架（信息表格）。
    
    :param preview_frame: 预览框架
    :param df: 包含信息的 DataFrame
    :param tree: Treeview 对象
    """
    # 创建 Treeview 对象
    tree = ttk.Treeview(preview_frame, columns=("index", "title", "tags", "type", "id"), show='headings', selectmode=tk.EXTENDED)

    # 设置列标题和排序功能
    tree.heading("index", text="序号")
    tree.heading("title", text="标题", command=lambda: sort_column(tree, "title", False))
    tree.heading("tags", text="标签", command=lambda: sort_column(tree, "tags", False))
    tree.heading("type", text="类型", command=lambda: sort_column(tree, "type", False))
    tree.heading("id", text="ID", command=lambda: sort_column(tree, "id", False))

    # 设置列宽度和对齐方式
    tree.column("index", width=50, anchor=tk.CENTER)
    tree.column("title", width=200, anchor=tk.CENTER)
    tree.column("tags", width=80, anchor=tk.CENTER)
    tree.column("type", width=50, anchor=tk.CENTER)
    tree.column("id", width=100, anchor=tk.CENTER)

    # 插入数据到 Treeview
    for index, row in df.iterrows():
        tags = [tag.capitalize() for tag in row["tags"]] if isinstance(row["tags"], list) else []
        type_ = row["type"].capitalize() if isinstance(row["type"], str) else ""
        tree.insert("", tk.END, values=(index + 1, row["title"], tags, type_, row["id"]))

    tree.pack(expand=True, fill=tk.BOTH)

    # 绑定单击事件
    tree.bind("<Button-1>", lambda event: on_tree_select(tree, event))
    tree.bind("<ButtonRelease-1>", on_click)

    return tree

# 定义全局变量
keyword_combobox_widget = None
keyword_entry_widget = None  # 将 keyword_entry_widget 也定义为全局变量

def create_bottom_preview_frame(preview_frame, tree, df):
    """
    创建预览下部框架（标签筛选）。
    
    :param preview_frame: 预览框架
    :param tree: Treeview 对象
    :param df: 包含信息的 DataFrame
    """
    global keyword_combobox_widget, keyword_entry_widget  # 声明为全局变量

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

    # 创建确认按钮
    confirm_button = tk.Button(filter_frame, text="确认", command=lambda: on_confirm_filter(tree, filter_field_var.get(), keyword_var.get(), df))
    confirm_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 创建全选按钮
    select_all_button = tk.Button(filter_frame, text="全选", command=lambda: select_all_items(tree))
    select_all_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 定义 keyword_entry 和 keyword_combobox
    keyword_entry_widget = keyword_entry
    keyword_combobox_widget = None

    # 定义更新关键词输入框的函数
    def update_keyword_input(*args):
        global keyword_entry_widget, keyword_combobox_widget  # 声明为全局变量
        field = filter_field_var.get()
        keyword_var.set("")
        for item in tree.get_children():
            tree.delete(item)
        for index, row in df.iterrows():
            tree.insert("", tk.END, values=(index + 1, row["title"], row["tags"], row["type"], row["id"]))

        for widget in left_filter_frame.winfo_children():
            if widget in [keyword_entry_widget, keyword_combobox_widget] and widget is not None:
                widget.pack_forget()
                widget.destroy()

        if field in ["标签", "类型"]:
            values = set()
            for item in tree.get_children():
                col_index = {"标签": 2, "类型": 3}[field]
                values.add(tree.item(item, "values")[col_index])
            values = sorted(values)

            keyword_combobox_widget = ttk.Combobox(left_filter_frame, textvariable=keyword_var, values=values, state='readonly')
            keyword_combobox_widget.pack(side=tk.LEFT, padx=5, pady=5)
        else:
            keyword_entry_widget = tk.Entry(left_filter_frame, textvariable=keyword_var, width=20)
            keyword_entry_widget.pack(side=tk.LEFT, padx=5, pady=5)

        # 清除选中的项目
        selected_items.clear()

    # 绑定筛选字段变化事件
    filter_field_var.trace_add("write", update_keyword_input)

    # 创建开始提取按钮
    extract_button = tk.Button(bottom_preview_frame, text="开始提取", command=lambda: on_extract_selected_ids(tree))
    extract_button.pack(side=tk.BOTTOM, padx=5, pady=5)

    return extract_button

def select_all_items(tree):
    """
    将 Treeview 中的所有项目加入 selected_items 并添加选中标签改变背景颜色。
    
    :param tree: Treeview 对象
    """
    for item in tree.get_children():
        item_values = tree.item(item, "values")
        selected_id = item_values[4]
        if selected_id not in selected_items:
            selected_items.add(selected_id)
            tree.item(item, tags=('selected',))  # 添加选中标签
        
    # 配置选中标签的样式
    tree.tag_configure('selected', background='lightblue')

def on_confirm_filter(tree, field, keyword, df):
    """
    确认筛选按钮点击事件处理函数。
    
    :param tree: Treeview 对象
    :param field: 筛选字段
    :param keyword: 关键词
    :param df: 包含信息的 DataFrame
    """
    global keyword_combobox_widget  # 声明为全局变量

    if not keyword:
        for item in tree.get_children():
            tree.delete(item)
        for index, row in df.iterrows():
            tree.insert("", tk.END, values=(index + 1, row["title"], row["tags"], row["type"], row["id"]))
        return

    field_dict = {"标题": "title", "标签": "tags", "类型": "type"}
    if field not in field_dict:
        messagebox.showwarning("错误", "筛选字段无效")
        return

    if field == "标签":
        tags = set()
        for tag_list in df["tags"]:
            if isinstance(tag_list, list):
                tags.update(tag.lower() for tag in tag_list)
        unique_tags = sorted(set(tag.capitalize() for tag in tags))

        keyword_combobox_widget['values'] = unique_tags
        keyword_combobox_widget.pack(side=tk.LEFT, padx=5, pady=5)

        if keyword.lower() not in tags:
            keyword = re.sub(r'[^a-zA-Z0-9\s]', '', keyword)
            if keyword.lower() not in tags:
                messagebox.showwarning("错误", f"标签 '{keyword}' 不存在")
                return

        filtered_df = df[df["tags"].apply(lambda x: any(tag.lower() == keyword.lower() for tag in x))]
    else:
        filtered_df = df[df[field_dict[field]].astype(str).str.contains(keyword, case=False, na=False)]

    for item in tree.get_children():
        tree.delete(item)
    for new_index, row in enumerate(filtered_df.itertuples(index=False), start=1):
        tree.insert("", tk.END, values=(new_index, row.title, row.tags, row.type, row.id))

    # 清除选中的项目
    selected_items.clear()

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
        selected_id = item_values[4]

        if not isinstance(selected_id, str) or not selected_id.strip():
            messagebox.showwarning("无效 ID", "选中的项目没有有效的 ID")
            return

        matching_rows = df[df["id"] == int(selected_id)]
        if matching_rows.empty:
            messagebox.showwarning("未找到匹配项", f"未找到 ID 为 {selected_id} 的项目")
            return

        preview_path = matching_rows["preview"].values[0] if not matching_rows["preview"].isna().all() else None
        if preview_path and os.path.exists(preview_path):
            preview_path = preview_path.replace("\\", "/")
            open_image(preview_path)
        elif preview_path is None:
            messagebox.showwarning("预览文件缺失", f"ID 为 {selected_id} 的项目没有预览文件")
        else:
            messagebox.showwarning("文件不存在", f"预览文件路径 {preview_path} 不存在")

def create_main_window(df, output_path):
    """
    创建并显示主窗口，包含信息表格、标签筛选、路径设置和输出模式选择等功能。

    :param df: 包含信息的 DataFrame
    :param output_path: 输出路径
    """
    # 创建主窗口               
    root = tk.Tk()
    root.title("RePKG_GUI")
    root.geometry("800x600")  # 设置窗口大小
    root.resizable(False, False)  # 禁止调整窗口大小

    # 创建 Notebook 作为主容器
    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill=tk.BOTH)

    # 创建“已安装壁纸”选项卡
    installed_wallpapers_tab = ttk.Frame(notebook)
    notebook.add(installed_wallpapers_tab, text="已安装壁纸")

    # 创建“设置”选项卡
    settings_tab = ttk.Frame(notebook)
    notebook.add(settings_tab, text="设置")

    # 创建“帮助”选项卡
    help_tab = ttk.Frame(notebook)
    notebook.add(help_tab, text="帮助")

    # 创建“关于”选项卡
    about_tab = ttk.Frame(notebook)
    notebook.add(about_tab, text="关于")

    # 创建预览框架（已安装壁纸选项卡）
    preview_frame = tk.Frame(installed_wallpapers_tab)
    preview_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    # 创建模式切换框架
    mode_frame = tk.Frame(preview_frame)
    mode_frame.pack(side=tk.TOP, fill=tk.X)

    # 创建模式变量
    mode_var = tk.StringVar(value="列表模式")

    # 创建模式切换按钮
    list_mode_button = tk.Radiobutton(mode_frame, text="列表模式", variable=mode_var, value="列表模式", indicatoron=0, command=lambda: toggle_mode(tree, preview_frame, df, mode_var, mode_frame, extract_button))
    list_mode_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    thumbnail_mode_button = tk.Radiobutton(mode_frame, text="缩略图模式", variable=mode_var, value="缩略图模式", indicatoron=0, command=lambda: toggle_mode(tree, preview_frame, df, mode_var, mode_frame, extract_button))
    thumbnail_mode_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    # 创建 Treeview 对象
    tree = ttk.Treeview(preview_frame, columns=("index", "title", "tags", "type", "id"), show='headings', selectmode=tk.EXTENDED)

    # 创建预览上部框架（信息表格）
    tree = create_top_preview_frame(preview_frame, df, tree)

    # 创建预览下部框架（标签筛选）
    extract_button = create_bottom_preview_frame(preview_frame, tree, df)

    # 创建设置框架（设置选项卡）
    setting_frame = tk.Frame(settings_tab)
    setting_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

    # 创建设置上部框架（steam.exe 路径设置）
    top_setting_frame = ttk.LabelFrame(setting_frame, text="steam.exe路径", padding=(10, 10))
    top_setting_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    steam_path = read_path_from_file("steam_path")
    steam_path_var = tk.StringVar(value=steam_path)
    steam_path_entry = tk.Entry(top_setting_frame, textvariable=steam_path_var, width=50)
    steam_path_entry.pack(side=tk.LEFT, padx=5, pady=5)

    change_path_button = tk.Button(top_setting_frame, text="更改路径", command=lambda: on_change_path(root, steam_path_var))
    change_path_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 创建设置中部框架（功能选项）
    middle_setting_frame = ttk.LabelFrame(setting_frame, text="自定义选项", padding=(10, 10))  # 更改为 LabelFrame
    middle_setting_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # 添加功能选项
    extract_info_var = add_feature_option(middle_setting_frame, "不把TEX文件转换为图像", default_value=False)
    clear_cache_var = add_feature_option(middle_setting_frame, "使用壁纸名作为子目录名称而不是壁纸ID", default_value=True)
    copyright_var = add_feature_option(middle_setting_frame, "复制壁纸目录中的project.json和预览文件到输出目录对应子文件夹", default_value=False)
    # single_folder_var = add_feature_option(middle_setting_frame, "忽略现有目录结构将所有文件放在同一目录", default_value=False)
    overwrite_var = add_feature_option(middle_setting_frame, "覆盖所有现有文件", default_value=True)

    # 创建设置下部框架（输出路径和输出模式选择）
    bottom_setting_frame = ttk.LabelFrame(setting_frame, text="输出路径及模式", padding=(10, 10))  # 更改为 LabelFrame
    bottom_setting_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # 创建输出路径控件
    output_path_frame = tk.Frame(bottom_setting_frame)
    output_path_frame.pack(side=tk.TOP, fill=tk.X)

    output_path_label = tk.Label(output_path_frame, text="输出路径：")
    output_path_label.pack(side=tk.LEFT, padx=5, pady=5)

    output_path_var = tk.StringVar(value=output_path)
    output_path_entry = tk.Entry(output_path_frame, textvariable=output_path_var, width=50)
    output_path_entry.pack(side=tk.LEFT, padx=5, pady=5)

    select_output_button = tk.Button(output_path_frame, text="选择输出文件夹", command=lambda: on_select_output_path(output_path_var))
    select_output_button.pack(side=tk.LEFT, padx=5, pady=5)

    open_output_folder_button = tk.Button(output_path_frame, text="打开输出文件夹", command=lambda: open_folder(output_path_var.get()))
    open_output_folder_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 创建输出模式控件
    output_mode_frame = tk.Frame(bottom_setting_frame)
    output_mode_frame.pack(side=tk.TOP, fill=tk.X)

    output_mode_label = tk.Label(output_mode_frame, text="输出模式：")
    output_mode_label.pack(side=tk.LEFT, padx=5, pady=5)

    style = ttk.Style()
    style.configure('TCombobox', postoffset=(0, 0, 40, 0))

    output_mode_var = tk.StringVar(value="在指定文件夹中输出至单独的文件夹")
    output_mode_combobox = ttk.Combobox(output_mode_frame, textvariable=output_mode_var, values=["分别输出至源文件所在文件夹", "在指定文件夹中集中输出", "在指定文件夹中输出至单独的文件夹"], style='TCombobox', width=40)
    output_mode_combobox.pack(side=tk.LEFT, padx=5, pady=5)

    output_mode_var.trace_add("write", lambda *args: on_output_mode_change(output_mode_var, output_path_var, read_path_from_file("output_path")))

    # 强制更新窗口布局
    root.update_idletasks()

    # 确保窗口居中
    center_window(root)

    # 创建RePKG_GUI信息框架
    about_frame = ttk.LabelFrame(about_tab, text="RePKG_GUI", padding=(10, 10))
    about_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # 设置字体样式
    bold_font = ("Helvetica", 10, "normal")

    # 添加版本信息
    version_label = ttk.Label(about_frame, text="版本: 1.0.0", font=bold_font)
    version_label.pack(anchor=tk.W, padx=5, pady=5)

    # 添加作者信息
    author_label = ttk.Label(about_frame, text="作者: FLmhp", font=bold_font)
    author_label.pack(anchor=tk.W, padx=5, pady=5)

    # 添加基于项目信息
    based_on_label = ttk.Label(about_tab, text="本项目基于 RePKG 开发")
    based_on_label.pack(anchor=tk.W, padx=5, pady=5)

    # 创建 RePKG 信息框架
    base_frame = ttk.LabelFrame(about_tab, text="RePKG", padding=(10, 10))
    base_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # 添加 RePKG 版本信息
    repkg_version_label = ttk.Label(base_frame, text="版本: 0.3.2", font=bold_font)
    repkg_version_label.pack(anchor=tk.W, padx=5, pady=5)

    # 添加 RePKG 作者信息
    repkg_author_label = ttk.Label(base_frame, text="作者: notscuffed", font=bold_font)
    repkg_author_label.pack(anchor=tk.W, padx=5, pady=5)

    # 创建一个新的 Frame 来包含 follow_author_label 和 csdn_label
    author_frame = tk.Frame(about_frame)
    author_frame.pack(anchor=tk.W, padx=5, pady=5)

    # 添加关注作者标签
    follow_author_label = ttk.Label(author_frame, text="关注作者：", font=bold_font)
    follow_author_label.pack(side=tk.LEFT, padx=0, pady=0)

    # 创建超链接标签
    csdn_label = tk.Label(author_frame, text="CSDN", fg="blue", cursor="hand2", font=("Helvetica", 10, "underline"))
    csdn_label.pack(side=tk.LEFT, padx=0, pady=0)
    csdn_label.bind("<Button-1>", lambda event: webbrowser.open_new("https://blog.csdn.net/flMHP?spm=1010.2135.3001.5343"))  # 替换为实际的URL

    # 加载图片并缩放
    try:
        image = Image.open("nekomusume.png")
        # 缩放图像
        image = image.resize((200, 200), Image.LANCZOS)  # 根据需要调整大小
        photo = ImageTk.PhotoImage(image)
    except Exception as e:
        messagebox.showerror("错误", f"无法加载图像：{e}")
        photo = None

    if photo:
        # 创建Label以显示图片
        link = tk.Label(about_frame, image=photo, cursor="hand2")
        link.image = photo  # 保存对图像的引用
        link.pack(side=tk.BOTTOM, anchor=tk.SE, padx=5, pady=5)

        # 绑定点击事件
        link.bind("<Button-1>", lambda event: webbrowser.open_new("https://i.postimg.cc/Kc92tL7f/MEITU-20250210-165522349.jpg"))  # 替换为实际的URL

    root.mainloop()

def on_tree_select(tree, event):
    """
    处理 Treeview 的单击事件，实现多选功能，并改变选中行的背景颜色。
    """
    region = tree.identify_region(event.x, event.y)
    if region == "cell":
        item = tree.identify_row(event.y)
        if item:
            item_values = tree.item(item, "values")
            selected_id = item_values[4]
            if selected_id in selected_items:
                selected_items.remove(selected_id)
                tree.selection_remove(item)
                tree.item(item, tags=())  # 移除选中标签
            else:
                selected_items.add(selected_id)
                tree.selection_add(item)
                tree.item(item, tags=('selected',))  # 添加选中标签

    # 配置选中标签的样式
    tree.tag_configure('selected', background='lightblue')

def on_extract_selected_ids(tree):
    """
    将选中的项目 ID 写入 choices.txt 文件。
    """
    if not selected_items:
        messagebox.showwarning("未选择项目", "请先选择要提取的项目")
        return

    try:
        with open("choices.txt", "w") as file:
            for item_id in selected_items:
                file.write(f"{item_id}\n")
        messagebox.showinfo("提取成功", "选中的项目 ID 已成功写入 choices.txt")
        log_success("成功提取选中的项目 ID")
    except Exception as e:
        messagebox.showerror("提取失败", f"写入 choices.txt 时发生错误: {e}")
        log_error(f"写入 choices.txt 时发生错误: {e}")

def on_output_mode_change(output_mode_var, output_path_var, original_output_path):
    """
    处理输出模式变化。

    :param output_mode_var: 输出模式变量
    :param output_path_var: 输出路径变量
    :param original_output_path: 原始输出路径
    """
    mode = output_mode_var.get()
    if mode == "分别输出至源文件所在文件夹":
        output_path_var.set("./output")
    else:
        output_path_var.set(original_output_path)

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
        # 加载图像
        image = Image.open(file_path)
        
        # 获取原始图像的宽度和高度
        original_width, original_height = image.size
        
        # 计算缩放比例
        scale_factor = min(max_width / original_width, max_height / original_height)
        
        # 计算新的宽度和高度
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        # 缩放图像
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # 创建 PhotoImage 对象
        photo = ImageTk.PhotoImage(resized_image)
    except Exception as e:
        messagebox.showerror("错误", f"无法加载图像：{e}")
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

    # 运行 Tkinter 主循环
    preview.mainloop()

def open_folder(folder_path):
    """
    打开指定的文件夹路径。

    :param folder_path: 文件夹路径
    """
    if folder_path:
        try:
            os.startfile(folder_path)  # Windows
        except AttributeError:
            try:
                os.system(f'open "{folder_path}"')  # macOS
            except:
                try:
                    os.system(f'xdg-open "{folder_path}"')  # Linux
                except Exception as e:
                    messagebox.showwarning("打开文件夹失败", f"无法打开文件夹: {e}")

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

def on_select_output_path(output_path_var):
    """
    选择输出路径。

    :param output_path_var: 输出路径变量
    """
    file_path = filedialog.askdirectory()
    if file_path:
        output_path_var.set(file_path)
        write_output_path_to_file(file_path)

def write_output_path_to_file(output_path):
    """
    将输出路径写入 config.json 文件。

    :param output_path: 输出路径
    """
    try:
        with open("config.json", "r+", encoding='utf-8') as file:
            config = json.load(file)
            config["output_path"] = output_path
            file.seek(0)
            json.dump(config, file, indent=4)
            file.truncate()
        log_success(f"成功写入路径: {output_path}")
    except FileNotFoundError:
        log_error("config.json 文件未找到")
    except json.JSONDecodeError:
        log_error("config.json 文件格式错误")
    except Exception as e:
        log_error(f"写入 config.json 文件时发生错误: {e}")
        messagebox.showwarning("写入文件失败", f"写入文件 config.json 时发生错误: {e}")

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
    # 检查 config.json 文件是否存在，如果不存在则创建默认文件
    if not os.path.exists("config.json"):
        default_config = {
            "steam_path": "",
            "output_path": "./output"
        }
        with open("config.json", "w", encoding='utf-8') as file:
            json.dump(default_config, file, indent=4)

    # 读取 steam_path 从 config.json 文件
    steam_path = read_path_from_file("steam_path")
    if steam_path:
        # 路径有效，写入、读取并展示 info.csv
        extract_info_to_csv()
        df = read_info_csv("info.csv")
        if df is not None:
            # 读取 output_path 从 config.json 文件
            output_path = read_path_from_file("output_path")
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
            with open("config.json", "r+", encoding='utf-8') as file:
                config = json.load(file)
                config["steam_path"] = path
                file.seek(0)
                json.dump(config, file, indent=4)
                file.truncate()
            if steam_path_var is not None:
                steam_path_var.set(path)
            app.root.destroy()  # 关闭选择窗口

            # 写入 info.csv
            extract_info_to_csv()

            # 读取 info.csv 并展示
            df = read_info_csv("info.csv")
            if df is not None:
                # 读取 output_path
                output_path = read_path_from_file("output_path")
                create_main_window(df, output_path)
        except FileNotFoundError:
            log_error("config.json 文件未找到")
        except json.JSONDecodeError:
            log_error("config.json 文件格式错误")
        except Exception as e:
            log_error(f"写入 config.json 文件时发生错误: {e}")
            messagebox.showerror("写入文件失败", f"写入文件 config.json 时发生错误: {e}")
    else:
        messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")

if __name__ == "__main__":
    main()