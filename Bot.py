#!/usr/bin/env python3
"""
Time-Limited Web Terminal System (sshx.io Clone)
Single-File Production Architecture
- Backend: FastAPI + Asyncio WebSockets
- Engine: Linux PTY (Pseudo-Terminal) Subprocess Manager
- Database: Firebase Realtime Database
- Frontend: Embedded Single Page Application (HTML5/CSS3/xterm.js)
- Admin: Integrated CLI Management Suite
"""

import os
import sys
import pty
import fcntl
import termios
import struct
import signal
import asyncio
import secrets
import json
import re
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
import urllib.request
import urllib.error

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# ==============================================================================
# 1. CONFIGURATION & FIREBASE CONSTANTS
# ==============================================================================
FIREBASE_DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL", 
    "https://gsgssnn-580ca-default-rtdb.firebaseio.com"
).rstrip("/")
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "http://localhost:8000").rstrip("/")
DEFAULT_SHELL = os.getenv("SHELL", "/bin/bash")
APP_PORT = int(os.getenv("PORT", 8000))

# Local In-Memory Cache (Fallback & Real-time State Tracking)
LOCAL_SESSION_CACHE: Dict[str, Dict[str, Any]] = {}
ACTIVE_PTY_PROCESSES: Dict[str, Dict[str, Any]] = {}

# ==============================================================================
# 2. FIREBASE REALTIME DATABASE REST DRIVER
# ==============================================================================
class FirebaseStore:
    @staticmethod
    def _request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Optional[Any]:
        url = f"{FIREBASE_DATABASE_URL}/{endpoint.lstrip('/')}.json"
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        payload = json.dumps(data).encode("utf-8") if data is not None else None
        
        try:
            with urllib.request.urlopen(req, data=payload, timeout=5) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except Exception as err:
            print(f"[Firebase Warning] Cloud sync error ({endpoint}): {err}", file=sys.stderr)
            return None

    @classmethod
    def save_session(cls, token: str, session_data: dict) -> bool:
        LOCAL_SESSION_CACHE[token] = session_data
        result = cls._request(f"terminal_sessions/{token}", method="PUT", data=session_data)
        return result is not None or token in LOCAL_SESSION_CACHE

    @classmethod
    def get_session(cls, token: str) -> Optional[dict]:
        cloud_data = cls._request(f"terminal_sessions/{token}", method="GET")
        if cloud_data and isinstance(cloud_data, dict):
            LOCAL_SESSION_CACHE[token] = cloud_data
            return cloud_data
        return LOCAL_SESSION_CACHE.get(token)

    @classmethod
    def update_status(cls, token: str, status: str) -> bool:
        if token in LOCAL_SESSION_CACHE:
            LOCAL_SESSION_CACHE[token]["status"] = status
        result = cls._request(f"terminal_sessions/{token}/status", method="PUT", data=status)
        return result is not None

    @classmethod
    def list_all_sessions(cls) -> Dict[str, dict]:
        cloud_sessions = cls._request("terminal_sessions", method="GET")
        if cloud_sessions and isinstance(cloud_sessions, dict):
            LOCAL_SESSION_CACHE.update(cloud_sessions)
            return cloud_sessions
        return LOCAL_SESSION_CACHE

    @classmethod
    def delete_session(cls, token: str) -> bool:
        if token in LOCAL_SESSION_CACHE:
            del LOCAL_SESSION_CACHE[token]
        cls._request(f"terminal_sessions/{token}", method="DELETE")
        return True

# ==============================================================================
# 3. DURATION PARSER & TOKEN UTILS
# ==============================================================================
def parse_duration_string(duration_str: str) -> timedelta:
    """Parses strings like '1h', '3d', '15d', '30d', '365d', '45m' into timedelta."""
    duration_str = duration_str.strip().lower()
    presets = {
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
        "1month": timedelta(days=30),
        "30d": timedelta(days=30),
        "1year": timedelta(days=365),
        "365d": timedelta(days=365),
    }
    if duration_str in presets:
        return presets[duration_str]

    match = re.match(r"^(\d+)([smhdyw])$", duration_str)
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use e.g. 1h, 12h, 3d, 15d, 30d, 1y")

    amount, unit = int(match.group(1)), match.group(2)
    unit_map = {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
        "y": timedelta(days=amount * 365),
    }
    return unit_map[unit]

