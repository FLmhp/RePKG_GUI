# 导入标准库
import csv
import datetime
import json
import os
import ast

# 导入第三方库
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# 导入自定义模块
from LocateWE import LocateWE

# 定义 selected_items 集合
selected_items = set()

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

    # 读取 steam_path.txt 文件中的路径
    try:
        with open("steam_path.txt", 'r', encoding='utf-8') as path_file:
            steam_path = path_file.read().strip()
    except FileNotFoundError:
        messagebox.showwarning("文件未找到", "steam_path.txt 文件未找到")
        log_error("steam_path.txt 文件未找到")
        return
    except Exception as e:
        messagebox.showwarning("读取文件失败", f"读取 steam_path.txt 文件时发生错误: {e}")
        log_error(f"读取 steam_path.txt 文件时发生错误: {e}")
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
                                    extracted_data[field] = data.get(field, None)
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

def read_path_from_file(file_path):
    """
    从文件中读取路径，并检查路径是否有效。

    :param file_path: 文件路径
    :return: 有效的路径或 None
    """
    try:
        with open(file_path, 'r') as file:
            path = file.read().strip()
            return path
    except FileNotFoundError:
        pass
    return None

def parse_tags(tags_str):
    try:
        tags = ast.literal_eval(tags_str)
        return tags  # 返回原始标签列表
    except (ValueError, SyntaxError):
        return []

def read_info_csv(file_path):
    """
    读取 CSV 文件并返回 DataFrame。

    :param file_path: CSV 文件路径
    :return: DataFrame 或 None
    """
    try:
        df = pd.read_csv(file_path, converters={'tags': parse_tags, 'type': lambda x: x.capitalize()})
        # 标准化标签字段
        df['tags'] = df['tags'].apply(lambda tags: [tag.capitalize() for tag in tags] if isinstance(tags, list) else [])
        return df
    except FileNotFoundError:
        messagebox.showwarning("文件未找到", f"未找到文件: {file_path}")
    except pd.errors.EmptyDataError:
        messagebox.showwarning("文件为空", f"文件 {file_path} 为空")
    except pd.errors.ParserError:
        messagebox.showwarning("解析错误", f"无法解析文件 {file_path}")
    return None

def sort_column(tree, col, reverse):
    """
    根据列标题排序树形视图中的数据。

    :param tree: Treeview 对象
    :param col: 列名
    :param reverse: 是否反向排序
    """
    l = [(tree.set(k, col), k) for k in tree.get_children('')]
    l.sort(reverse=reverse)

    # 重新排列项
    for index, (val, k) in enumerate(l):
        tree.move(k, '', index)
        tree.set(k, "index", index + 1)  # 更新序号列

    # 切换排序顺序
    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

