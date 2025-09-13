# lop and watch pyperclip data
import pyperclip
import time

prev_data = []
while True:
    data = pyperclip.paste()
    if data != prev_data:
        # Yellow header, green clipboard content
        print("\033[93mClipboard changed:\033[0m")
        print(f"\033[92m{data}\033[0m")
        prev_data = data
    time.sleep(0.1)

