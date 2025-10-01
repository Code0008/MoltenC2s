import ctypes
import ctypes.wintypes as wintypes



kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.POINTER(ctypes.c_byte)),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
    ]

def create_background_process(command_line):
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    # Flags para no mostrar ventana
    CREATE_NO_WINDOW = 0x08000000

    success = kernel32.CreateProcessW(
        None,                        # lpApplicationName
        command_line,               # lpCommandLine
        None, None,                 # lpProcessAttributes, lpThreadAttributes
        False,                      # bInheritHandles
        CREATE_NO_WINDOW,           # dwCreationFlags
        None,                       # lpEnvironment
        None,                       # lpCurrentDirectory
        ctypes.byref(si),           # lpStartupInfo
        ctypes.byref(pi)            # lpProcessInformation
    )

    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    else:
        print(f"[+] Proceso creado en segundo plano. PID: {pi.dwProcessId}")
        return pi

# Ejemplo de uso
if __name__ == "__main__":
    
    cmd = r'"C:\Users\Public\Downloads\notepede.exe'  # o tu_script.exe / script.py
    create_background_process(cmd)
