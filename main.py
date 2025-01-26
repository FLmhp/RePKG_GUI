import os
import tkinter as tk
from tkinter import ttk, messagebox
from LocateWE import LocateWE
import pandas as pd

def read_path_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            path = file.read().strip()
            if os.path.exists(path) and path.lower().endswith("steam.exe"):
                return path
    except FileNotFoundError:
        pass
    return None

def read_info_csv(file_path):
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
    tree = ttk.Treeview(root, columns=list(df.columns), show='headings')
    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)  # 设置列宽，可以根据需要调整
    for index, row in df.iterrows():
        tree.insert("", tk.END, values=list(row))
    tree.pack(expand=True, fill=tk.BOTH)

def main():
    path = read_path_from_file("path.txt")
    if path:
        # 路径有效，读取并展示info.csv
        df = read_info_csv("info.csv")
        if df is not None:
            create_main_window(df)
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
        if not read_path_from_file("path.txt"):
            return

def on_path_selected(app):
    path = app.entry.get()
    if path and path.lower().endswith("steam.exe") and os.path.exists(path):
        with open("path.txt", "w") as file:
            file.write(path)
        app.root.destroy()  # 关闭选择窗口
        df = read_info_csv("info.csv")
        if df is not None:
            create_main_window(df)
    else:
        messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")

def create_main_window(df):
    root = tk.Tk()
    root.title("RePKG_GUI")
    root.geometry("800x600")  # 设置主窗口大小
    root.resizable(False, False)  # 禁止调整窗口大小

    # 确保窗口居中
    center_window(root)

    display_table(root, df)
    root.mainloop()

def center_window(root):
    """
    将窗口居中
    """
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 800
    window_height = 600
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f'{window_width}x{window_height}+{x}+{y}')

if __name__ == "__main__":
    main()