def create_main_window(df, output_path):
    root = tk.Tk()
    root.title("RePKG_GUI")
    root.geometry("1200x600")  # 设置窗口大小
    root.resizable(False, False)  # 禁止调整窗口大小

    # 创建主框架
    main_frame = tk.Frame(root)
    main_frame.pack(expand=True, fill=tk.BOTH)

    # 左侧区域：信息表格和标签筛选
    left_frame = tk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    # 左侧上区域：信息表格
    top_left_frame = tk.Frame(left_frame)
    top_left_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

    # 创建 Treeview 对象
    tree = ttk.Treeview(top_left_frame, columns=("index", "title", "tags", "type", "id"), show='headings')

    # 设置列标题和对齐方式
    tree.heading("index", text="序号")
    tree.heading("title", text="标题", command=lambda: sort_column(tree, "title", False))
    tree.heading("tags", text="标签", command=lambda: sort_column(tree, "tags", False))
    tree.heading("type", text="类型", command=lambda: sort_column(tree, "type", False))
    tree.heading("id", text="ID", command=lambda: sort_column(tree, "id", False))

    # 设置列的宽度和对齐方式
    tree.column("index", width=50, anchor=tk.CENTER)
    tree.column("title", width=200, anchor=tk.CENTER)
    tree.column("tags", width=80, anchor=tk.CENTER)
    tree.column("type", width=50, anchor=tk.CENTER)
    tree.column("id", width=100, anchor=tk.CENTER)

    # 添加序号列和 id 列
    for index, row in df.iterrows():
        # 标准化标签和类型字段
        tags = [tag.capitalize() for tag in row["tags"]] if isinstance(row["tags"], list) else []
        type_ = row["type"].capitalize() if isinstance(row["type"], str) else ""
        tree.insert("", tk.END, values=(index + 1, row["title"], tags, type_, row["id"]))

    tree.pack(expand=True, fill=tk.BOTH)

    # 左侧下区域：标签筛选
    bottom_left_frame = tk.Frame(left_frame)
    bottom_left_frame.pack(side=tk.BOTTOM, fill=tk.X)

    # 筛选字段选择框
    filter_field_label = tk.Label(bottom_left_frame, text="筛选字段：")
    filter_field_label.pack(side=tk.LEFT, padx=5, pady=5)

    filter_field_var = tk.StringVar(value="标题")
    filter_field_combobox = ttk.Combobox(bottom_left_frame, textvariable=filter_field_var, values=["标题", "标签", "类型"], state='readonly')
    filter_field_combobox.pack(side=tk.LEFT, padx=5, pady=5)

    # 关键词输入框
    keyword_label = tk.Label(bottom_left_frame, text="关键词：")
    keyword_label.pack(side=tk.LEFT, padx=5, pady=5)

    # 初始化关键词输入框为 Entry
    keyword_var = tk.StringVar()
    keyword_entry = tk.Entry(bottom_left_frame, textvariable=keyword_var, width=20)
    keyword_entry.pack(side=tk.LEFT, padx=5, pady=5)

    # 确认按钮
    confirm_button = tk.Button(bottom_left_frame, text="确认", command=lambda: on_confirm_filter(tree, filter_field_var.get(), keyword_var.get(), df))
    confirm_button.pack(side=tk.RIGHT, padx=5, pady=5)  # 确保确认按钮始终在最右侧

    # 预先定义 keyword_entry 和 keyword_combobox
    keyword_entry_widget = keyword_entry
    keyword_combobox_widget = None

    def update_keyword_input(*args):
        nonlocal keyword_entry_widget, keyword_combobox_widget  # 在函数开始时声明 nonlocal
        field = filter_field_var.get()
        
        # 清空关键字输入框
        keyword_var.set("")
        
        # 恢复原始数据
        for item in tree.get_children():
            tree.delete(item)
        for index, row in df.iterrows():
            tree.insert("", tk.END, values=(index + 1, row["title"], row["tags"], row["type"], row["id"]))
        
        # 销毁之前的控件
        for widget in bottom_left_frame.winfo_children():
            if widget in [keyword_entry_widget, keyword_combobox_widget]:
                widget.pack_forget()
                widget.destroy()
    
        if field in ["标签", "类型"]:
            # 获取当前 Treeview 中该字段的所有可能值
            values = set()
            for item in tree.get_children():
                col_index = {"标签": 2, "类型": 3}[field]
                if field == "标签":
                    tag_list = tree.item(item, "values")[col_index]
                    if isinstance(tag_list, list):
                        values.update(tag.lower() for tag in tag_list)
                else:
                    values.add(tree.item(item, "values")[col_index])
            values = sorted(set(tag.capitalize() for tag in values))  # 去重并转换为首字母大写
    
            # 创建新的 Combobox
            keyword_combobox_widget = ttk.Combobox(bottom_left_frame, textvariable=keyword_var, values=values, state='readonly')
            keyword_combobox_widget.pack(side=tk.LEFT, padx=5, pady=5)
            # 移除自动筛选的绑定
            # keyword_combobox_widget.bind("<<ComboboxSelected>>", lambda event: confirm_button.invoke())
        else:
            # 创建新的 Entry
            keyword_entry_widget = tk.Entry(bottom_left_frame, textvariable=keyword_var, width=20)
            keyword_entry_widget.pack(side=tk.LEFT, padx=5, pady=5)

    # 绑定筛选字段的 Combobox 的变化事件
    filter_field_var.trace_add("write", update_keyword_input)

    # 右侧区域
    right_frame = tk.Frame(main_frame)
    right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

    # 右侧上区域：显示 steam.exe 位置和更改其位置的按钮
    top_right_frame = tk.Frame(right_frame)
    top_right_frame.pack(side=tk.TOP, fill=tk.X)

    steam_path_label = tk.Label(top_right_frame, text="steam.exe路径：")
    steam_path_label.pack(side=tk.LEFT, padx=5, pady=5)

    steam_path = read_path_from_file("steam_path.txt")
    steam_path_var = tk.StringVar(value=steam_path)
    steam_path_entry = tk.Entry(top_right_frame, textvariable=steam_path_var, width=50)
    steam_path_entry.pack(side=tk.LEFT, padx=5, pady=5)

    change_path_button = tk.Button(top_right_frame, text="更改路径", command=lambda: on_change_path(root, steam_path_var))
    change_path_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 右侧中区域：选择输出路径和输出模式
    middle_right_frame = tk.Frame(right_frame)
    middle_right_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # 输出路径的控件在同一行
    output_path_frame = tk.Frame(middle_right_frame)
    output_path_frame.pack(side=tk.TOP, fill=tk.X)

    output_path_label = tk.Label(output_path_frame, text="输出路径：")
    output_path_label.pack(side=tk.LEFT, padx=5, pady=5)

    output_path_var = tk.StringVar(value=output_path)
    output_path_entry = tk.Entry(output_path_frame, textvariable=output_path_var, width=50)
    output_path_entry.pack(side=tk.LEFT, padx=5, pady=5)

    select_output_button = tk.Button(output_path_frame, text="选择输出文件夹", command=lambda: on_select_output_path(output_path_var))
    select_output_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 打开输出文件夹按钮
    open_output_folder_button = tk.Button(output_path_frame, text="打开输出文件夹", command=lambda: open_folder(output_path_var.get()))
    open_output_folder_button.pack(side=tk.LEFT, padx=5, pady=5)

    # 输出模式的控件在同一行
    output_mode_frame = tk.Frame(middle_right_frame)
    output_mode_frame.pack(side=tk.TOP, fill=tk.X)

    output_mode_label = tk.Label(output_mode_frame, text="输出模式：")
    output_mode_label.pack(side=tk.LEFT, padx=5, pady=5)

    # 创建样式对象
    style = ttk.Style()
    style.configure('TCombobox', postoffset=(0, 0, 40,0))  # 增加下拉框的宽度

    output_mode_var = tk.StringVar(value="在指定文件夹中输出至单独的文件夹")
    output_mode_combobox = ttk.Combobox(output_mode_frame, textvariable=output_mode_var, values=["分别输出至源文件所在文件夹", "在指定文件夹中集中输出", "在指定文件夹中输出至单独的文件夹"], style='TCombobox', width=40)
    output_mode_combobox.pack(side=tk.LEFT, padx=5, pady=5)

    # 监听 output_mode_combobox 的变化
    output_mode_var.trace_add("write", lambda *args: on_output_mode_change(output_mode_var, output_path_var, read_path_from_file("output_path.txt")))

    # 右侧下区域：功能选项
    bottom_right_frame = tk.Frame(right_frame)
    bottom_right_frame.pack(side=tk.BOTTOM, fill=tk.X)

    # 添加功能选项
    add_feature_option(bottom_right_frame, "提取信息", ["启用", "禁用"], default_value="启用")
    add_feature_option(bottom_right_frame, "清理缓存", ["启用", "禁用"], default_value="禁用")

    # 定义事件处理函数并传递 df 参数
    def on_row_click(tree, event, df):
        """
        处理行单击事件，切换选中状态并改变背景颜色。
        """
        item = tree.identify_row(event.y)
        if item:
            if item in selected_items:
                tree.item(item, tags=())
                selected_items.remove(item)
            else:
                tree.item(item, tags=("selected",))
                selected_items.add(item)

    def on_right_click(tree, event, df):
        """
        处理右键单击事件，打开预览文件。
        """
        item = tree.identify_row(event.y)
        if item:
            item_values = tree.item(item, "values")
            selected_id = item_values[4]  # 使用 Treeview 中的 id 列

            # 确保 selected_id 是有效的字符串
            if not isinstance(selected_id, str) or not selected_id.strip():
                messagebox.showwarning("无效 ID", "选中的项目没有有效的 ID")
                return

            # 检查 df 中是否存在该 id
            matching_rows = df[df["id"] == int(selected_id)]
            if matching_rows.empty:
                messagebox.showwarning("未找到匹配项", f"未找到 ID 为 {selected_id} 的项目")
                return

            preview_path = matching_rows["preview"].values[0] if not matching_rows["preview"].isna().all() else None
            if preview_path and os.path.exists(preview_path):
                preview_path = preview_path.replace("\\", "/")  # 确保路径使用 Unix 风格
                open_image(preview_path)
            elif preview_path is None:
                messagebox.showwarning("预览文件缺失", f"ID 为 {selected_id} 的项目没有预览文件")
            else:
                messagebox.showwarning("文件不存在", f"预览文件路径 {preview_path} 不存在")

    def on_confirm_filter(tree, field, keyword, df):
        """
        处理确认按钮点击事件，根据筛选字段和关键词更新 Treeview 数据。
        """
        if not keyword:
            # 如果关键词为空，恢复原始数据
            for item in tree.get_children():
                tree.delete(item)
            for index, row in df.iterrows():
                tree.insert("", tk.END, values=(index + 1, row["title"], row["tags"], row["type"], row["id"]))
            return

        # 根据筛选字段和关键词过滤数据
        field_dict = {"标题": "title", "标签": "tags", "类型": "type"}
        if field not in field_dict:
            messagebox.showwarning("错误", "筛选字段无效")
            return

        if field == "标签":
            # 对标签进行标准化处理
            tags = set()
            for tag_list in df["tags"]:
                if isinstance(tag_list, list):
                    tags.update(tag.lower() for tag in tag_list)
            unique_tags = sorted(set(tag.capitalize() for tag in tags))  # 去重并转换为首字母大写

            # 更新 Combobox 选项
            keyword_combobox_widget['values'] = unique_tags
            keyword_combobox_widget.pack(side=tk.LEFT, padx=5, pady=5)

            # 检查关键词是否在标准化后的标签中
            if keyword.lower() not in tags:
                messagebox.showwarning("错误", f"标签 '{keyword}' 不存在")
                return

            # 过滤数据
            filtered_df = df[df["tags"].apply(lambda x: any(tag.lower() == keyword.lower() for tag in x))]
        else:
            # 其他字段的过滤逻辑
            filtered_df = df[df[field_dict[field]].astype(str).str.contains(keyword, case=False, na=False)]

        # 更新 Treeview 数据
        for item in tree.get_children():
            tree.delete(item)
        for new_index, row in enumerate(filtered_df.itertuples(index=False), start=1):
            tree.insert("", tk.END, values=(new_index, row.title, row.tags, row.type, row.id))

    # 绑定事件并传递 df 参数
    tree.bind("<Button-1>", lambda event: on_row_click(tree, event, df))
    tree.bind("<Button-3>", lambda event: on_right_click(tree, event, df))

    # 强制更新窗口布局
    root.update_idletasks()

    # 确保窗口居中
    center_window(root)

    root.mainloop()

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

    # 加载图像
    try:
        image = Image.open(file_path)
        photo = ImageTk.PhotoImage(image)
    except Exception as e:
        messagebox.showerror("错误", f"无法加载图像：{e}")
        return

    # 创建标签显示图像
    label = tk.Label(preview, image=photo)
    label.image = photo  # 保存对图像的引用
    label.pack()

    # 设置窗口大小
    preview.geometry(f"{image.width}x{image.height}")  # 修改为属性访问

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
    app = LocateWE(select_root, on_path_selected, steam_path_var)

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
    将输出路径写入 output_path.txt 文件。

    :param output_path: 输出路径
    """
    try:
        with open("output_path.txt", "w") as file:
            file.write(output_path)
    except Exception as e:
        messagebox.showwarning("写入文件失败", f"写入文件 output_path.txt 时发生错误: {e}")
        log_error(f"写入文件 output_path.txt 时发生错误: {e}")

def add_feature_option(frame, feature_name, options, default_value=None):
    """
    添加功能选项。

    :param frame: 父框架
    :param feature_name: 功能名称
    :param options: 选项列表
    :param default_value: 默认值
    :return: Combobox 实例
    """
    feature_frame = tk.Frame(frame)
    feature_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    feature_label = tk.Label(feature_frame, text=feature_name)
    feature_label.pack(side=tk.LEFT, padx=5, pady=5)

    # 确保默认值是选项之一
    if default_value is not None and default_value not in options:
        options.append(default_value)

    feature_var = tk.StringVar()
    feature_combobox = ttk.Combobox(feature_frame, textvariable=feature_var, values=options, state='readonly')
    feature_combobox.pack(side=tk.LEFT, padx=5, pady=5)

    # 延迟设置默认值
    def set_default_after_init():
        if default_value:
            feature_combobox.set(default_value)
        else:
            feature_combobox.set(options[0] if options else "")

    feature_combobox.after(100, set_default_after_init)

    return feature_combobox  # 返回 Combobox 实例以便后续操作

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
    # 读取 steam_path.txt 文件中的路径
    path = read_path_from_file("steam_path.txt")
    if path:
        # 路径有效，写入、读取并展示 info.csv
        extract_info_to_csv()
        df = read_info_csv("info.csv")
        if df is not None:
            # 读取 output_path.txt 文件中的路径
            output_path = read_path_from_file("output_path.txt")
            create_main_window(df, output_path)
    else:
        # 路径无效，启动GUI让用户手动选择或搜索路径
        select_root = tk.Tk()
        select_root.title("选择 steam.exe 路径")
        select_root.geometry("400x300")  # 设置选择窗口大小
        select_root.resizable(False, False)  # 禁止调整窗口大小

        # 设置圆角窗口
        app = LocateWE(select_root, on_path_selected)

        app.root.protocol("WM_DELETE_WINDOW", select_root.destroy)  # 关闭选择窗口时退出应用
        app.root.mainloop()

        # 如果用户关闭选择窗口而没有选择路径，直接退出应用
        if not read_path_from_file("steam_path.txt"):
            return

def on_path_selected(app, steam_path_var=None):
    """
    处理路径选择结果。

    :param app: LocateWE 应用实例
    :param steam_path_var: steam.exe 路径变量
    """
    path = app.entry.get()
    if path and path.lower().endswith("steam.exe") and os.path.exists(path):
        with open("steam_path.txt", "w") as file:
            file.write(path)
        if steam_path_var is not None:
            steam_path_var.set(path)
        app.root.destroy()  # 关闭选择窗口

        # 写入 info.csv
        extract_info_to_csv()

        # 读取 info.csv 并展示
        df = read_info_csv("info.csv")
        if df is not None:
            # 读取 output_path.txt 文件中的路径
            output_path = read_path_from_file("output_path.txt")
            create_main_window(df, output_path)
    else:
        messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")

if __name__ == "__main__":
    main()