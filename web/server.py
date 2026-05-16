from http.server import HTTPServer, SimpleHTTPRequestHandler
import copy
import json
import os
import re as _re_multipart
import subprocess
from io import BytesIO
from urllib.parse import parse_qs, unquote, quote
import time
import base64
import socket
import threading
import ssl
import pystray
from PIL import Image
import webbrowser
import re
import uuid
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


# Fast-start HTTPServer: the default server_bind() calls socket.getfqdn(),
# which can block for 10+ seconds on machines with no reverse-DNS for the
# local hostname. We don't use server_name anywhere meaningful, so skip it.
class FastHTTPServer(HTTPServer):
    def server_bind(self):
        # Parent chain: TCPServer.server_bind binds the socket, then
        # BaseHTTPServer.server_bind sets server_name / server_port via getfqdn.
        # Skip the getfqdn step; set server_name from the raw host.
        import socketserver
        socketserver.TCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = host or "localhost"
        self.server_port = port


# ---------------------------------------------------------------------------
# Minimal multipart/form-data parser (stdlib only).
#
# Replaces `cgi.FieldStorage` which was removed from Python 3.13's stdlib.
# Parses a single file upload from a multipart body, which is all this server
# needs — it has exactly one /upload endpoint that expects a "file" field.
#
# Returns (filename, BytesIO) for the first file field found, or (None, None)
# if no file present or the body isn't multipart.
# ---------------------------------------------------------------------------
def _parse_multipart_file_upload(rfile, content_type: str, content_length: int):
    if not content_type or "multipart/form-data" not in content_type.lower():
        return None, None
    if content_length <= 0:
        return None, None

    m = _re_multipart.search(r"boundary=([^;\s]+)", content_type, _re_multipart.IGNORECASE)
    if not m:
        return None, None
    boundary = m.group(1).strip('"').encode("ascii", errors="replace")

    # Read the whole body. Current cgi.FieldStorage path also buffered the
    # body (to memory for small, to temp file for large). MAP_MAX_SIZE_BYTES
    # is enforced downstream on stream-save, not here.
    body = rfile.read(content_length)

    delimiter = b"--" + boundary
    # Split on the delimiter; first element is preamble (empty normally),
    # last element is the closing "--" marker or trailing whitespace.
    parts = body.split(delimiter)
    for part in parts[1:-1]:
        # Each real part starts with \r\n after the delimiter.
        part = part.lstrip(b"\r\n")
        # Trailing \r\n before the next delimiter.
        if part.endswith(b"\r\n"):
            part = part[:-2]
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        raw_headers = part[:header_end].decode("utf-8", errors="replace")
        part_body = part[header_end + 4:]

        disp_m = _re_multipart.search(
            r"Content-Disposition:\s*form-data;\s*(.*)",
            raw_headers,
            _re_multipart.IGNORECASE,
        )
        if not disp_m:
            continue
        disp = disp_m.group(1)
        name_m = _re_multipart.search(r'name="([^"]*)"', disp)
        filename_m = _re_multipart.search(r'filename="([^"]*)"', disp)
        if filename_m is None:
            continue
        # Only return the part whose field name is "file" — matches the
        # existing frontend contract (<input type="file" name="file">).
        if name_m is None or name_m.group(1) != "file":
            continue
        return filename_m.group(1), BytesIO(part_body)

    return None, None

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.map_sync import sync_ddnet_maps

# Configuration
MAPS_FOLDER = os.path.expanduser('~\\AppData\\Roaming\\DDNet\\maps')
# Default: 50 MB max size (adjust if needed)
MAP_MAX_SIZE_BYTES = 50 * 1024 * 1024


