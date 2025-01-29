# 导入标准库
import csv
import datetime
import json
import os

# 导入第三方库
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# 导入自定义模块
from LocateWE import LocateWE

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
    fields_to_extract = ["preview", "tags", "title", "type"]

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
            # 遍历子文件夹中的所有文件
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(folder_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            data = json.load(file)
                            # 提取所需字段
                            extracted_data = {field: data.get(field, None) for field in fields_to_extract}
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

def read_info_csv(file_path):
    """
    读取 CSV 文件并返回 DataFrame。

    :param file_path: CSV 文件路径
    :return: DataFrame 或 None
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        messagebox.showwarning("文件未找到", f"未找到文件: {file_path}")
    except pd.errors.EmptyDataError:
        messagebox.showwarning("文件为空", f"文件 {file_path} 为空")
    except pd.errors.ParserError:
        messagebox.showwarning("解析错误", f"无法解析文件 {file_path}")
    return None

def display_table(root, df):
    """
    在窗口中显示信息表格。

    :param root: 窗口根对象
    :param df: DataFrame 对象
    """
    tree = ttk.Treeview(root, columns=list(df.columns), show='headings')
    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)  # 设置列宽，可以根据需要调整
    for index, row in df.iterrows():
        tree.insert("", tk.END, values=list(row))
    tree.pack(expand=True, fill=tk.BOTH)

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

    # 切换排序顺序
    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

def create_main_window(df, output_path):
    root = tk.Tk()
    root.title("RePKG_GUI")
    root.geometry("1200x600")  # 设置窗口大小
    root.resizable(False, False)  # 禁止调整窗口大小

    # 确保窗口居中
    center_window(root)

    # 创建主框架
    main_frame = tk.Frame(root)
    main_frame.pack(expand=True, fill=tk.BOTH)

    # 左侧区域：信息表格
    left_frame = tk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    tree = ttk.Treeview(left_frame, columns=("title", "tags", "type"), show='headings')
    tree.heading("title", text="Title", command=lambda: sort_column(tree, "title", False))
    tree.heading("tags", text="Tags", command=lambda: sort_column(tree, "tags", False))
    tree.heading("type", text="Type", command=lambda: sort_column(tree, "type", False))
    tree.column("title", width=200)
    tree.column("tags", width=100)
    tree.column("type", width=100)
    for index, row in df.iterrows():
        tree.insert("", tk.END, values=(row["title"], row["tags"], row["type"]))
    tree.pack(expand=True, fill=tk.BOTH)

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
    style.configure('TCombobox', postoffset=(0, 0, 40, 0))  # 增加下拉框的宽度

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
    window_width = 1200
    window_height = 600
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
            create_main_window(df)
    else:
        messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")

if __name__ == "__main__":
    main()