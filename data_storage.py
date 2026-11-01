"""ReMate JSON document storage: B2 Private Bucket (default), or local files.

Stores the seven existing JSON collections as private B2 objects under data/.
The object-storage layout deliberately preserves the old JSON structure and API.
This is suitable for one server process / one writer, not simultaneous writers
on multiple application replicas. B2 is NOT a transactional database.
"""
import json
import logging
import os
import re
from pathlib import Path

from image_storage import b2_client, LOCAL_URL, EXT_MIME

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT / "data"))).resolve()
DATA_STORAGE = os.environ.get("DATA_STORAGE", "b2").strip().lower()
KINDS = (
    "products", "projects", "partners", "services", "album",
    "expertise-images", "service-covers",
)
if DATA_STORAGE not in ("b2", "local"):
    raise RuntimeError("DATA_STORAGE phải là b2 hoặc local")

PREFIX = os.environ.get("B2_DATA_PREFIX", "data").strip().strip("/")
if not PREFIX or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9/_-]*", PREFIX) or "//" in PREFIX:
    raise RuntimeError("B2_DATA_PREFIX chỉ được chứa chữ, số, dấu /, _ và -")
MARKER = f"{PREFIX}/.remate-initialized.json"


class DataStorageError(Exception):
    """Backend JSON storage is inaccessible, invalid, or its write failed."""


def _validate_kind(kind):
    if kind not in KINDS:
        raise DataStorageError("Tên tập dữ liệu không được hỗ trợ")


def _key(kind):
    _validate_kind(kind)
    return f"{PREFIX}/{kind}.json"


def local_path(kind):
    _validate_kind(kind)
    return DATA_DIR / f"{kind}.json"


def _bucket():
    bucket = os.environ.get("B2_BUCKET", "").strip()
    if not bucket:
        raise DataStorageError("Thiếu biến B2_BUCKET")
    return bucket


def _is_missing(exc):
    # Do not confuse missing data with 403, network failure, invalid key, etc.
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    code = str(response.get("Error", {}).get("Code", ""))
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in ("NoSuchKey", "404", "NotFound") or status == 404


def _get_object(key):
    try:
        result = b2_client().get_object(Bucket=_bucket(), Key=key)
        return result["Body"].read()
    except Exception as exc:
        if _is_missing(exc):
            return None
        logging.exception("B2 JSON read failed: %s", key)
        raise DataStorageError("Không đọc được dữ liệu từ Backblaze B2; không dùng bản local thay thế") from exc


def _put_object(key, raw):
    try:
        b2_client().put_object(
            Bucket=_bucket(), Key=key, Body=raw,
            ContentType="application/json; charset=utf-8",
            CacheControl="no-store",
        )
    except Exception as exc:
        logging.exception("B2 JSON write failed: %s", key)
        raise DataStorageError("Không lưu được dữ liệu lên Backblaze B2") from exc


def _parse_array(raw, kind):
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, TypeError, AttributeError) as exc:
        raise DataStorageError(f"Dữ liệu B2 '{kind}' bị hỏng hoặc không phải JSON") from exc
    if not isinstance(value, list):
        raise DataStorageError(f"Dữ liệu B2 '{kind}' phải là danh sách JSON")
    return value


def _migrate_local_urls(collection, uploads, public_root=None):
    """Move linked local content images to B2; keep external/static URL unchanged.

    Used for first-time seeding and for the optional explicit import script.
    uploads is a shared set of already copied object keys.
    """
    if public_root is None:
        public_root = ROOT / "public"
    if isinstance(collection, list):
        return [_migrate_local_urls(item, uploads, public_root) for item in collection]
    if isinstance(collection, dict):
        return {key: _migrate_local_urls(val, uploads, public_root) for key, val in collection.items()}
    if not isinstance(collection, str):
        return collection
    match = LOCAL_URL.fullmatch(collection)
    if not match:
        return collection
    folder, filename = match.groups()
    file_path = public_root / folder / filename
    if not file_path.is_file():
        raise DataStorageError(
            f"Ảnh local '{collection}' không có trong source. "
            "Hãy sao lưu ảnh từ Render trước khi di chuyển dữ liệu."
        )
    key = f"{folder}/{filename}"
    if key not in uploads:
        try:
            b2_client().head_object(Bucket=_bucket(), Key=key)
        except Exception as exc:
            if not _is_missing(exc):
                raise DataStorageError(f"Không kiểm tra được ảnh B2: {key}") from exc
            try:
                b2_client().put_object(
                    Bucket=_bucket(), Key=key, Body=file_path.read_bytes(),
                    ContentType=EXT_MIME[filename.rsplit(".", 1)[-1].lower()],
                )
            except Exception as inner:
                raise DataStorageError(f"Không upload được ảnh mẫu lên B2: {key}") from inner
        uploads.add(key)
    return f"/media/b2/{key}"