def _resolve_server_storage_cfg() -> str | None:
    """Find the storage.cfg the local DDNet server actually reads.

    DDNet's storage subsystem reads `storage.cfg` from the directory the
    server process was launched from ($CURRENTDIR), NOT from %APPDATA%. For
    Steam-installed servers that's the Steam install folder. We probe a few
    common locations and let an env var override.

    Resolution order:
      1. DDNETCONTROL_STORAGE_CFG env var (explicit override)
      2. Directory of any currently-running DDNet-Server.exe process
      3. First Steam install discovered alphabetically across drive letters

    Returns the absolute path string, or None when no install is detected
    (in which case the caller falls back to %APPDATA%\\DDNet\\storage.cfg).
    """
    override = os.environ.get("DDNETCONTROL_STORAGE_CFG")
    if override:
        return override

    # Prefer the install that's currently running — that's the one the user
    # cares about. Use WMIC (Windows-only) to grab the executable path of any
    # live DDNet-Server.exe process. Best-effort: don't fail if WMIC isn't
    # available or returns nothing useful.
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "name='DDNet-Server.exe'", "get",
             "ExecutablePath", "/format:list"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.lower().startswith("executablepath="):
                exe_path = line.split("=", 1)[1].strip()
                if exe_path:
                    cfg = os.path.join(os.path.dirname(exe_path), "storage.cfg")
                    if os.path.isfile(cfg):
                        return cfg
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Fallback: probe common Steam install paths across drive letters and
    # return the install with the most recent DDNet-Server.exe modification
    # time — that's almost always the one the user is actually using
    # (Steam updates the active library copy).
    candidate_relpaths = [
        r"steamapps\common\DDraceNetwork\ddnet",
        r"SteamLibrary\steamapps\common\DDraceNetwork\ddnet",
    ]
    drives = [f"{d}:\\" for d in "CDEFGHIJKLMNOPQRSTUVWXYZ"]
    found_installs: list[tuple[float, str]] = []  # (mtime, storage.cfg path)
    for drive in drives:
        for rel in candidate_relpaths:
            install_dir = os.path.join(drive, rel)
            cfg = os.path.join(install_dir, "storage.cfg")
            exe = os.path.join(install_dir, "DDNet-Server.exe")
            if os.path.isfile(cfg) and os.path.isfile(exe):
                try:
                    found_installs.append((os.path.getmtime(exe), cfg))
                except OSError:
                    pass
    if found_installs:
        # Sort by mtime descending — newest first.
        found_installs.sort(key=lambda x: x[0], reverse=True)
        return found_installs[0][1]
    return None


SERVER_STORAGE_CFG_PATH = _resolve_server_storage_cfg()

# Simple in-memory token store (clears on server restart)
TOKENS: set[str] = set()
SYNC_STATUS_LOCK = threading.Lock()
SYNC_STATUS: dict[str, object] = {
    "running": False,
    "mode": None,
    "stage": "idle",
    "message": "Idle",
    "startedAt": None,
    "finishedAt": None,
    "success": None,
    "error": None,
    "progress": None,
    "counts": None,
    "summary": None,
    "logs": [],
}


def append_sync_log(message: str) -> None:
    with SYNC_STATUS_LOCK:
        logs = list(SYNC_STATUS.get("logs", []))
        logs.append({
            "timestamp": int(time.time() * 1000),
            "message": message,
        })
        SYNC_STATUS["logs"] = logs[-40:]


def get_sync_status_snapshot() -> dict[str, object]:
    with SYNC_STATUS_LOCK:
        return copy.deepcopy(SYNC_STATUS)


def set_sync_status(**updates: object) -> None:
    with SYNC_STATUS_LOCK:
        SYNC_STATUS.update(updates)


def run_sync_job(mode: str) -> None:
    def on_progress(payload: dict[str, object]) -> None:
        stage = str(payload.get("stage", "sync"))
        message = str(payload.get("message", "Working"))
        append_sync_log(f"[{stage}] {message}")
        set_sync_status(
            stage=stage,
            message=message,
            progress=payload.get("progress"),
            counts=payload.get("counts"),
        )

    try:
        summary = sync_ddnet_maps(
            mode=mode,
            callback=on_progress,
            register_with_server=True,
            storage_cfg_path=SERVER_STORAGE_CFG_PATH,
        )
        if SERVER_STORAGE_CFG_PATH:
            append_sync_log(f"Wrote storage.cfg to {SERVER_STORAGE_CFG_PATH}")
        append_sync_log("Sync completed successfully")
        set_sync_status(
            running=False,
            success=True,
            error=None,
            finishedAt=int(time.time() * 1000),
            summary=summary,
            stage="done",
            message="Sync completed",
            progress=None,
            counts=None,
        )
    except Exception as exc:
        append_sync_log(f"Sync failed: {exc}")
        set_sync_status(
            running=False,
            success=False,
            error=str(exc),
            finishedAt=int(time.time() * 1000),
            stage="error",
            message="Sync failed",
            progress=None,
            counts=None,
        )


