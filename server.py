"""
ReMate Website Server — Python 3; cloud image storage requires SDKs in requirements.txt.
Chạy:   python server.py      → http://localhost:3000
Admin:  http://localhost:3000/admin.html  (ADMIN_USER / ADMIN_PASSWORD qua biến môi trường)

Chức năng:
  - Phục vụ file tĩnh trong ./public
  - REST API cho sản phẩm/dự án/đối tác/dịch vụ, JSON lưu B2 (mặc định) hoặc local qua DATA_STORAGE
  - Upload ảnh (dataURL base64) → B2/local/Firebase/Cloudinary theo IMAGE_STORAGE
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

from dotenv import load_dotenv

# Load local .env before importing image_storage (it reads IMAGE_STORAGE at import time).
# Existing OS/Render environment variables always take precedence over .env.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=False)

from image_storage import (
    IMAGE_STORAGE, LOCAL_FOLDERS, ImageStorageError, delete_image, signed_image_url, store_image
)
from data_storage import (DATA_STORAGE, DataStorageError, initialize as initialize_data,
                          read_all, write_all)

# ---------------- Cấu hình ----------------
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "3000"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "remate@2026")  # ĐỔI khi triển khai thật

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
UPLOAD_DIR = LOCAL_FOLDERS["uploads"]
ALBUM_DIR = LOCAL_FOLDERS["album"]
EXPERTISE_DIR = LOCAL_FOLDERS["expertise"]
SERVICE_COVERS_DIR = LOCAL_FOLDERS["service-covers"]
MAX_SERVICE_COVER_BYTES = 6 * 1024 * 1024  # 6 MiB per image
MAX_EXPERTISE_IMAGE_BYTES = 5 * 1024 * 1024  # Mỗi ô dùng một ảnh ≤ 5 MiB
MAX_ALBUM_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MiB/ảnh, không giới hạn tổng số ảnh
TYPES = ("products", "projects", "partners", "services")
PRODUCT_CATEGORIES = ("Phế liệu", "Vật tư", "Máy móc - thiết bị")
PROJECT_CATEGORIES = ("Bảo trì - bảo dưỡng", "Thiết kế - gia công", "Cải tiến - cải tạo", "Tư vấn - giải pháp")
SERVICE_GROUPS = (
    "Kiểm tra, bảo trì thiết bị tại nhà máy",
    "Thiết kế, gia công, chế tạo máy theo yêu cầu",
    "Đo đạc, tư vấn, triển khai các giải pháp tiết kiệm năng lượng",
)
MAX_BODY = 25 * 1024 * 1024  # 25MB / request
MAX_IMAGES = 12
SESSION_SECONDS = 8 * 60 * 60

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALBUM_DIR.mkdir(parents=True, exist_ok=True)
EXPERTISE_DIR.mkdir(parents=True, exist_ok=True)
SERVICE_COVERS_DIR.mkdir(parents=True, exist_ok=True)

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


# ---------------- JSON data: B2 by default, local as an optional fallback ----------------
# One lock protects mutations across HTTP threads in this ONE Python process.
# Do not run multiple processes or Render replicas writing the same JSON objects.
_data_lock = threading.Lock()


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
    """Giữ URL cũ, lưu ảnh dataURL mới tại provider đang chọn."""
    if not isinstance(images, list):
        return []
    result = []
    created = []
    try:
        for img in images[:MAX_IMAGES]:
            img = str(img or "").strip()
            m = DATAURL_RE.match(img)
            if not m:
                if img:
                    result.append(img)
                continue
            ext = m.group(1).lower().replace("jpeg", "jpg")
            try:
                binary = base64.b64decode(m.group(2), validate=True)
            except (ValueError, base64.binascii.Error):
                raise ApiError("Ảnh không hợp lệ")
            if not binary or len(binary) > 8 * 1024 * 1024:
                raise ApiError("Mỗi ảnh phải có dữ liệu và không vượt quá 8 MiB", 413)
            if not image_signature_ok(binary, ext):
                raise ApiError("Định dạng file ảnh không khớp nội dung")
            try:
                new_src = store_image("uploads", binary, ext)
            except ImageStorageError as exc:
                raise ApiError(str(exc), 502) from exc
            created.append(new_src)
            result.append(new_src)
        return result
    except Exception:
        # Nếu ảnh thứ N lỗi thì xóa các ảnh mới được lưu trong cùng lần upload.
        for src in created:
            delete_image(src, "uploads")
        raise


def delete_uploads(paths):
    for p in paths or []:
        delete_image(p, "uploads")


def image_signature_ok(binary, ext):
    return (
        (ext == "jpg" and binary.startswith(b"\xff\xd8\xff")) or
        (ext == "png" and binary.startswith(b"\x89PNG\r\n\x1a\n")) or
        (ext == "webp" and binary.startswith(b"RIFF") and binary[8:12] == b"WEBP") or
        (ext == "gif" and binary[:6] in (b"GIF87a", b"GIF89a"))
    )


def normalize(kind, b, old=None):
    """Chuẩn hóa dữ liệu theo MẪU BÀI ĐĂNG."""
    if not isinstance(b, dict):
        raise ApiError("Dữ liệu không hợp lệ")
    item = dict(old or {})
    # Kiểm tra liên kết và dữ liệu bắt buộc TRƯỚC khi ghi file ảnh.
    if kind == "partners":
        website = text(b.get("website"), 500)
        if website:
            parsed = urlparse(website)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ApiError("Website đối tác phải bắt đầu bằng http:// hoặc https://")
        if not text(b.get("title"), 200):
            raise ApiError("Tên không được để trống")
        if not text(b.get("summary"), 500):
            raise ApiError("Vui lòng nhập mô tả ngắn về đối tác")
    if kind in ("products", "projects"):
        category = text(b.get("category"), 100)
        allowed = PRODUCT_CATEGORIES if kind == "products" else PROJECT_CATEGORIES
        # Cho phép giữ nguyên danh mục cũ khi Ẩn/Hiện bài cũ (PUT từ Admin).
        # Bài mới và những lần đổi danh mục đều phải dùng danh mục quy định.
        unchanged_legacy = old is not None and category == text(old.get("category"), 100)
        if category not in allowed and not unchanged_legacy:
            what = "sản phẩm" if kind == "products" else "dự án"
            raise ApiError(f"Lĩnh vực {what} chỉ được chọn: {', '.join(allowed)}")
    if kind == "services":
        if not text(b.get("title"), 200):
            raise ApiError("Vui lòng nhập tên dịch vụ")
        if not text(b.get("summary"), 500):
            raise ApiError("Vui lòng nhập mô tả ngắn cho dịch vụ")
        if text(b.get("category"), 200) not in SERVICE_GROUPS:
            raise ApiError("Dịch vụ phải thuộc một trong ba nhóm đã quy định")
    item.update({
        "title": text(b.get("title"), 200),
        "category": text(b.get("category"), 100),
        "summary": text(b.get("summary"), 500),
        "content": text(b.get("content"), 20000),
        "images": save_images((b.get("images") or [])[:1] if kind == "partners" and isinstance(b.get("images"), list) else b.get("images")),
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
    elif kind == "partners":
        # Thông tin đối tác hiển thị công khai, logo là ảnh đầu tiên.
        item["website"] = website
    elif kind == "services":
        specs = b.get("specs") if isinstance(b.get("specs"), list) else []
        item["specs"] = [{"key": text(s.get("key"), 100), "value": text(s.get("value"), 300)}
                         for s in specs if isinstance(s, dict) and text(s.get("key"))][:30]
    else:
        item.update({
            "client": text(b.get("client"), 200),
            "location": text(b.get("location"), 200),
            "time": text(b.get("time"), 100),
            "scope": text(b.get("scope"), 1000),
            "result": text(b.get("result"), 2000),
        })
    return item



# ---------------- Album hình ảnh hoạt động (lưu riêng public/album) ----------------
def store_album_image(dataurl):
    """Giới hạn 8 MiB/ảnh, xác minh kiểu ảnh bằng chữ ký file; không nhận SVG."""
    if not isinstance(dataurl, str):
        raise ApiError("Dữ liệu ảnh không hợp lệ")
    m = DATAURL_RE.fullmatch(dataurl.strip())
    if not m:
        raise ApiError("Album chỉ nhận ảnh PNG, JPG, WebP hoặc GIF")
    ext = m.group(1).lower().replace("jpeg", "jpg")
    raw = m.group(2)
    if len(raw) > ((MAX_ALBUM_IMAGE_BYTES + 2) // 3 * 4 + 16):
        raise ApiError("Mỗi ảnh không được vượt quá 8 MB", 413)
    try:
        binary = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ApiError("Nội dung ảnh không hợp lệ")
    if not binary or len(binary) > MAX_ALBUM_IMAGE_BYTES:
        raise ApiError("Mỗi ảnh phải có dữ liệu và không vượt quá 8 MB", 413)
    sig_ok = (
        (ext == "jpg" and binary.startswith(b"\xff\xd8\xff")) or
        (ext == "png" and binary.startswith(b"\x89PNG\r\n\x1a\n")) or
        (ext == "webp" and binary.startswith(b"RIFF") and binary[8:12] == b"WEBP") or
        (ext == "gif" and binary[:6] in (b"GIF87a", b"GIF89a"))
    )
    if not sig_ok:
        raise ApiError("Định dạng file ảnh không khớp với dữ liệu")
    try:
        return store_image("album", binary, ext)
    except ImageStorageError as exc:
        raise ApiError(str(exc), 502) from exc


def delete_album_image(src):
    delete_image(src, "album")

# ---------------- Ảnh biểu tượng 4 lĩnh vực trên trang Giới thiệu ----------------
def store_expertise_image(dataurl):
    """Upload ảnh riêng, xác minh chữ ký và giới hạn dung lượng mỗi file."""
    if not isinstance(dataurl, str):
        raise ApiError("Thiếu file ảnh")
    m = DATAURL_RE.fullmatch(dataurl.strip())
    if not m:
        raise ApiError("Chỉ hỗ trợ JPG, PNG, WebP hoặc GIF")
    ext = m.group(1).lower().replace("jpeg", "jpg")
    encoded = m.group(2)
    if len(encoded) > ((MAX_EXPERTISE_IMAGE_BYTES + 2) // 3 * 4 + 16):
        raise ApiError("Ảnh tối đa 5 MB", 413)
    try:
        binary = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ApiError("Dữ liệu ảnh không hợp lệ")
    if not binary or len(binary) > MAX_EXPERTISE_IMAGE_BYTES:
        raise ApiError("Ảnh tối đa 5 MB", 413)
    valid = ((ext == "jpg" and binary.startswith(b"\xff\xd8\xff")) or
             (ext == "png" and binary.startswith(b"\x89PNG\r\n\x1a\n")) or
             (ext == "webp" and binary.startswith(b"RIFF") and binary[8:12] == b"WEBP") or
             (ext == "gif" and binary[:6] in (b"GIF87a", b"GIF89a")))
    if not valid:
        raise ApiError("Loại file không khớp nội dung")
    try:
        return store_image("expertise", binary, ext)
    except ImageStorageError as exc:
        raise ApiError(str(exc), 502) from exc


def delete_expertise_image(src):
    delete_image(src, "expertise")


def expertise_items():
    """Giữ đúng 4 mục, theo thứ tự SITE.services; tự khôi phục nếu file trống."""
    saved = read_all("expertise-images")
    if not isinstance(saved, list):
        saved = []
    by_index = {i.get("index"): i for i in saved if isinstance(i, dict) and type(i.get("index")) is int}
    return [{"index": n, "src": by_index.get(n, {}).get("src") or None,
             "updatedAt": by_index.get(n, {}).get("updatedAt") or None} for n in range(4)]


# ---------------- Ảnh đại diện 3 nhóm dịch vụ (độc lập với các bài đăng) ----------------
def store_service_cover(dataurl):
    """Chỉ lưu hình thật với đúng chữ ký, max 6 MiB, đường dẫn riêng."""
    if not isinstance(dataurl, str):
        raise ApiError("Thiếu ảnh đại diện")
    m = DATAURL_RE.fullmatch(dataurl.strip())
    if not m:
        raise ApiError("Chỉ hỗ trợ ảnh JPG, PNG, WebP hoặc GIF")
    ext = m.group(1).lower().replace("jpeg", "jpg")
    encoded = m.group(2)
    if len(encoded) > ((MAX_SERVICE_COVER_BYTES + 2) // 3 * 4 + 16):
        raise ApiError("Ảnh vượt quá 6 MB", 413)
    try:
        binary = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ApiError("Dữ liệu ảnh không hợp lệ")
    if not binary or len(binary) > MAX_SERVICE_COVER_BYTES:
        raise ApiError("Ảnh vượt quá 6 MB", 413)
    valid = ((ext == "jpg" and binary.startswith(b"\xff\xd8\xff")) or
             (ext == "png" and binary.startswith(b"\x89PNG\r\n\x1a\n")) or
             (ext == "webp" and binary.startswith(b"RIFF") and binary[8:12] == b"WEBP") or
             (ext == "gif" and binary[:6] in (b"GIF87a", b"GIF89a")))
    if not valid:
        raise ApiError("Định dạng file không khớp nội dung")
    try:
        return store_image("service-covers", binary, ext)
    except ImageStorageError as exc:
        raise ApiError(str(exc), 502) from exc


def delete_service_cover(src):
    delete_image(src, "service-covers")


def service_cover_items():
    saved = read_all("service-covers")
    if not isinstance(saved, list):
        saved = []
    by_index = {it.get("index"): it for it in saved if isinstance(it, dict) and type(it.get("index")) is int and it.get("index") in (0, 1, 2)}
    return [{"index": i, "src": by_index.get(i, {}).get("src") or None,
             "updatedAt": by_index.get(i, {}).get("updatedAt") or None} for i in range(3)]


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
        except DataStorageError as e:
            self.log_error("Data storage failure: %s", e)
            self.send_json(503, {"error": str(e)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # lỗi không lường trước
            self.log_error("Lỗi: %r", e)
            try:
                self.send_json(500, {"error": "Lỗi máy chủ"})
            except OSError:
                pass

    # ----- API -----

    def service_covers_api(self, method, parts):
        """GET 3 cover công khai, PUT / DELETE index 0..2 cho admin."""
        if method == "GET" and len(parts) == 2:
            return self.send_json(200, service_cover_items())
        if len(parts) != 3 or parts[2] not in ("0", "1", "2"):
            raise ApiError("Nhóm dịch vụ không tồn tại", 404)
        if not self.is_auth():
            raise ApiError("Cần đăng nhập admin", 401)
        if method not in ("PUT", "DELETE"):
            raise ApiError("Phương thức không hỗ trợ", 405)
        index = int(parts[2])
        payload = self.read_body() if method == "PUT" else None
        if method == "PUT" and (not isinstance(payload, dict) or not payload.get("image")):
            raise ApiError("Hãy chọn ảnh trước khi lưu")
        with _data_lock:
            items = service_cover_items()
            old_src = items[index]["src"]
            new_src = store_service_cover(payload["image"]) if method == "PUT" else None
            items[index] = {"index": index, "src": new_src, "updatedAt": now_iso()}
            try:
                write_all("service-covers", items)
            except Exception:
                delete_service_cover(new_src)
                raise
            if old_src and old_src != new_src:
                delete_service_cover(old_src)
        broadcast("change", {"type": "service-covers", "action": "update" if new_src else "reset", "index": index})
        return self.send_json(200, items[index])

    def expertise_api(self, method, parts):
        """GET công khai; PUT upload / DELETE khôi phục biểu tượng mặc định (admin)."""
        if method == "GET" and len(parts) == 2:
            return self.send_json(200, expertise_items())
        if len(parts) != 3 or parts[2] not in ("0", "1", "2", "3"):
            raise ApiError("Vị trí lĩnh vực không hợp lệ", 404)
        if not self.is_auth():
            raise ApiError("Cần đăng nhập admin", 401)
        index = int(parts[2])
        if method not in ("PUT", "DELETE"):
            raise ApiError("Phương thức không hỗ trợ", 405)
        payload = self.read_body() if method == "PUT" else None
        if method == "PUT" and (not isinstance(payload, dict) or not payload.get("image")):
            raise ApiError("Hãy chọn ảnh trước khi lưu")
        with _data_lock:
            items = expertise_items()
            old_src = items[index]["src"]
            new_src = store_expertise_image(payload["image"]) if method == "PUT" else None
            items[index] = {"index": index, "src": new_src, "updatedAt": now_iso()}
            try:
                write_all("expertise-images", items)
            except Exception:
                delete_expertise_image(new_src)
                raise
            if old_src and old_src != new_src:
                delete_expertise_image(old_src)
        broadcast("change", {"type": "expertise-images", "action": "update" if new_src else "reset", "index": index})
        return self.send_json(200, items[index])

    def album_api(self, method, parts):
        """GET công khai, POST thêm ảnh, PUT chú thích, DELETE một ảnh hoặc nhiều ảnh."""
        is_admin = self.is_auth()
        album_id = unquote(parts[2]) if len(parts) > 2 else None
        if method == "GET" and not album_id:
            return self.send_json(200, sorted(read_all("album"), key=lambda i: i.get("createdAt", ""), reverse=True))
        if not is_admin:
            raise ApiError("Cần đăng nhập admin", 401)
        body = self.read_body() if method in ("POST", "PUT", "DELETE") else {}
        with _data_lock:
            items = read_all("album")
            if method == "POST" and not album_id:
                if not isinstance(body, dict):
                    raise ApiError("Dữ liệu không hợp lệ")
                caption = text(body.get("caption"), 250)
                src = store_album_image(body.get("image"))
                item = {"id": secrets.token_hex(8), "src": src, "caption": caption,
                        "createdAt": now_iso()}
                try:
                    write_all("album", items + [item])
                except Exception:
                    delete_album_image(src)
                    raise
                action, status, response = "create", 201, item
            elif method == "PUT" and album_id:
                it = next((x for x in items if x.get("id") == album_id), None)
                if it is None:
                    raise ApiError("Không tìm thấy ảnh", 404)
                it["caption"] = text(body.get("caption"), 250)
                write_all("album", items)
                action, status, response = "update", 200, it
            elif method == "DELETE" and album_id:
                if album_id == "selected":
                    ids = body.get("ids") if isinstance(body, dict) else None
                    if not isinstance(ids, list) or not ids or len(ids) > 500 or any(not isinstance(v, str) for v in ids):
                        raise ApiError("Danh sách ảnh cần xóa không hợp lệ")
                    selected = set(ids)
                    deleting = [x for x in items if x.get("id") in selected]
                    if not deleting:
                        raise ApiError("Không tìm thấy ảnh để xóa", 404)
                else:
                    deleting = [x for x in items if x.get("id") == album_id]
                    if not deleting:
                        raise ApiError("Không tìm thấy ảnh", 404)
                deleted = {x["id"] for x in deleting}
                write_all("album", [x for x in items if x.get("id") not in deleted])
                for item in deleting:
                    delete_album_image(item.get("src"))
                action, status, response = "delete", 200, {"ok": True, "deleted": len(deleting)}
            else:
                raise ApiError("Phương thức không hỗ trợ", 405)
        broadcast("change", {"type": "album", "action": action})
        return self.send_json(status, response)

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

        if name == "album":
            return self.album_api(method, parts)
        if name == "expertise-images":
            return self.expertise_api(method, parts)
        if name == "service-covers":
            return self.service_covers_api(method, parts)

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
                try:
                    write_all(kind, items)
                except Exception:
                    # New uploaded images are not yet referenced by stored JSON.
                    originals = set(x for x in (body.get("images") or []) if isinstance(x, str))
                    delete_uploads([p for p in it.get("images", []) if p not in originals])
                    raise
                action, status = "create", 201
            elif method == "PUT" and item_id:
                idx = next((i for i, x in enumerate(items) if x.get("id") == item_id), -1)
                if idx < 0:
                    raise ApiError("Không tìm thấy", 404)
                old_imgs = list(items[idx].get("images") or [])
                it = normalize(kind, body, items[idx])
                it["updatedAt"] = now_iso()
                items[idx] = it
                try:
                    write_all(kind, items)
                except Exception:
                    originals = set(x for x in (body.get("images") or []) if isinstance(x, str))
                    delete_uploads([p for p in it.get("images", []) if p not in originals and p not in old_imgs])
                    raise
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
        if p.startswith("/media/"):
            try:
                signed = signed_image_url(p)
            except ImageStorageError as exc:
                raise ApiError(str(exc), 502) from exc
            if not signed:
                raise ApiError("Không tìm thấy ảnh", 404)
            self.send_response(302)
            self.send_header("Location", signed)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if p.startswith("/service-covers/"):
            base, rel = LOCAL_FOLDERS["service-covers"], p[len("/service-covers/"):]
        elif p.startswith("/expertise/"):
            base, rel = LOCAL_FOLDERS["expertise"], p[len("/expertise/"):]
        elif p.startswith("/album/"):
            base, rel = LOCAL_FOLDERS["album"], p[len("/album/"):]
        elif p.startswith("/uploads/"):
            base, rel = LOCAL_FOLDERS["uploads"], p[len("/uploads/"):]
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
        self.send_header("Cache-Control", "public, max-age=604800" if p.startswith(("/uploads/", "/album/", "/expertise/", "/service-covers/")) else "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if "/api/stream" not in (self.path or ""):
            super().log_message(fmt, *args)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    # No HTTP requests are accepted if private JSON storage is unreachable.
    initialize_data()
    httpd = Server((HOST, PORT), Handler)
    print(f"ReMate website: http://localhost:{PORT}")
    print(f"Ảnh upload mới: IMAGE_STORAGE={IMAGE_STORAGE}")
    print(f"Dữ liệu JSON: DATA_STORAGE={DATA_STORAGE}")
    print(f"Trang quản trị: http://localhost:{PORT}/admin.html  (user: {ADMIN_USER})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ.")