def _seed_data(kind, uploads=None):
    # Source-bundled seed is for first-time initialization only, never normal GET.
    source = ROOT / "data" / f"{kind}.json"
    try:
        if source.is_file():
            raw = source.read_bytes()
            values = _parse_array(raw, kind)
            if uploads is not None:
                values = _migrate_local_urls(values, uploads)
            return json.dumps(values, ensure_ascii=False, indent=2).encode("utf-8")
    except DataStorageError:
        raise
    except OSError as exc:
        raise DataStorageError(f"Không đọc được dữ liệu khởi tạo '{kind}'") from exc
    return b"[]\n"


def initialize():
    """Before serving HTTP, initialize absent B2 keys exactly once.

    A sentinel object marks completed initialization. If the sentinel exists
    and a collection disappears, stop rather than silently restoring bundled
    seed data and losing customer changes. Never overwrite an existing key.
    """
    if DATA_STORAGE == "local":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return

    marker = _get_object(MARKER)
    # Fail closed on a corrupted marker.
    if marker is not None:
        try:
            obj = json.loads(marker.decode("utf-8"))
            if obj.get("app") != "remate" or obj.get("schema") != 1:
                raise ValueError("Bad marker")
        except (ValueError, UnicodeDecodeError, AttributeError) as exc:
            raise DataStorageError("Dấu khởi tạo dữ liệu B2 không hợp lệ") from exc

    uploaded_seeds = set()
    for kind in KINDS:
        raw = _get_object(_key(kind))
        if raw is None:
            if marker is not None:
                raise DataStorageError(
                    f"Thiếu {kind}.json trên B2 sau khi đã khởi tạo. "
                    "Dừng để tránh mất dữ liệu; hãy khôi phục từ file version backup."
                )
            _put_object(_key(kind), _seed_data(kind, uploaded_seeds))
            logging.info("B2 initialized: %s", _key(kind))
        else:
            _parse_array(raw, kind)

    if marker is None:
        _put_object(MARKER, json.dumps({
            "app": "remate", "schema": 1,
            "collections": list(KINDS),
        }, ensure_ascii=False).encode("utf-8"))
    logging.info("DATA_STORAGE=b2 ready (%s/%s)", _bucket(), PREFIX)


def read_all(kind):
    """Read latest JSON from chosen storage; never return [] on B2 failures."""
    _validate_kind(kind)
    if DATA_STORAGE == "local":
        try:
            return _parse_array(local_path(kind).read_bytes(), kind)
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise DataStorageError("Không đọc được dữ liệu JSON local") from exc
    raw = _get_object(_key(kind))
    if raw is None:
        raise DataStorageError(
            f"Không tìm thấy {_key(kind)} trên B2. "
            "Chạy lệnh khởi tạo hoặc khôi phục bản sao lưu."
        )
    return _parse_array(raw, kind)


def write_all(kind, items):
    """Write JSON; server.py guards read-modify-write with a process lock."""
    _validate_kind(kind)
    if not isinstance(items, list):
        raise DataStorageError("Dữ liệu ghi phải là một danh sách JSON")
    raw = json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")
    if DATA_STORAGE == "local":
        dest = local_path(kind)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Unique temp path avoids two local processes sharing a temp filename.
        import secrets
        temp = dest.with_name(f".{kind}-{secrets.token_hex(6)}.tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, dest)
        finally:
            temp.unlink(missing_ok=True)
        return
    _put_object(_key(kind), raw)