def start_sync_job(mode: str) -> dict[str, object]:
    with SYNC_STATUS_LOCK:
        if SYNC_STATUS.get("running"):
            return copy.deepcopy(SYNC_STATUS)

        SYNC_STATUS.update({
            "running": True,
            "mode": mode,
            "stage": "queued",
            "message": f"Starting {mode} sync",
            "startedAt": int(time.time() * 1000),
            "finishedAt": None,
            "success": None,
            "error": None,
            "progress": None,
            "counts": None,
            "summary": None,
            "logs": [],
        })

    append_sync_log(f"Queued {mode} sync")
    worker = threading.Thread(target=run_sync_job, args=(mode,), daemon=True)
    worker.start()
    return get_sync_status_snapshot()


def sanitize_map_basename(name: str) -> str:
    r"""Sanitize base filename similar to Trashmap PHP:
    - remove characters not in [\w\s\d\-_~,;:\[\]\(\).\\]
    - trim whitespace
    """
    # Remove disallowed characters
    cleaned = re.sub(r"[^\w\s\d\-_~,;:\[\]\(\).\\]", "", name)
    # Trim whitespace
    cleaned = re.sub(r"\s*(.*[^\s]|)\s*", r"\1", cleaned)
    return cleaned


def ensure_unique_path(folder: str, base: str, ext: str) -> tuple[str, str]:
    """Return (final_filename, full_path) ensuring uniqueness by appending (n)."""
    filename = f"{base}{ext}"
    full = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(full):
        filename = f"{base} ({counter}){ext}"
        full = os.path.join(folder, filename)
        counter += 1
    return filename, full


class MapServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set the directory to the location of the server.py file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=current_dir, **kwargs)

    def end_headers(self):
        # Add CORS headers to all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle OPTIONS method for CORS preflight requests
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'')

    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/test':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "message": "Server is working"}).encode())
            return
        elif self.path == '/list-maps':
            maps_folder = MAPS_FOLDER
            print(f"Looking for maps in: {maps_folder}")
            maps = []
            if os.path.exists(maps_folder):
                print(f"Directory exists, checking for .map files")
                for file in os.listdir(maps_folder):
                    if file.endswith('.map'):
                        file_path = os.path.join(maps_folder, file)
                        maps.append({
                            'name': file,
                            'modified': os.path.getmtime(file_path) * 1000,  # Convert to milliseconds
                            'size': os.path.getsize(file_path)
                        })
                print(f"Found {len(maps)} map files")
            else:
                print(f"Directory does not exist: {maps_folder}")
            # Sort maps by modification time, newest first (reversed order)
            maps.sort(key=lambda x: x['modified'], reverse=True)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(maps).encode())
            return
        
        elif self.path == '/get-logs':
            # Return last 500 lines of ddnet_control.log
            log_path = os.path.join(MAPS_FOLDER, 'ddnet_control.log')
            try:
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        # Get last 500 lines
                        last_lines = lines[-500:] if len(lines) > 500 else lines
                        content = ''.join(last_lines)
                else:
                    content = "Log file not found at: " + log_path
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error reading log: {str(e)}".encode())
            return
            
        elif self.path.startswith('/download/'):
            try:
                # URL decode the map name to handle spaces and special characters
                map_name = self.path[9:]  # Remove '/download/' prefix
                map_name = unquote(map_name)  # Properly decode URL
                
                # Get the maps folder path
                maps_folder = MAPS_FOLDER
                if not os.path.exists(maps_folder):
                    os.makedirs(maps_folder, exist_ok=True)
                
                # Only check for parent directory traversal
                if '..' in map_name:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid file name"}).encode())
                    return
                
                # Normalize the path to handle any path separators
                map_name = os.path.basename(map_name)  # Get just the filename part
                file_path = os.path.join(maps_folder, map_name)
                
                print(f"Attempting to download: {file_path}")  # Debug log
                
                if not os.path.exists(file_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "File not found",
                        "path": file_path,
                        "available_maps": os.listdir(maps_folder) if os.path.exists(maps_folder) else []
                    }).encode())
                    return
                    
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{quote(map_name)}"')
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": str(e),
                    "path": file_path if 'file_path' in locals() else "unknown",
                    "maps_folder": maps_folder if 'maps_folder' in locals() else "unknown"
                }).encode())
            return
            
        elif self.path == '/issue-token':
            # Create a simple per-session upload token
            token = str(uuid.uuid4())
            TOKENS.add(token)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"token": token}).encode())
            return
            
        elif self.path == '/list-folders':
            # List subfolders in the DDNet maps directory
            folders = []
            if os.path.exists(MAPS_FOLDER):
                for item in os.listdir(MAPS_FOLDER):
                    item_path = os.path.join(MAPS_FOLDER, item)
                    if os.path.isdir(item_path):
                        # Count .map files in folder
                        map_count = len([f for f in os.listdir(item_path) if f.endswith('.map')])
                        folders.append({
                            'name': item,
                            'mapCount': map_count
                        })
            folders.sort(key=lambda x: x['name'].lower())
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(folders).encode())
            return
            
        elif self.path.startswith('/list-maps-folder/'):
            # List maps in a specific subfolder
            folder_name = unquote(self.path[18:])  # Remove '/list-maps-folder/' prefix
            
            # Security check
            if '..' in folder_name:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid folder name"}).encode())
                return
            
            folder_path = os.path.join(MAPS_FOLDER, folder_name)
            maps = []
            
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    if file.endswith('.map'):
                        file_path = os.path.join(folder_path, file)
                        maps.append({
                            'name': file,
                            'folder': folder_name,
                            'modified': os.path.getmtime(file_path) * 1000,
                            'size': os.path.getsize(file_path)
                        })
                maps.sort(key=lambda x: x['modified'], reverse=True)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(maps).encode())
            return
            
        elif self.path.startswith('/download-folder/'):
            # Download map from a specific subfolder
            try:
                path_parts = self.path[17:]  # Remove '/download-folder/' prefix
                path_parts = unquote(path_parts)
                
                # Split into folder and filename
                parts = path_parts.split('/', 1)
                if len(parts) != 2:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid path format"}).encode())
                    return
                
                folder_name, map_name = parts
                
                # Security check
                if '..' in folder_name or '..' in map_name:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid path"}).encode())
                    return
                
                file_path = os.path.join(MAPS_FOLDER, folder_name, map_name)
                
                if not os.path.exists(file_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "File not found", "path": file_path}).encode())
                    return
                
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{quote(map_name)}"')
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        elif self.path == '/sync-status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_sync_status_snapshot()).encode())
            return

        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/upload':
            # Optional token check: allow if valid token provided
            provided_token = self.headers.get('X-Upload-Token')
            if provided_token and provided_token not in TOKENS:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid token"}).encode())
                return

            # Parse the form data (stdlib multipart parser — cgi.FieldStorage
            # was removed in Python 3.13; we hand-parse the one "file" field).
            try:
                content_length = int(self.headers.get('Content-Length', '0'))
            except (TypeError, ValueError):
                content_length = 0
            content_type = self.headers.get('Content-Type', '')

            orig_name, file_stream = _parse_multipart_file_upload(
                self.rfile, content_type, content_length
            )

            if file_stream is None or not orig_name:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No file field provided"}).encode())
                return

            # Enforce .map extension
            base, ext = os.path.splitext(orig_name)
            if ext.lower() != '.map':
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Filename must end with .map"}).encode())
                return

            # Sanitize base name similar to Trashmap
            sanitized = sanitize_map_basename(base)
            if not sanitized:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Filename had to be adjusted and is now empty"}).encode())
                return

            # Get client IP for user-specific mapping
            client_ip = self.client_address[0]
            # Clean IP for filename (replace dots with underscores)
            safe_ip = client_ip.replace('.', '_').replace(':', '_')
            
            # Create user-specific filename: originalname_userip.map
            user_specific_filename = f"{sanitized}_{safe_ip}.map"
            final_filename = user_specific_filename
            
            # Prepare target folder and user-specific path (overwrite user's existing file)
            os.makedirs(MAPS_FOLDER, exist_ok=True)
            final_path = os.path.join(MAPS_FOLDER, final_filename)

            # Stream save with size enforcement and retry logic
            total_written = 0
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    with open(final_path, 'wb') as f:
                        # Reset file pointer for retries
                        file_stream.seek(0)
                        total_written = 0
                        
                        while True:
                            chunk = file_stream.read(1024 * 1024)
                            if not chunk:
                                break
                            total_written += len(chunk)
                            if total_written > MAP_MAX_SIZE_BYTES:
                                raise ValueError("Maximum file size exceeded")
                            f.write(chunk)
                    
                    # If we reach here, file was written successfully
                    break
                    
                except PermissionError as pe:
                    if attempt < max_retries - 1:
                        print(f"File locked, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Final attempt failed
                        self.send_response(423)  # HTTP 423 Locked
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "error": f"File is locked by another process: {final_filename}",
                            "details": "The file might be open in DDNet client or another application. Please close it and try again.",
                            "path": final_path
                        }).encode())
                        return
                        
                except ValueError as ve:
                    # Delete partial file
                    try:
                        if os.path.exists(final_path):
                            os.remove(final_path)
                    except Exception:
                        pass
                    self.send_response(413)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": str(ve),
                        "limitBytes": MAP_MAX_SIZE_BYTES
                    }).encode())
                    return

            # Build response message indicating user-specific mapping
            message = f"File uploaded as your personal map: {final_filename}"
            if final_filename != f"{orig_name.replace('.map', '')}_{safe_ip}.map":
                message = f"Filename adjusted and saved as your personal map: {final_filename}"

            # Automatically simulate double-click after successful upload (hidden, no CMD window)
            try:
                print(f"Auto-simulating click on: {final_path}")
                # Use ShellExecute via PowerShell to open file silently (no visible CMD)
                subprocess.Popen(
                    ['powershell', '-WindowStyle', 'Hidden', '-Command', f'Start-Process "{final_path}"'],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"Successfully triggered map loading for {final_filename}")
            except Exception as e:
                print(f"Error auto-simulating click: {e}")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "filename": final_filename,
                "originalName": orig_name,  # Original filename without IP suffix
                "message": message
            }).encode())
            
    
        elif self.path == '/check-file':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            file_name = data.get('fileName')
            last_modified = data.get('lastModified')
            
            # Validate file name
            if not file_name:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing fileName parameter",
                    "changed": False
                }).encode())
                return
            
            # Get the full path in maps folder
            maps_folder = os.path.expanduser('~\\AppData\\Roaming\\DDNet\\maps\\maps from site')
            full_path = os.path.join(maps_folder, file_name)
            
            response = {"changed": False}
            
            if os.path.exists(full_path):
                try:
                    current_mtime = os.path.getmtime(full_path) * 1000  # Convert to milliseconds
                    print(f"Checking {file_name}: last_modified={last_modified}, current_mtime={current_mtime}")
                    
                    if not last_modified or current_mtime > last_modified:
                        with open(full_path, 'rb') as f:
                            content = f.read()
                        response = {
                            "changed": True,
                            "lastModified": current_mtime,
                            "content": list(content)  # Convert bytes to list for JSON serialization
                        }
                except Exception as e:
                    print(f"Error reading file {file_name}: {e}")
                    response = {
                        "changed": False,
                        "error": str(e)
                    }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif self.path == '/simulate-click':
            # Read the JSON body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Get the file path
            file_path = data.get('filePath')
            print(f"Simulating click on: {file_path}")
            
            if file_path and os.path.exists(file_path):
                try:
                    # Simulate double click silently (no visible CMD window)
                    subprocess.Popen(
                        ['powershell', '-WindowStyle', 'Hidden', '-Command', f'Start-Process "{file_path}"'],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print(f"Successfully triggered: {os.path.basename(file_path)}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": f"Simulated click on {os.path.basename(file_path)}"}).encode())
                except Exception as e:
                    print(f"Error running explorer: {e}")
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": f"Failed to open file: {str(e)}"}).encode())
            else:
                print(f"File not found: {file_path}")
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "File not found", "path": file_path}).encode())
        elif self.path == '/find-map':
            # Find a map file by name in DDNet maps folder (recursive)
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            file_name = data.get('fileName', '').strip()
            
            if not file_name:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing fileName"}).encode())
                return
            
            # Search recursively in maps folder
            found_paths = []
            for root, dirs, files in os.walk(MAPS_FOLDER):
                if file_name in files:
                    found_paths.append(os.path.join(root, file_name))
            
            if len(found_paths) == 1:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"path": found_paths[0]}).encode())
            elif len(found_paths) > 1:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"paths": found_paths}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"path": None, "notFound": True}).encode())
            return
            
        elif self.path == '/browse-file':
            # Open native Windows file picker and return selected path
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                # Hide the main tkinter window
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                # Open file dialog
                file_path = filedialog.askopenfilename(
                    title="Select .map file to watch",
                    initialdir=MAPS_FOLDER,
                    filetypes=[("Map files", "*.map"), ("All files", "*.*")]
                )
                
                root.destroy()
                
                if file_path:
                    # Convert forward slashes to backslashes for Windows
                    file_path = file_path.replace('/', '\\')
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"path": file_path}).encode())
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"path": None, "cancelled": True}).encode())
                    
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return
            
        elif self.path == '/start-auto-update':
            # One-click auto-update: start PowerShell watcher directly
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            file_path = data.get('filePath', '').strip()
            server_url = data.get('serverUrl', 'http://localhost:8299')
            
            if not file_path:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing filePath"}).encode())
                return
            
            if not os.path.exists(file_path):
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"File not found: {file_path}"}).encode())
                return
            
            try:
                # Download the auto_uploader.ps1 script to a temp location
                script_dir = os.path.dirname(os.path.abspath(__file__))
                ps1_path = os.path.join(script_dir, 'auto_uploader.ps1')
                
                if not os.path.exists(ps1_path):
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "auto_uploader.ps1 not found on server"}).encode())
                    return
                
                # Start PowerShell with the auto-uploader script in a new visible window
                # The ps1 script expects: -File <mapPath> -Server <serverUrl>
                # Use -Command to invoke the script with its parameters
                ps_command = f'& "{ps1_path}" -File "{file_path}" -Server "{server_url}"'
                cmd = [
                    'powershell',
                    '-NoProfile',
                    '-ExecutionPolicy', 'Bypass',
                    '-NoExit',
                    '-Command', ps_command
                ]
                
                # Start in a new console window so user can see the watcher
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=script_dir
                )
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"Auto-update watcher started for {os.path.basename(file_path)}"
                }).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif self.path == '/sync-types':
            content_length = int(self.headers.get('Content-Length', '0'))
            data = {}
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

            mode = str(data.get('mode', 'all')).strip().lower() or 'all'
            if mode not in {'all', 'official', 'testing'}:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid sync mode: {mode}"}).encode())
                return

            current_status = get_sync_status_snapshot()
            if current_status.get("running"):
                self.send_response(409)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(current_status).encode())
                return

            started = start_sync_job(mode)
            self.send_response(202)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(started).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid endpoint"}).encode())

