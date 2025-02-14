import subprocess

# 使用subprocess.Popen在后台执行命令，注意使用双反斜杠转义路径中的反斜杠
process = subprocess.Popen(['.\\Repkg extract "C:\\Program Files (x86)\\Steam\\steamapps\\workshop\\content\\431960\\1087763654\\scene.pkg" --overwrite -o "C:\\Program Files (x86)\\Steam\\steamapps\\workshop\\content\\431960\\1087763654\\output"'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# 读取输出结果
stdout, stderr = process.communicate()

# 打印输出结果
print(stdout)
