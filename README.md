
---

## 🎯 Objetivos
- Documentar el diseño y flujo de un keylogger con canal C2 cifrado.
- Analizar riesgos e identificar puntos de detección (ETW, AMSI, EDR).
- Proponer medidas de mitigación y controles defensivos aplicables en entornos reales.

---

## ⚙️ Arquitectura (resumen)
1. **Inicialización**
   - Crea `SECURITY_ATTRIBUTES` heredables.
   - Abre un pipe anónimo con `CreatePipe()` y ajusta permisos con `SetHandleInformation()`.

2. **Ejecución de comandos**
   - Usa `CreateProcessW()` con `powershell.exe /c <cmd>` y `CREATE_NO_WINDOW`.
   - Configura `STARTUPINFO` con `STARTF_USESTDHANDLES` para redirigir `stdout/stderr`.

3. **Lectura y exfiltración**
   - Lee la salida con `ReadFile()` usando un buffer de 4096 bytes.
   - Envía resultados al endpoint `/readinfo` o `/uploads` mediante HTTPS.

4. **Ciclo C2 (pull-based)**
   - `/register` → `/gettask` → ejecución → `/readinfo`.

---

## 🔧 APIs / Flags relevantes
- **APIs:** `CreatePipe`, `SetHandleInformation`, `CreateProcessW`, `ReadFile`, `CloseHandle`.
- **Estructuras:** `SECURITY_ATTRIBUTES`, `STARTUPINFO`, `PROCESS_INFORMATION`.
- **Flags:** `STARTF_USESTDHANDLES`, `CREATE_NO_WINDOW`, `HANDLE_FLAG_INHERIT`.

---

## 🧠 Mapeo MITRE ATT&CK

| Táctica | ID | Técnica | Descripción |
|----------|----|----------|-------------|
| Execution | T1059.001 | PowerShell | Ejecución de comandos vía intérprete. |
| Execution | T1204.002 | User Execution | Ejecución por el usuario. |
| Collection | T1056.001 | Keylogging | Captura de entradas del teclado. |
| Command & Control | T1071.001 | Web Protocols | Comunicación C2 mediante HTTP/HTTPS. |
| Exfiltration | T1041 | Over C2 Channel | Exfiltración por canal de control. |
| Defense Evasion | T1562 | Impair Defenses | Interferencia con defensas (AV/EDR). |

---

## 🔍 Detecciones recomendadas
- Activar auditoría de procesos (Event ID **4688**).  
- Habilitar **Script Block Logging** y **AMSI**.  
- Monitorizar patrones de *beaconing* a dominios externos (periodicidad, JA3/JA4).  
- Correlacionar ejecución de `powershell.exe` con tráfico HTTPS saliente.  
- Detectar hooks de teclado o accesos repetidos a APIs sensibles.

---

## 🛡️ Mitigaciones sugeridas
- Restringir PowerShell con **Constrained Language Mode**, **AppLocker** o **WDAC**.  
- Bloquear dominios no autorizados y analizar tráfico TLS.  
- Aplicar reglas EDR que identifiquen `CreateProcess(powershell.exe)` + `CREATE_NO_WINDOW` + redirección de pipes.  
- Aplicar políticas de **least privilege** y segmentación de red.  

---

## 📊 Resultados
En entornos controlados, el agente demostró capacidad de:
- Capturar entradas (keylogging) sin privilegios elevados.
- Ejecutar comandos remotos y enviar la salida al C2.
- Mantener comunicación HTTPS sin detección inicial por Defender.

Sin embargo, presenta **limitaciones operativas** y **patrones detectables** por soluciones EDR modernas.

---

## 👥 Autores
- **Giordano Abraham Villegas Risco** — u20241339  
- **Fredy Salvador Gamarra Ramos** — u202412038

---

## 📚 Referencias
- [MITRE ATT&CK Framework](https://attack.mitre.org)  
- [HackTheBox Academy](https://academy.hackthebox.com)  
- Técnicas: T1059, T1056.001, T1071.001, T1041, T1562, T1027.

---
---
## 📬 Contacto
**Giordano Villegas** — u20241339 - [Linkedin](https://www.linkedin.com/in/abraham-villegas-r-760875362/)

**Fredy Gamarra** — u202412038 - [Linkedin](https://www.linkedin.com/in/fredy-salvador-gamarra-ramos/)

