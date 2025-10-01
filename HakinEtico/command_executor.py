import ctypes
import ctypes.wintypes as wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Constantes
STARTF_USESTDHANDLES = 0x00000100
CREATE_NO_WINDOW = 0x08000000
HANDLE_FLAG_INHERIT = 0x00000001
BUFSIZE = 4096

# Estructuras
class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

# Firmas de funciones (recomendado)
kernel32.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.DWORD]
kernel32.CreatePipe.restype  = wintypes.BOOL

kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
kernel32.SetHandleInformation.restype  = wintypes.BOOL

kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR,
    ctypes.POINTER(SECURITY_ATTRIBUTES), ctypes.POINTER(SECURITY_ATTRIBUTES),
    wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID,
    wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)
]
kernel32.CreateProcessW.restype = wintypes.BOOL

kernel32.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
kernel32.ReadFile.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

def run_command_get_output(cmd):
    # Crear SECURITY_ATTRIBUTES heredable
    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
    sa.lpSecurityDescriptor = None
    sa.bInheritHandle = True

    # Handles para pipe
    read_handle = wintypes.HANDLE()
    write_handle = wintypes.HANDLE()

    if not kernel32.CreatePipe(ctypes.byref(read_handle), ctypes.byref(write_handle), ctypes.byref(sa), 0):
        raise ctypes.WinError(ctypes.get_last_error())

    # Evitar que el handle de lectura sea heredado por el hijo
    if not kernel32.SetHandleInformation(read_handle, HANDLE_FLAG_INHERIT, 0):
        kernel32.CloseHandle(read_handle)
        kernel32.CloseHandle(write_handle)
        raise ctypes.WinError(ctypes.get_last_error())

    # Preparar STARTUPINFO con los handles de stdout/stderr apuntando al write_handle
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    si.dwFlags = STARTF_USESTDHANDLES
    si.hStdOutput = write_handle
    si.hStdError = write_handle
    si.hStdInput = None

    pi = PROCESS_INFORMATION()

    # Comando: usar cmd.exe /c <cmd>
    cmdline = f'powershell.exe /c {cmd}'

    success = kernel32.CreateProcessW(
        None,
        ctypes.create_unicode_buffer(cmdline),
        None,
        None,
        True,               
        CREATE_NO_WINDOW,  
        None,
        None,
        ctypes.byref(si),
        ctypes.byref(pi)
    )

    if not success:
        kernel32.CloseHandle(read_handle)
        kernel32.CloseHandle(write_handle)
        raise ctypes.WinError(ctypes.get_last_error())

    kernel32.CloseHandle(write_handle)

    # Leer desde el pipe
    output_bytes = bytearray()
    bytes_read = wintypes.DWORD(0)
    buf = ctypes.create_string_buffer(BUFSIZE)

    while True:
        ok = kernel32.ReadFile(read_handle, buf, BUFSIZE, ctypes.byref(bytes_read), None)
        if not ok or bytes_read.value == 0:
            break
        output_bytes += buf.raw[:bytes_read.value]

    # Cerrar handles del proceso
    kernel32.CloseHandle(read_handle)
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)

    return output_bytes.decode("utf-8", errors="ignore").strip()

if __name__ == "__main__":
    salida = run_command_get_output("Get-Process")
