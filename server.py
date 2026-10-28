"""
ReMate Website Server — Python 3.8+ thuần, KHÔNG cần cài thư viện ngoài.
Chạy:   python server.py      → http://localhost:3000
Admin:  http://localhost:3000/admin.html  (ADMIN_USER / ADMIN_PASSWORD qua biến môi trường)

Chức năng:
  - Phục vụ file tĩnh trong ./public
  - REST API cho sản phẩm (products) và dự án (projects), lưu vào ./data/*.json
  - Upload ảnh (dataURL base64) → lưu vào ./public/uploads
  - Cập nhật thời gian thực bằng Server-Sent Events (SSE): GET /api/stream
"""
import base64
import json
import mimetypes
import os
import queue
import re
import secrets
import threading
import time
import unicodedata
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

# ---------------- Cấu hình ----------------
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "3000"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "remate@2026")  # ĐỔI khi triển khai thật

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")).resolve()
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", PUBLIC_DIR / "uploads")).resolve()
TYPES = ("products", "projects")
MAX_BODY = 25 * 1024 * 1024  # 25MB / request
MAX_IMAGES = 12
SESSION_SECONDS = 8 * 60 * 60

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".md": "text/plain; charset=utf-8",
}


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ---------------- Lưu trữ JSON (khóa ghi để an toàn đa luồng) ----------------
_data_lock = threading.Lock()


def data_file(kind):
    return DATA_DIR / f"{kind}.json"


def read_all(kind):
    try:
        return json.loads(data_file(kind).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_all(kind, items):
    tmp = data_file(kind).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, data_file(kind))  # ghi nguyên tử


# ---------------- Phiên đăng nhập ----------------
_sessions = {}  # token -> thời điểm hết hạn
_sess_lock = threading.Lock()


def new_session():
    token = secrets.token_hex(24)
    with _sess_lock:
        _sessions[token] = time.time() + SESSION_SECONDS
    return token


def check_token(token):
    with _sess_lock:
        exp = _sessions.get(token)
        if not exp or exp < time.time():
            _sessions.pop(token, None)
            return False
        return True


def drop_session(token):
    with _sess_lock:
        _sessions.pop(token, None)


# ---------------- Realtime SSE ----------------
_clients = set()
_clients_lock = threading.Lock()


def broadcast(event, payload):
    msg = f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
    with _clients_lock:
        for q in list(_clients):
            q.put(msg)


# ---------------- Tiện ích ----------------
def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


def slugify(s):
    s = str(s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]
    return s or "item"


def text(v, max_len=5000):
    return str(v if v is not None else "").strip()[:max_len]


DATAURL_RE = re.compile(r"^data:image/(png|jpe?g|webp|gif);base64,(.+)$", re.I | re.S)


def save_images(images):
    """Ảnh: giữ nguyên URL có sẵn (/uploads/..., /img/..., http...) hoặc lưu dataURL base64 thành file."""
    if not isinstance(images, list):
        return []
    result = []
    for img in images[:MAX_IMAGES]:
        img = str(img or "").strip()
        m = DATAURL_RE.match(img)
        if not m:
            if img:
                result.append(img)
            continue
        ext = m.group(1).lower().replace("jpeg", "jpg")
        name = f"{int(time.time() * 1000)}-{secrets.token_hex(4)}.{ext}"
        try:
            (UPLOAD_DIR / name).write_bytes(base64.b64decode(m.group(2)))
        except (ValueError, OSError):
            raise ApiError("Ảnh không hợp lệ")
        result.append(f"/uploads/{name}")
    return result


def delete_uploads(paths):
    for p in paths or []:
        if isinstance(p, str) and p.startswith("/uploads/"):
            f = (UPLOAD_DIR / p[len("/uploads/"):]).resolve()
            if f.parent == UPLOAD_DIR:
                try:
                    f.unlink()
                except OSError:
                    pass


def normalize(kind, b, old=None):
    """Chuẩn hóa dữ liệu theo MẪU BÀI ĐĂNG."""
    if not isinstance(b, dict):
        raise ApiError("Dữ liệu không hợp lệ")
    item = dict(old or {})
    item.update({
        "title": text(b.get("title"), 200),
        "category": text(b.get("category"), 100),
        "summary": text(b.get("summary"), 500),
        "content": text(b.get("content"), 20000),
        "images": save_images(b.get("images")),
        "featured": bool(b.get("featured")),
        "published": b.get("published") is not False,
    })
    if not item["title"]:
        raise ApiError("Tên không được để trống")
    if kind == "products":
        specs = b.get("specs") if isinstance(b.get("specs"), list) else []
        item.update({
            "condition": text(b.get("condition"), 100),   # Tình trạng
            "price": text(b.get("price"), 100),           # Giá hoặc "Liên hệ"
            "quantity": text(b.get("quantity"), 100),
            "origin": text(b.get("origin"), 100),
            "specs": [{"key": text(s.get("key"), 100), "value": text(s.get("value"), 300)}
                      for s in specs if isinstance(s, dict) and text(s.get("key"))][:30],
        })
    else:
        item.update({
            "client": text(b.get("client"), 200),
            "location": text(b.get("location"), 200),
            "time": text(b.get("time"), 100),
            "scope": text(b.get("scope"), 1000),
            "result": text(b.get("result"), 2000),
        })
    return item


