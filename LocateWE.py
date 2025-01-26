import os
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
import ctypes
import win32gui
from tkinter import filedialog, messagebox
from scandir import scandir

class LocateWE:
    def __init__(self, root, on_path_selected_callback):
        self.root = root
        self.on_path_selected_callback = on_path_selected_callback
        self.root.title("RePKG_GUI")
        self.window_width = 400
        self.window_height = 300
        self.center_window()
        self.set_rounded_corners()
        self.create_widgets()

    def set_window_attribute(self, window, attribute, value):
        hwnd = win32gui.GetParent(window.winfo_id())  # 获取窗口句柄
        DwmSetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(ctypes.c_int(value)), ctypes.sizeof(ctypes.c_int))

    def set_rounded_corners(self, enable=True):
        """
        设置窗口的圆角效果
        :param window: Tkinter窗口对象
        :param enable: 是否启用圆角（True为圆角，False为直角）
        """
        value = 2 if enable else 1
        self.set_window_attribute(self.root, 33, value)

    def center_window(self):
        """
        将窗口居中
        """
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        self.root.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')

    def select_file(self):
        """
        打开文件选择对话框并显示所选文件路径
        """
        file_path = filedialog.askopenfilename()
        if file_path:
            if file_path.lower().endswith("steam.exe"):
                self.entry.delete(0, tk.END)
                self.entry.insert(0, file_path)
                self.write_path_to_file(file_path)  # 将路径写入文件
                self.create_confirm_button()  # 创建确认按钮
            else:
                messagebox.showwarning("路径错误", "请选择正确的 steam.exe 路径")
                self.entry.delete(0, tk.END)

    def search_steam(self):
        """
        搜索 steam.exe 的位置并显示在输入框中
        """
        steam_path = self.find_steam_exe()
        if steam_path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, steam_path)
            self.write_path_to_file(steam_path)  # 将路径写入文件
            self.create_confirm_button()  # 创建确认按钮
        else:
            self.search_steam_on_all_drives()

    def find_steam_exe(self):
        """
        使用 scandir 库搜索 steam.exe 的位置
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
        在所有盘符中搜索 steam.exe
        """
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
                        return
                except Exception as e:
                    self.log_error(f"Error searching drive {futures[future]}: {e}")
        self.entry.delete(0, tk.END)
        messagebox.showwarning("未找到 steam.exe", "在所有驱动器中未找到 steam.exe")

    def find_steam_exe_on_drive(self, drive):
        """
        在指定盘符中搜索 steam.exe
        """
        if not os.path.exists(drive):
            return None
        try:
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
        drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
        drives = []
        for drive in range(1, 27):
            if drive_bitmask & 1:
                drives.append(chr(ord('A') + drive - 1) + ':\\')
            drive_bitmask >>= 1
        return drives

    def log_error(self, message):
        """
        将错误信息写入 errors.txt 文件并包含时间戳
        :param message: 错误信息
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("errors.txt", "a") as log_file:
            log_file.write(f"{timestamp} - {message}\n")

    def write_path_to_file(self, path):
        """
        将路径写入 path.txt 文件
        :param path: steam.exe 的路径
        """
        with open("path.txt", "w") as file:
            file.write(path)

    def create_widgets(self):
        label = tk.Label(self.root, text="steam.exe路径：", font=("Arial", 14))
        label.pack(pady=20)

        self.entry = tk.Entry(self.root, width=50)
        self.entry.pack(pady=10)

        button_select = tk.Button(self.root, text="选择steam.exe路径", command=self.select_file)
        button_select.pack(pady=5)

        button_search = tk.Button(self.root, text="自动搜索", command=self.search_steam)
        button_search.pack(pady=5)

    def create_confirm_button(self):
        """
        创建确认按钮并绑定关闭窗口的事件
        """
        self.confirm_button = tk.Button(self.root, text="确认", command=lambda: self.on_path_selected_callback(self))
        self.confirm_button.pack(pady=5)

# if __name__ == "__main__":
#     root = tk.Tk()
#     app = LocateWE(root)
#     root.mainloop()