from tkinter import *
import webbrowser
from PIL import Image, ImageTk

# 创建Tkinter窗口
root = Tk()

# 定义回调函数
def callback(url):
    webbrowser.open_new(url)

# 加载图片
image = Image.open("1739175194920.png")
photo = ImageTk.PhotoImage(image)

# 创建Label以显示图片
link = Label(root, image=photo, cursor="hand2")
link.pack()

# 绑定点击事件
link.bind("<Button-1>", lambda e: callback("https://blog.csdn.net/flMHP?spm=1010.2135.3001.5343"))

# 运行Tkinter主循环
root.mainloop()
