import os
import ctypes

def get_drives():
    drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
    drives = []
    for drive in range(1, 27):
        if drive_bitmask & 1:
            drives.append(chr(ord('A') + drive - 1) + ':\\')
        drive_bitmask >>= 1
    return drives

if __name__ == "__main__":
    drives = get_drives()
    print("当前电脑的盘符有:", drives)