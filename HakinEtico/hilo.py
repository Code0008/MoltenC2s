import ctypes
import time
kernel32 = ctypes.windll.kernel32
@ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
def thread_function(lpParam):
    for i in range(5):
        print(f"[Hilo] Iteración {i}")
        time.sleep(1)
    return 0

def create_ctypes_thread():
    thread_id = ctypes.c_ulong(0)
    h_thread = kernel32.CreateThread(None,0,thread_function,None,0,ctypes.byref(thread_id))
    if not h_thread:
        raise ctypes.WinError()
    print(f"[+] Hilo creado. ID: {thread_id.value}")
    return h_thread


if __name__ == "__main__":
    print("[*] Proceso principal iniciando hilo...")
    create_ctypes_thread()
    for i in range(100000):
        import os
        print(f"PID actual: {os.getpid()}")
        print(f"[Main] Iteración {i}")
        time.sleep(1)