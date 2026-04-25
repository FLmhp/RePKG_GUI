from dataclasses import dataclass, field
from typing import Optional

import tkinter as tk
from tkinter import ttk


@dataclass
class AppState:
    selected_items: set[str] = field(default_factory=set)
    not_convert_tex_to_image_var: Optional[tk.BooleanVar] = None
    use_wallpaper_name_as_subdir_var: Optional[tk.BooleanVar] = None
    copy_project_json_and_preview_var: Optional[tk.BooleanVar] = None
    overwrite_files_var: Optional[tk.BooleanVar] = None
    output_path_var: Optional[tk.StringVar] = None
    output_mode_var: Optional[tk.StringVar] = None
    batch_extract_workers_var: Optional[tk.StringVar] = None
    status_var: Optional[tk.StringVar] = None
    keyword_combobox_widget: Optional[ttk.Combobox] = None
    keyword_entry_widget: Optional[tk.Entry] = None
    current_tree_widget: Optional[ttk.Treeview] = None
    current_extract_button: Optional[tk.Button] = None