# ---------------- HTTP Handler ----------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ReMate/1.0"

    # ----- phản hồi -----
    def send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def load_raw_body(self):
        """Đọc hết body ngay đầu request để kết nối keep-alive luôn sạch."""
        self._raw = b""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            self.close_connection = True
            raise ApiError("Dữ liệu quá lớn (tối đa 25MB)", 413)
        if length:
            self._raw = self.rfile.read(length)

    def read_body(self):
        raw = getattr(self, "_raw", b"")
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError("JSON không hợp lệ")

    def token(self):
        return (self.headers.get("Authorization") or "").replace("Bearer ", "", 1).strip()

    def is_auth(self):
        return check_token(self.token())

    # ----- định tuyến -----
    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_DELETE(self):
        self.route("DELETE")

    def route(self, method):
        path = urlparse(self.path).path
        try:
            self.load_raw_body()
            if path.startswith("/api/"):
                return self.api(method, path)
            if method != "GET":
                raise ApiError("Phương thức không hỗ trợ", 405)
            return self.static(path)
        except ApiError as e:
            self.send_json(e.status, {"error": str(e)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # lỗi không lường trước
            self.log_error("Lỗi: %r", e)
            try:
                self.send_json(500, {"error": "Lỗi máy chủ"})
            except OSError:
                pass

    # ----- API -----
    def api(self, method, path):
        parts = [p for p in path.split("/") if p]  # ['api', kind, id]
        name = parts[1] if len(parts) > 1 else ""

        if name == "stream" and method == "GET":
            return self.stream()
        if name == "login" and method == "POST":
            b = self.read_body()
            if b.get("username") == ADMIN_USER and b.get("password") == ADMIN_PASSWORD:
                return self.send_json(200, {"token": new_session()})
            raise ApiError("Sai tên đăng nhập hoặc mật khẩu", 401)
        if name == "logout" and method == "POST":
            drop_session(self.token())
            return self.send_json(200, {"ok": True})
        if name == "me":
            ok = self.is_auth()
            return self.send_json(200 if ok else 401, {"ok": ok})

        if name not in TYPES:
            raise ApiError("Không tìm thấy API", 404)
        kind = name
        item_id = unquote(parts[2]) if len(parts) > 2 else None
        admin = self.is_auth()

        if method == "GET":
            items = read_all(kind)
            if item_id:
                it = next((x for x in items if x.get("id") == item_id or x.get("slug") == item_id), None)
                if not it or (not it.get("published") and not admin):
                    raise ApiError("Không tìm thấy", 404)
                return self.send_json(200, it)
            visible = items if admin else [x for x in items if x.get("published")]
            visible.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
            return self.send_json(200, visible)

        if not admin:
            raise ApiError("Cần đăng nhập admin", 401)
        body = self.read_body()

        with _data_lock:
            items = read_all(kind)
            if method == "POST" and not item_id:
                it = normalize(kind, body)
                it["id"] = secrets.token_hex(6)
                it["slug"] = f"{slugify(it['title'])}-{it['id'][:4]}"
                it["createdAt"] = it["updatedAt"] = now_iso()
                items.append(it)
                write_all(kind, items)
                action, status = "create", 201
            elif method == "PUT" and item_id:
                idx = next((i for i, x in enumerate(items) if x.get("id") == item_id), -1)
                if idx < 0:
                    raise ApiError("Không tìm thấy", 404)
                old_imgs = list(items[idx].get("images") or [])
                it = normalize(kind, body, items[idx])
                it["updatedAt"] = now_iso()
                items[idx] = it
                write_all(kind, items)
                delete_uploads([p for p in old_imgs if p not in it["images"]])  # ảnh bị gỡ
                action, status = "update", 200
            elif method == "DELETE" and item_id:
                it = next((x for x in items if x.get("id") == item_id), None)
                if not it:
                    raise ApiError("Không tìm thấy", 404)
                write_all(kind, [x for x in items if x.get("id") != item_id])
                delete_uploads(it.get("images"))
                broadcast("change", {"type": kind, "action": "delete", "id": item_id})
                return self.send_json(200, {"ok": True})
            else:
                raise ApiError("Phương thức không hỗ trợ", 405)

        broadcast("change", {"type": kind, "action": action, "id": it["id"]})
        return self.send_json(status, it)

    def stream(self):
        """Server-Sent Events: giữ kết nối, đẩy sự kiện 'change' + ping 25 giây/lần."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")  # tắt buffer Nginx
        self.end_headers()
        self.close_connection = True
        q = queue.Queue()
        with _clients_lock:
            _clients.add(q)
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=25)
                except queue.Empty:
                    msg = ": ping\n\n"
                self.wfile.write(msg.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _clients_lock:
                _clients.discard(q)

    # ----- File tĩnh -----
    def static(self, path):
        p = unquote(path)
        if p == "/":
            p = "/index.html"
        if p.startswith("/uploads/"):
            base, rel = UPLOAD_DIR, p[len("/uploads/"):]
        else:
            base, rel = PUBLIC_DIR, p.lstrip("/")
        full = (base / rel).resolve()
        if base.resolve() not in full.parents and full != base.resolve():
            raise ApiError("Forbidden", 403)
        if not full.is_file():
            page = PUBLIC_DIR / "404.html"
            body = page.read_bytes() if page.is_file() else b"404"
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        ctype = MIME.get(full.suffix.lower()) or mimetypes.guess_type(str(full))[0] or "application/octet-stream"
        body = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=604800" if p.startswith("/uploads/") else "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if "/api/stream" not in (self.path or ""):
            super().log_message(fmt, *args)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    httpd = Server((HOST, PORT), Handler)
    print(f"ReMate website: http://localhost:{PORT}")
    print(f"Trang quản trị: http://localhost:{PORT}/admin.html  (user: {ADMIN_USER})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ.")