def get_local_ip():
    try:
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def copy_to_clipboard(text):
    """Copy text to clipboard using clip.exe (reliable on Windows)"""
    try:
        # Use clip.exe - most reliable method on Windows
        process = subprocess.Popen(
            ['clip'],
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        process.communicate(input=text.encode('utf-8'))
        return True
    except Exception as e:
        print(f"Clipboard error: {e}")
        return False


def create_tray_icon(server_thread):
    # Load and create the icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'map.ico')
    image = Image.open(icon_path)
    
    # Get the local IP for the menu
    local_ip = get_local_ip()
    local_url = f'http://localhost:8299'
    public_url = f'http://185.60.44.131:8299'
    
    def on_clicked(icon, item):
        item_str = str(item)
        if item_str == "Open Local":
            webbrowser.open(local_url)
        elif item_str == "Open Public":
            webbrowser.open(public_url)
        elif item_str == f"Copy: {local_url}":
            if copy_to_clipboard(local_url):
                print(f"Copied to clipboard: {local_url}")
        elif item_str == f"Copy: {public_url}":
            if copy_to_clipboard(public_url):
                print(f"Copied to clipboard: {public_url}")
        elif item_str == "Restart":
            print("Restarting server...")
            import sys
            # Start new instance using a batch file approach for clean restart
            script_path = os.path.abspath(sys.argv[0])
            script_dir = os.path.dirname(script_path)
            python_exe = sys.executable
            
            # Create a temporary batch file to restart
            bat_content = f'''@echo off
timeout /t 2 /nobreak >nul
cd /d "{script_dir}"
start "" "{python_exe}" "{script_path}"
del "%~f0"
'''
            bat_path = os.path.join(script_dir, '_restart.bat')
            with open(bat_path, 'w') as f:
                f.write(bat_content)
            
            # Run the batch file detached
            subprocess.Popen(
                ['cmd', '/c', bat_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=script_dir
            )
            icon.stop()
            os._exit(0)
        elif item_str == "Exit":
            print("Shutting down server...")
            icon.stop()
            os._exit(0)
    
    # Create the menu with submenus
    menu = (
        pystray.MenuItem("Open Local", on_clicked),
        pystray.MenuItem("Open Public", on_clicked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Copy: {local_url}", on_clicked),
        pystray.MenuItem(f"Copy: {public_url}", on_clicked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart", on_clicked),
        pystray.MenuItem("Exit", on_clicked)
    )
    
    # Create the icon
    icon = pystray.Icon("DDNet Map Server", image, "DDNet Map Server", menu)
    return icon

def run_server():
    # Change working directory to the location of server.py
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Bind to all interfaces
    server_address = ('0.0.0.0', 8299)
    httpd = FastHTTPServer(server_address, MapServerHandler)

    # Opportunistic HTTPS: if cert.pem and key.pem sit next to server.py,
    # wrap the socket with TLS. Required so the editor PC's browser can use
    # the File System Access API (which needs a secure context). Generated
    # by `make_cert.bat` at the repo root. Falls back to plain HTTP if absent.
    _server_dir = os.path.dirname(os.path.abspath(__file__))
    _cert_path = os.path.join(_server_dir, 'cert.pem')
    _key_path = os.path.join(_server_dir, 'key.pem')
    using_https = os.path.exists(_cert_path) and os.path.exists(_key_path)
    if using_https:
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=_cert_path, keyfile=_key_path)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            print(f'TLS enabled (cert: {_cert_path})')
        except Exception as _tls_err:
            print(f'[WARN] TLS init failed ({_tls_err}); continuing on plain HTTP')
            using_https = False

    scheme = 'https' if using_https else 'http'
    local_ip = get_local_ip()
    print(f'\nServer running on:')
    print(f' - Local:   {scheme}://localhost:{server_address[1]}')
    print(f' - Network: {scheme}://{local_ip}:{server_address[1]}')
    print(f'\nServing files from: {os.getcwd()}')
    print('\nTo access from other devices on your network, use the Network URL')
    
    # Create and start server in a non-daemon thread so the process stays
    # alive even if the tray icon exits or fails to start.
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = False
    server_thread.start()
    
    # Try to hide console window on Windows
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        print("Console window hidden")
    except Exception:
        print("Could not hide console window")
    
    print('\nMinimizing to system tray...')
    
    # Create and run tray icon.
    # icon.run() blocks the main thread while the tray is active.
    # If it returns or crashes, keep the HTTP server alive anyway by
    # falling back to a simple keep-alive loop so the process doesn't exit.
    icon = create_tray_icon(server_thread)
    try:
        icon.run()
    except Exception as e:
        print(f"Tray icon error: {e}")

    # icon.run() returned (tray exited or failed) — keep the HTTP server
    # alive so the shortcut still works even without a tray icon.
    print("Tray icon exited — server still running on http://localhost:8299")
    try:
        server_thread.join()
    except KeyboardInterrupt:
        httpd.shutdown()

if __name__ == '__main__':
    # pythonw.exe (the shortcut uses this) detaches stdout/stderr to None,
    # so every `print()` in the request handlers crashes with
    # "'NoneType' object has no attribute 'write'" and the HTTP handler
    # silently dies mid-request. Swap to /dev/null-like sinks so prints
    # are harmless no-ops.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8', errors='replace')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8', errors='replace')

    # Always log crashes to a file so we can diagnose "tray flashes and dies" issues.
    # Runs regardless of --no-tray mode.
    import traceback
    CRASH_LOG = os.path.join(os.environ.get("APPDATA", os.path.dirname(__file__)),
                             "DDNet", "maps", "map-manager-crash.log")
    try:
        os.makedirs(os.path.dirname(CRASH_LOG), exist_ok=True)
    except Exception:
        CRASH_LOG = os.path.join(os.path.dirname(__file__), "map-manager-crash.log")

    def _record_crash(exc_type, exc_value, exc_tb):
        try:
            with open(CRASH_LOG, "a", encoding="utf-8") as fh:
                fh.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=fh)
        except Exception:
            pass

    # Hook both thread-level and main-thread exceptions
    sys.excepthook = _record_crash
    try:
        threading.excepthook = lambda args: _record_crash(args.exc_type, args.exc_value, args.exc_traceback)
    except Exception:
        pass

    try:
        if os.environ.get("DDNETCONTROL_NO_TRAY") == "1":
            # Headless mode for automated verification. Runs the HTTP server
            # in the foreground without tray icon or console-hiding side effects.
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            server_address = ('0.0.0.0', 8299)
            httpd = FastHTTPServer(server_address, MapServerHandler)
            print(f"[no-tray] Serving on http://localhost:{server_address[1]}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
        else:
            run_server()
    except BaseException:
        _record_crash(*sys.exc_info())
        raise