def create_terminal_session(duration_str: str, label: str = "Standard Session") -> dict:
    delta = parse_duration_string(duration_str)
    now = datetime.now(timezone.utc)
    expires_at = now + delta
    token = secrets.token_urlsafe(12)

    session_data = {
        "token": token,
        "label": label,
        "duration_requested": duration_str,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "status": "Active",
        "access_url": f"{PUBLIC_HOST}/s/{token}"
    }

    FirebaseStore.save_session(token, session_data)
    return session_data

def is_session_expired(session_data: dict) -> bool:
    if session_data.get("status") != "Active":
        return True
    try:
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.now(timezone.utc) >= expires_at:
            session_data["status"] = "Expired"
            FirebaseStore.update_status(session_data["token"], "Expired")
            return True
    except Exception:
        return True
    return False

# ==============================================================================
# 4. EMBEDDED FRONTEND UI (Single Page App HTML/CSS/JS)
# ==============================================================================
TERMINAL_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>sshx | Secure Web Terminal</title>
  
  <!-- xterm.js CDN -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css" />
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.min.js"></script>

  <style>
    :root {
      --bg-primary: #0a0c10;
      --bg-secondary: #12161f;
      --border-color: #242b38;
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
      --accent-green: #2ea043;
      --accent-amber: #d29922;
      --accent-red: #f85149;
      --accent-cyan: #388bfd;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    header {
      background-color: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      user-select: none;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      font-size: 0.95rem;
      letter-spacing: 0.5px;
    }
    .brand-tag {
      background: rgba(56, 139, 253, 0.15);
      color: var(--accent-cyan);
      border: 1px solid rgba(56, 139, 253, 0.3);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
    }
    .header-center {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--accent-amber);
    }
    .status-dot.active { background-color: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
    .status-dot.disconnected { background-color: var(--accent-red); }

    .timer-badge {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      padding: 4px 12px;
      border-radius: 20px;
      font-family: monospace;
      font-size: 0.85rem;
      display: flex;
      gap: 6px;
      align-items: center;
    }
    .timer-val { color: var(--accent-amber); font-weight: bold; }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn {
      background: #1c212c;
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn:hover { background: #2b3242; }

    #terminal-container {
      flex: 1;
      width: 100%;
      height: calc(100vh - 48px);
      padding: 8px;
      background: #0d1117;
    }
    .xterm { height: 100%; }

    #overlay-banner {
      display: none;
      position: absolute;
      top: 60px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(248, 81, 73, 0.95);
      color: white;
      padding: 12px 24px;
      border-radius: 8px;
      font-weight: 500;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      z-index: 999;
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <span>sshx.terminal</span>
      <span class="brand-tag">isolated pty</span>
    </div>

    <div class="header-center">
      <div class="status-badge">
        <div id="statusDot" class="status-dot"></div>
        <span id="statusText">Connecting...</span>
      </div>
      <div class="timer-badge">
        <span>Time Left:</span>
        <span id="countdownTimer" class="timer-val">--:--:--</span>
      </div>
    </div>

    <div class="header-actions">
      <button class="btn" onclick="navigator.clipboard.writeText(window.location.href); alert('Link Copied!');">Copy Link</button>
      <button class="btn" onclick="toggleFullscreen()">Fullscreen</button>
    </div>
  </header>

  <div id="overlay-banner">Session Expired or Revoked. Connection Terminated.</div>
  <div id="terminal-container"></div>

  <script>
    const sessionToken = "{{TOKEN}}";
    const expiresAtMs = new Date("{{EXPIRES_AT}}").getTime();

    // 1. Live Expiry Countdown
    function updateCountdown() {
      const now = new Date().getTime();
      const distance = expiresAtMs - now;

      if (distance <= 0) {
        document.getElementById("countdownTimer").innerText = "EXPIRED";
        document.getElementById("statusDot").className = "status-dot disconnected";
        document.getElementById("statusText").innerText = "Expired";
        document.getElementById("overlay-banner").style.display = "block";
        if (ws) ws.close();
        return;
      }

      const hours = Math.floor(distance / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      document.getElementById("countdownTimer").innerText = 
        `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    setInterval(updateCountdown, 1000);
    updateCountdown();

    // 2. Initialize xterm.js
    const term = new Terminal({
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        selectionBackground: '#388bfd40',
        black: '#484f58',
        red: '#ff7b72',
        green: '#3fb950',
        yellow: '#d29922',
        blue: '#58a6ff',
        magenta: '#bc8cff',
        cyan: '#39c5cf',
        white: '#b1bac4'
      },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      cursorBlink: true,
      scrollback: 10000
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon.WebLinksAddon());
    term.open(document.getElementById('terminal-container'));
    fitAddon.fit();

    window.addEventListener('resize', () => {
      fitAddon.fit();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
      }
    });

    // 3. WebSocket Connection
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionToken}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      document.getElementById("statusDot").className = "status-dot active";
      document.getElementById("statusText").innerText = "Active";
      fitAddon.fit();
      ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
      term.focus();
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onclose = () => {
      document.getElementById("statusDot").className = "status-dot disconnected";
      document.getElementById("statusText").innerText = "Disconnected";
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stdin", data: data }));
      }
    });

    function toggleFullscreen() {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
      } else {
        if (document.exitFullscreen) document.exitFullscreen();
      }
    }
  </script>
</body>
</html>
"""

EXPIRED_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Session Terminated | 410 Gone</title>
  <style>
    body {
      background-color: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
    }
    .card {
      background: #161b22;
      border: 1px solid #30363d;
      padding: 40px;
      border-radius: 12px;
      text-align: center;
      max-width: 480px;
      box-shadow: 0 16px 32px rgba(0,0,0,0.4);
    }
    h1 { color: #f85149; font-size: 1.8rem; margin-bottom: 12px; }
    p { color: #8b949e; line-height: 1.5; font-size: 0.95rem; margin-bottom: 24px; }
    .badge {
      background: rgba(248, 81, 73, 0.1);
      border: 1px solid rgba(248, 81, 73, 0.3);
      color: #ff7b72;
      padding: 4px 12px;
      border-radius: 6px;
      font-family: monospace;
      display: inline-block;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>410 - Session Expired</h1>
    <p>This web terminal link has expired, was revoked by an administrator, or the allocated time limit reached zero.</p>
    <div class="badge">Status: Expired / Subprocess Terminated</div>
  </div>
</body>
</html>
"""

# ==============================================================================
# 5. PTY (PSEUDO-TERMINAL) ASYNC MANAGER
# ==============================================================================
class PTYSession:
    def __init__(self, token: str, websocket: WebSocket, expires_at: datetime):
        self.token = token
        self.ws = websocket
        self.expires_at = expires_at
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.loop = asyncio.get_running_loop()
        self.is_running = True

    async def start(self):
        # Fork PTY process
        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:
            # Child process: Set shell environment & execute
            os.environ["TERM"] = "xterm-256color"
            os.environ["COLORTERM"] = "truecolor"
            os.execv(DEFAULT_SHELL, [DEFAULT_SHELL])
            sys.exit(0)
        else:
            # Parent process: set master_fd non-blocking
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Register reader callback in asyncio event loop
            self.loop.add_reader(self.master_fd, self._read_pty_output)

            # Register to active map
            ACTIVE_PTY_PROCESSES[self.token] = {
                "pty": self,
                "pid": self.pid,
                "created_at": datetime.now(timezone.utc)
            }

            # Spawn time-limit watchdog task
            asyncio.create_task(self._expiry_watchdog())

    def _read_pty_output(self):
        if not self.is_running or self.master_fd is None:
            return
        try:
            data = os.read(self.master_fd, 4096)
            if data:
                asyncio.create_task(self.ws.send_text(data.decode("utf-8", errors="replace")))
        except (BlockingIOError, InterruptedError):
            pass
        except Exception:
            self.cleanup()

    def write_stdin(self, data: str):
        if self.master_fd and self.is_running:
            try:
                os.write(self.master_fd, data.encode("utf-8"))
            except Exception as err:
                print(f"[PTY Error] Stdin write failure: {err}", file=sys.stderr)

    def resize(self, cols: int, rows: int):
        if self.master_fd and self.is_running:
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            except Exception as err:
                print(f"[PTY Error] Resize failed: {err}", file=sys.stderr)

    async def _expiry_watchdog(self):
        """Monitors session duration and forcibly kills process upon expiry."""
        while self.is_running:
            await asyncio.sleep(2)
            if datetime.now(timezone.utc) >= self.expires_at:
                try:
                    await self.ws.send_text("\r\n\x1b[1;31m[SESSION EXPIRED]: Time limit reached. Disconnecting...\x1b[0m\r\n")
                    await self.ws.close(code=1000)
                except Exception:
                    pass
                self.cleanup()
                break

    def cleanup(self):
        if not self.is_running:
            return
        self.is_running = False

        if self.master_fd is not None:
            try:
                self.loop.remove_reader(self.master_fd)
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

        if self.pid is not None:
            try:
                os.killpg(os.getpgid(self.pid), signal.SIGTERM)
            except Exception:
                try:
                    os.kill(self.pid, signal.SIGKILL)
                except Exception:
                    pass
            self.pid = None

        if self.token in ACTIVE_PTY_PROCESSES:
            del ACTIVE_PTY_PROCESSES[self.token]

# ==============================================================================
# 6. FASTAPI WEB APPLICATION & ROUTING
# ==============================================================================
app = FastAPI(title="Time-Limited Web Terminal (sshx.io)")

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(
        """<body style='background:#0d1117;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;'>
        <div style='text-align:center;'>
        <h2>sshx Time-Limited Web Terminal System</h2>
        <p style='color:#8b949e;'>Access via your unique token link: <code>/s/&lt;token&gt;</code></p>
        </div></body>"""
    )

@app.get("/s/{token}", response_class=HTMLResponse)
async def serve_terminal_page(token: str):
    session = FirebaseStore.get_session(token)
    if not session or is_session_expired(session):
        return HTMLResponse(content=EXPIRED_HTML_TEMPLATE, status_code=410)

    html_content = (
        TERMINAL_HTML_TEMPLATE
        .replace("{{TOKEN}}", token)
        .replace("{{EXPIRES_AT}}", session["expires_at"])
    )
    return HTMLResponse(content=html_content)

@app.websocket("/ws/{token}")
async def terminal_websocket(websocket: WebSocket, token: str):
    await websocket.accept()

    session = FirebaseStore.get_session(token)
    if not session or is_session_expired(session):
        await websocket.send_text("\r\n\x1b[1;31m[ERROR]: Link expired or invalid.\x1b[0m\r\n")
        await websocket.close(code=1008)
        return

    expires_at = datetime.fromisoformat(session["expires_at"])
    pty_session = PTYSession(token, websocket, expires_at)
    await pty_session.start()

    try:
        while True:
            message_text = await websocket.receive_text()
            message = json.loads(message_text)
            msg_type = message.get("type")

            if msg_type == "stdin":
                pty_session.write_stdin(message.get("data", ""))
            elif msg_type == "resize":
                cols = int(message.get("cols", 80))
                rows = int(message.get("rows", 24))
                pty_session.resize(cols, rows)

    except WebSocketDisconnect:
        pty_session.cleanup()
    except Exception as err:
        print(f"[WebSocket Error]: {err}", file=sys.stderr)
        pty_session.cleanup()

# ==============================================================================
# 7. INTERACTIVE CLI MANAGEMENT DASHBOARD (Admin Suite)
# ==============================================================================
def cli_dashboard():
    while True:
        print("\n" + "=" * 55)
        print("   SSHX TERMINAL CONTROLLER - ADMIN CLI DASHBOARD")
        print("=" * 55)
        print("1. Generate New Time-Limited Terminal Link")
        print("2. List All Active / Stored Sessions")
        print("3. Inspect Session Details")
        print("4. Revoke / Terminate Session Immediately")
        print("5. Start Production Server")
        print("6. Exit")
        choice = input("\nSelect Option [1-6]: ").strip()

        if choice == "1":
            print("\nPreset Durations: [1h] 1 Hour | [1d] 1 Day | [30d] 1 Month | [365d] 1 Year")
            print("Custom Input Examples: 15d, 3d, 12h, 45m")
            duration_input = input("Enter Duration: ").strip()
            label_input = input("Enter Session Label (Optional): ").strip() or "Web Terminal Link"

            try:
                session = create_terminal_session(duration_input, label_input)
                print("\n[SUCCESS] New Session Created!")
                print(f"Token:       {session['token']}")
                print(f"Created:     {session['created_at']}")
                print(f"Expires:     {session['expires_at']}")
                print(f"Access Link: {session['access_url']}")
            except Exception as e:
                print(f"[ERROR]: {e}")

        elif choice == "2":
            sessions = FirebaseStore.list_all_sessions()
            if not sessions:
                print("\nNo sessions found in storage.")
                continue

            print("\n" + "-" * 75)
            print(f"{'TOKEN':<16} | {'STATUS':<10} | {'EXPIRES AT':<25} | {'LABEL'}")
            print("-" * 75)
            for tok, data in sessions.items():
                status = "Expired" if is_session_expired(data) else data.get("status", "Active")
                print(f"{tok:<16} | {status:<10} | {data.get('expires_at', ''):<25} | {data.get('label', '')}")

        elif choice == "3":
            tok = input("\nEnter session token to inspect: ").strip()
            session = FirebaseStore.get_session(tok)
            if session:
                print(json.dumps(session, indent=4))
            else:
                print("[ERROR]: Session not found.")

        elif choice == "4":
            tok = input("\nEnter session token to REVOKE: ").strip()
            FirebaseStore.update_status(tok, "Revoked")
            if tok in ACTIVE_PTY_PROCESSES:
                ACTIVE_PTY_PROCESSES[tok]["pty"].cleanup()
            print(f"[SUCCESS]: Session '{tok}' revoked and killed.")

        elif choice == "5":
            print(f"\nLaunching Server on 0.0.0.0:{APP_PORT}...")
            uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
            break

        elif choice == "6":
            sys.exit(0)

# ==============================================================================
# 8. APPLICATION ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sshx Time-Limited Web Terminal System")
    parser.add_argument("command", nargs="?", default="server", choices=["server", "admin", "create", "list"])
    parser.add_argument("--duration", "-d", type=str, help="Duration for link generation (e.g. 1h, 15d, 30d)")
    parser.add_argument("--label", "-l", type=str, default="CLI Session", help="Session description")
    args = parser.parse_args()

    if args.command == "admin":
        cli_dashboard()
    elif args.command == "create":
        if not args.duration:
            print("[ERROR]: Please supply duration with -d (e.g., python app.py create -d 15d)")
            sys.exit(1)
        res = create_terminal_session(args.duration, args.label)
        print(f"\nGenerated Link: {res['access_url']}\nExpires At: {res['expires_at']}")
    elif args.command == "list":
        for tok, d in FirebaseStore.list_all_sessions().items():
            print(f"{tok} -> {d.get('status')} (Expires: {d.get('expires_at')})")
    else:
        # Default: Start Server
        uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
