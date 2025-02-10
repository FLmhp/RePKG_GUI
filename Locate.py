import os
import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
import ctypes
import win32gui
from tkinter import filedialog, messagebox
from scandir import scandir

class Locate:
    def __init__(self, root, on_path_selected_callback, steam_path_var=None):
        """
        初始化 Locate 类，设置窗口属性和创建控件。

        :param root: Tkinter 根窗口对象
        :param on_path_selected_callback: 选择路径后的回调函数
        :param steam_path_var: 存储 Steam 路径的变量（可选）
        """
        self.root = root
        self.on_path_selected_callback = on_path_selected_callback
        self.steam_path_var = steam_path_var
        self.root.title("RePKG_GUI")
        self.window_width = 400
        self.window_height = 300
        try:
            # 检查 config.json 文件是否存在，如果不存在则创建默认文件
            if not os.path.exists("config.json"):
                default_config = {
                    "steam_path": "",
                    "output_path": "./output"
                }
                with open("config.json", "w", encoding='utf-8') as file:
                    json.dump(default_config, file, indent=4)

            self.check_path_file()  # 检查 steam_path 的状态
            self.center_window()  # 将窗口居中
            self.set_rounded_corners()  # 设置窗口圆角效果
            self.create_widgets()  # 创建窗口控件
        except Exception as e:
            self.log_error(f"Error initializing window: {e}")
            messagebox.showerror("初始化失败", "窗口初始化失败，请检查日志文件。")

    def check_path_file(self):
        """
        检查 config.json 文件中 steam_path 的状态，如果路径不存在、为空或路径不指向 steam.exe，则清空 logs.txt。
        """
        try:
            # 检查 config.json 文件是否存在
            if not os.path.exists("config.json"):
                self.clear_logs()
                return

            # 读取 config.json 文件
            with open("config.json", "r", encoding='utf-8') as file:
                config = json.load(file)
                path = config.get("steam_path", "")

            # 检查路径是否有效
            if not path or not os.path.isfile(path) or not path.lower().endswith("steam.exe"):
                self.clear_logs()
        except FileNotFoundError:
            self.log_error("config.json 文件未找到")
        except json.JSONDecodeError:
            self.log_error("config.json 文件格式错误")
        except Exception as e:
            self.log_error(f"Error checking path file: {e}")

    def clear_logs(self):
        """
        清空 logs.txt 文件。
        """
        try:
            with open("logs.txt", "w") as log_file:
                log_file.write("")
        except Exception as e:
            self.log_error(f"Error clearing logs: {e}")

    def log_success(self, message):
        """
        将成功信息写入 logs.txt 文件并包含时间戳。

        :param message: 成功信息
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("logs.txt", "a") as log_file:
                log_file.write(f"{timestamp} - SUCCESS: {message}\n")
        except Exception as e:
            self.log_error(f"Error logging success: {e}")

    def log_error(self, message):
        """
        将错误信息写入 errors.txt 文件并包含时间戳。

        :param message: 错误信息
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("errors.txt", "a") as log_file:
                log_file.write(f"{timestamp} - ERROR: {message}\n")
        except Exception as e:
            messagebox.showwarning("日志错误", f"Error logging error: {e}")

    def set_window_attribute(self, window, attribute, value):
        """
        设置窗口的 DWM 属性。

        :param window: Tkinter 窗口对象
        :param attribute: 属性 ID
        :param value: 属性值
        """
        try:
            hwnd = win32gui.GetParent(window.winfo_id())  # 获取窗口句柄
            DwmSetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(ctypes.c_int(value)), ctypes.sizeof(ctypes.c_int))
            self.log_success(f"Set window attribute {attribute} to {value}")
        except Exception as e:
            self.log_error(f"Error setting window attribute: {e}")

    def set_rounded_corners(self, enable=True):
        """
        设置窗口的圆角效果。

        :param enable: 是否启用圆角（True 为圆角，False 为直角）
        """
        try:
            value = 2 if enable else 1
            self.set_window_attribute(self.root, 33, value)
            self.log_success(f"Set rounded corners to {'enabled' if enable else 'disabled'}")
        except Exception as e:
            self.log_error(f"Error setting rounded corners: {e}")

    def center_window(self):
        """
        将窗口居中显示在屏幕上。
        """
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - self.window_width) // 2
            y = (screen_height - self.window_height) // 2
            self.root.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')
            self.log_success("Centered window")
        except Exception as e:
            self.log_error(f"Error centering window: {e}")

    def select_file(self):
        """
        打开文件选择对话框并显示所选文件路径。
        """
        try:
            file_path = filedialog.askopenfilename()
            if file_path and os.path.isfile(file_path):
                if file_path.lower().endswith("steam.exe"):
                    self.entry.config(state='normal')  # 设置输入框为可编辑模式
                    self.entry.delete(0, tk.END)
                    self.entry.insert(0, file_path)
                    self.write_path_to_file(file_path)  # 将路径写入文件
                    self.create_confirm_button()  # 创建确认按钮
                    self.entry.config(state='readonly')  # 设置输入框为只读模式
                    self.log_success(f"Selected file: {file_path}")
                else:
                    messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")
                    self.entry.delete(0, tk.END)
            elif file_path:
                messagebox.showwarning("路径错误", "选择的路径无效")
                self.entry.delete(0, tk.END)
        except Exception as e:
            self.log_error(f"Error selecting file: {e}")
            messagebox.showerror("选择文件失败", "选择文件时发生错误，请检查日志文件。")

    def search_steam(self):
        """
        搜索 steam.exe 的位置并显示在输入框中。
        """
        try:
            steam_path = self.find_steam_exe()
            if steam_path:
                self.entry.config(state='normal')  # 设置输入框为可编辑模式
                self.entry.delete(0, tk.END)
                self.entry.insert(0, steam_path)
                self.write_path_to_file(steam_path)  # 将路径写入文件
                self.create_confirm_button()  # 创建确认按钮
                self.entry.config(state='readonly')  # 设置输入框为只读模式
                self.log_success(f"Found steam.exe at: {steam_path}")
            else:
                self.search_steam_on_all_drives()
        except Exception as e:
            self.log_error(f"Error searching for steam.exe: {e}")
            messagebox.showerror("搜索失败", "搜索 steam.exe 时发生错误，请检查日志文件。")

    def find_steam_exe(self):
        """
        使用 scandir 库搜索常见路径中的 steam.exe 文件。

        :return: steam.exe 的路径或 None（如果未找到）
        """
        common_paths = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Program Files (x86)\Steam",
            r"D:\Program Files\Steam",
            r"E:\Program Files (x86)\Steam",
            r"E:\Program Files\Steam"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                try:
                    for entry in scandir(path):
                        if entry.name.lower() == "steam.exe" and entry.is_file():
                            return entry.path
                except FileNotFoundError:
                    self.log_error(f"FileNotFoundError scanning {path}")
                except Exception as e:
                    self.log_error(f"Error scanning {path}: {e}")
        return None

    def search_steam_on_all_drives(self):
        """
        在所有盘符中搜索 steam.exe 并显示在输入框中。
        """
        try:
            drives = self.get_drives()
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(self.find_steam_exe_on_drive, drive): drive for drive in drives}
                for future in as_completed(futures):
                    try:
                        steam_path = future.result()
                        if steam_path:
                            self.entry.delete(0, tk.END)
                            self.entry.insert(0, steam_path)
                            self.create_confirm_button()  # 创建确认按钮
                            self.log_success(f"Found steam.exe at: {steam_path}")
                            return
                    except Exception as e:
                        self.log_error(f"Error searching drive {futures[future]}: {e}")
            self.entry.delete(0, tk.END)
            messagebox.showwarning("未找到 steam.exe", "在所有驱动器中未找到 steam.exe")
        except Exception as e:
            self.log_error(f"Error searching steam.exe on all drives: {e}")
            messagebox.showerror("搜索失败", "搜索所有驱动器时发生错误，请检查日志文件。")

    def find_steam_exe_on_drive(self, drive):
        """
        在指定盘符中搜索 steam.exe 文件。

        :param drive: 盘符路径
        :return: steam.exe 的路径或 None（如果未找到）
        """
        try:
            if not os.path.exists(drive):
                return None
            for entry in scandir(drive):
                if entry.is_dir():
                    dir_path = entry.path
                    if os.path.exists(dir_path):
                        for sub_entry in scandir(dir_path):
                            if sub_entry.name.lower() == "steam.exe" and sub_entry.is_file():
                                self.write_path_to_file(sub_entry.path)  # 将路径写入文件
                                return sub_entry.path
        except FileNotFoundError:
            self.log_error(f"FileNotFoundError scanning drive {drive}")
        except Exception as e:
            self.log_error(f"Error scanning drive {drive}: {e}")
        return None

    def get_drives(self):
        """
        获取系统中所有可用的盘符。

        :return: 包含所有可用盘符的列表
        """
        try:
            drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
            drives = []
            for drive in range(1, 27):
                if drive_bitmask & 1:
                    drives.append(chr(ord('A') + drive - 1) + ':\\')
                drive_bitmask >>= 1
            return drives
        except Exception as e:
            self.log_error(f"Error getting drives: {e}")
            return []

    def write_path_to_file(self, path):
        """
        将路径写入 config.json 文件。

        :param path: steam.exe 的路径
        """
        try:
            with open("config.json", "r+", encoding='utf-8') as file:
                config = json.load(file)
                config["steam_path"] = path
                file.seek(0)
                json.dump(config, file, indent=4)
                file.truncate()
            self.log_success(f"Wrote path to file: {path}")
        except FileNotFoundError:
            self.log_error("config.json 文件未找到")
        except json.JSONDecodeError:
            self.log_error("config.json 文件格式错误")
        except Exception as e:
            self.log_error(f"Error writing path to file: {e}")

    def create_widgets(self):
        """
        创建窗口中的控件。
        """
        try:
            label = tk.Label(self.root, text="请设置steam.exe路径：", font=("Arial", 14))
            label.pack(pady=20)

            self.entry = tk.Entry(self.root, width=50)
            self.entry.pack(pady=10)
            # 设置输入框为只读模式
            self.entry.config(state='readonly')

            # 创建一个用于显示提示信息的半透明小窗口
            self.hint_window = tk.Toplevel(self.root)
            self.hint_window.withdraw()  # 初始时隐藏小窗口
            self.hint_window.overrideredirect(True)  # 去除窗口边框
            self.hint_window.attributes('-alpha', 0.9)  # 设置窗口透明度

            # 创建一个用于显示提示信息的标签
            hint_label = tk.Label(self.hint_window, text="双击自动定位", bg='lightblue', fg='black', font=("Arial", 9))
            hint_label.pack()

            # 定义鼠标悬停事件处理函数
            def show_hint(event):
                self.hint_window.deiconify()  # 显示小窗口
                self.hint_window.lift()  # 确保小窗口在最上层
                self.hint_window.geometry(f"+{event.x_root + 20}+{event.y_root - 20}")  # 设置小窗口的位置

            # 定义鼠标离开事件处理函数
            def hide_hint(event):
                self.hint_window.withdraw()  # 隐藏小窗口

            # 将鼠标悬停事件绑定到输入框上
            self.entry.bind("<Enter>", show_hint)
            self.entry.bind("<Leave>", hide_hint)

            # 定义双击事件处理函数
            def on_double_click(event):
                self.entry.config(state='normal')  # 设置输入框为可编辑模式
                self.search_steam()
                self.entry.config(state='readonly')  # 设置输入框为只读模式
                # 移除双击事件绑定
                self.entry.unbind("<Double-1>")

            # 将双击事件绑定到输入框上，使其在双击时调用 search_steam 方法
            self.entry.bind("<Double-1>", on_double_click)

            button_select = tk.Button(self.root, text="浏览", command=self.select_file)
            button_select.pack(pady=5)

            self.log_success("Created widgets")
        except Exception as e:
            self.log_error(f"Error creating widgets: {e}")
            messagebox.showerror("创建控件失败", "创建控件时发生错误，请检查日志文件。")

    def create_confirm_button(self):
        """
        创建确认按钮并绑定关闭窗口的事件。
        """
        try:
            self.confirm_button = tk.Button(self.root, text="确认", command=self.on_confirm)
            self.confirm_button.pack(pady=5)
            self.log_success("Created confirm button")
        except Exception as e:
            self.log_error(f"Error creating confirm button: {e}")
            messagebox.showerror("创建确认按钮失败", "创建确认按钮时发生错误，请检查日志文件。")

    def on_confirm(self):
        """
        处理确认按钮点击事件，调用回调函数。
        """
        try:
            if self.steam_path_var is not None:
                self.on_path_selected_callback(self, self.steam_path_var)
            else:
                self.on_path_selected_callback(self)
            self.log_success("Confirmed path selection")
        except Exception as e:
            self.log_error(f"Error on confirm: {e}")
            messagebox.showerror("确认失败", "确认时发生错误，请检查日志文件。")