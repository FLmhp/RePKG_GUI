import json
import os
import csv

# 定义要提取的字段
fields_to_extract = ["preview", "tags", "title", "type"]

# 读取 path.txt 文件中的路径
with open("path.txt", 'r', encoding='utf-8') as path_file:
    steam_path = path_file.read().strip()

# 替换路径中的 steam.exe 为 steamapps\workshop\content\431960
directory = os.path.join(os.path.dirname(steam_path), "steamapps", "workshop", "content", "431960")

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
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    # 提取所需字段
                    extracted_data = {field: data.get(field, None) for field in fields_to_extract}
                    extracted_info.append(extracted_data)

# 将提取的信息写入 info.csv 文件
csv_file_path = r"c:\Users\FLmhp\Documents\Code\Projects\RePKG_GUI\info.csv"
with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.DictWriter(csv_file, fieldnames=fields_to_extract)
    csv_writer.writeheader()
    csv_writer.writerows(extracted_info)

print(f"信息已成功写入 {csv_file_path}")