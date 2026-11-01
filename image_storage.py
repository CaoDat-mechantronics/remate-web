"""ReMate image storage adapter.

IMAGE_STORAGE=b2|local|firebase|cloudinary selects where *new uploads* go.
Every stored URL identifies its original provider; changing IMAGE_STORAGE never
reroutes existing images to a different provider.

Old /uploads/, /album/, /expertise/ and /service-covers/ URLs remain local.
Remote objects use /media/<provider>/<folder>/<file>. B2/Firebase use signed
redirects; Cloudinary assets use public CDN delivery URLs.
"""
import json
import logging
import os
import re
import secrets
import time
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"

LOCAL_FOLDERS = {
    "uploads": Path(os.environ.get("UPLOAD_DIR", PUBLIC_DIR / "uploads")).resolve(),
    "album": Path(os.environ.get("ALBUM_DIR", PUBLIC_DIR / "album")).resolve(),
    "expertise": Path(os.environ.get("EXPERTISE_DIR", PUBLIC_DIR / "expertise")).resolve(),
    "service-covers": Path(os.environ.get("SERVICE_COVERS_DIR", PUBLIC_DIR / "service-covers")).resolve(),
}
IMAGE_STORAGE = os.environ.get("IMAGE_STORAGE", "b2").lower().strip()
if IMAGE_STORAGE not in ("local", "b2", "firebase", "cloudinary"):
    raise RuntimeError("IMAGE_STORAGE chỉ được là b2, local, firebase hoặc cloudinary")

EXT_MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
# Recognize only narrow, upload-generated paths; never accept arbitrary object keys.
REMOTE_URL = re.compile(
    r"^/media/(b2|firebase|cloudinary)/(uploads|album|expertise|service-covers)/([0-9a-zA-Z_-]+\.(?:jpg|png|webp|gif))$"
)
LOCAL_URL = re.compile(
    r"^/(uploads|album|expertise|service-covers)/([0-9a-zA-Z_-]+\.(?:jpg|png|webp|gif))$"
)


class ImageStorageError(Exception):
    pass


def _required(*names):
    values = [os.environ.get(n, "").strip() for n in names]
    if any(not v for v in values):
        missing = [n for n, v in zip(names, values) if not v]
        raise ImageStorageError("Thiếu cấu hình: " + ", ".join(missing))
    return values


@lru_cache(maxsize=1)
def b2_client():
    endpoint, key_id, app_key, _ = _required(
        "B2_ENDPOINT", "B2_KEY_ID", "B2_APP_KEY", "B2_BUCKET"
    )
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise ImageStorageError("Chưa cài boto3: pip install -r requirements.txt") from exc
    # Read the B2 region from the endpoint, or use the explicit variable.
    region = os.environ.get("B2_REGION", "").strip()
    if not region:
        match = re.match(r"^https://s3\.([a-z0-9-]+)\.backblazeb2\.com/?$", endpoint)
        if not match:
            raise ImageStorageError("B2_ENDPOINT không đúng dạng https://s3.<region>.backblazeb2.com")
        region = match.group(1)
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=key_id,
        aws_secret_access_key=app_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@lru_cache(maxsize=2)
def cloudinary_client(for_write=False):
    """Cloudinary SDK configuration is server-side only.

    Read of existing Cloudinary images requires only CLOUDINARY_CLOUD_NAME,
    while upload/delete requires credentials. CLOUDINARY_URL is also supported.
    """
    url = os.environ.get("CLOUDINARY_URL", "").strip()
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()
    if not url and not cloud_name:
        raise ImageStorageError("Thiếu CLOUDINARY_CLOUD_NAME hoặc CLOUDINARY_URL")
    if not url and for_write and (not api_key or not api_secret):
        raise ImageStorageError("Thiếu CLOUDINARY_API_KEY hoặc CLOUDINARY_API_SECRET")
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.utils
    except ImportError as exc:
        raise ImageStorageError("Chưa cài cloudinary: pip install -r requirements.txt") from exc
    if url:
        # Cloudinary's Python SDK loads CLOUDINARY_URL from the environment.
        cloudinary.config(secure=True)
    else:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key or None,
            api_secret=api_secret or None,
            secure=True,
        )
    config = cloudinary.config()
    if not config.cloud_name:
        raise ImageStorageError("CLOUDINARY_URL không hợp lệ hoặc thiếu cloud name")
    if for_write and (not config.api_key or not config.api_secret):
        raise ImageStorageError("Thiếu API key/secret của Cloudinary")
    return cloudinary


def _cloudinary_public_id(folder, filename):
    # Fixed namespace is intentional: switching providers or env variables must
    # never change the location of previously uploaded Cloudinary images.
    return f"remate/{folder}/{filename.rsplit('.', 1)[0]}"


@lru_cache(maxsize=1)
def firebase_bucket():
    (bucket_name,) = _required("FIREBASE_STORAGE_BUCKET")
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    file_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE", "").strip()
    if not raw and not file_path:
        raise ImageStorageError("Cần FIREBASE_SERVICE_ACCOUNT_JSON hoặc FIREBASE_SERVICE_ACCOUNT_FILE")
    try:
        import firebase_admin
        from firebase_admin import credentials, storage
    except ImportError as exc:
        raise ImageStorageError("Chưa cài firebase-admin: pip install -r requirements.txt") from exc
    try:
        cert = credentials.Certificate(json.loads(raw) if raw else file_path)
        try:
            app = firebase_admin.get_app("remate-image-storage")
        except ValueError:
            app = firebase_admin.initialize_app(
                cert, {"storageBucket": bucket_name}, name="remate-image-storage"
            )
        return storage.bucket(app=app)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise ImageStorageError("Firebase service account hoặc bucket không hợp lệ") from exc


def _save_remote(provider, key, binary, content_type):
    if provider == "b2":
        (bucket,) = _required("B2_BUCKET")
        b2_client().put_object(
            Bucket=bucket, Key=key, Body=binary, ContentType=content_type
        )
    elif provider == "cloudinary":
        from io import BytesIO
        folder, filename = key.split("/", 1)
        client = cloudinary_client(for_write=True)
        ext = filename.rsplit(".", 1)[-1]
        public_id = _cloudinary_public_id(folder, filename)
        result = client.uploader.upload(
            BytesIO(binary), public_id=public_id,
            resource_type="image", type="upload", format=ext,
            overwrite=False, unique_filename=False,
        )
        if result.get("public_id") != public_id or result.get("format") != ext:
            raise ImageStorageError("Cloudinary trả về thông tin file không đúng định dạng")
    elif provider == "firebase":
        firebase_bucket().blob(key).upload_from_string(binary, content_type=content_type)
    else:
        raise ImageStorageError("Nhà cung cấp lưu trữ ảnh không được hỗ trợ")


def store_image(folder, binary, ext):
    """Return permanent app URL, independent of any temporary signed URL."""
    if folder not in LOCAL_FOLDERS or ext not in EXT_MIME or not binary:
        raise ImageStorageError("Loại ảnh hoặc thư mục upload không hợp lệ")
    filename = f"{int(time.time() * 1000)}-{secrets.token_hex(8)}.{ext}"
    if IMAGE_STORAGE == "local":
        dest = LOCAL_FOLDERS[folder]
        dest.mkdir(parents=True, exist_ok=True)
        (dest / filename).write_bytes(binary)
        return f"/{folder}/{filename}"
    key = f"{folder}/{filename}"
    try:
        _save_remote(IMAGE_STORAGE, key, binary, EXT_MIME[ext])
    except ImageStorageError:
        raise
    except Exception as exc:
        logging.exception("Image upload failed to %s", IMAGE_STORAGE)
        raise ImageStorageError("Không thể upload ảnh lên dịch vụ lưu trữ") from exc
    return f"/media/{IMAGE_STORAGE}/{key}"


def _parse_reference(src):
    if not isinstance(src, str):
        return None
    m = REMOTE_URL.fullmatch(src)
    if m:
        provider, folder, filename = m.groups()
        return provider, folder, filename
    m = LOCAL_URL.fullmatch(src)
    if m:
        folder, filename = m.groups()
        return "local", folder, filename
    return None


def delete_image(src, folder=None):
    """Delete by ORIGINAL provider. Ignore external links and unrelated folders.

    A failure to delete an old object is logged (not fatal to already-saved JSON).
    """
    info = _parse_reference(src)
    if not info:
        return
    provider, actual_folder, filename = info
    if folder is not None and actual_folder != folder:
        return
    try:
        if provider == "local":
            (LOCAL_FOLDERS[actual_folder] / filename).unlink(missing_ok=True)
        elif provider == "b2":
            (bucket,) = _required("B2_BUCKET")
            b2_client().delete_object(Bucket=bucket, Key=f"{actual_folder}/{filename}")
        elif provider == "cloudinary":
            client = cloudinary_client(for_write=True)
            client.uploader.destroy(
                _cloudinary_public_id(actual_folder, filename),
                resource_type="image", type="upload", invalidate=True,
            )
        elif provider == "firebase":
            firebase_bucket().blob(f"{actual_folder}/{filename}").delete()
    except Exception:
        logging.exception("Could not delete old image: %s", src)


def signed_image_url(path):
    """Return a B2/Firebase signed URL or Cloudinary CDN URL, or None.

    Switching IMAGE_STORAGE does not change how older images are retrieved.
    """
    m = REMOTE_URL.fullmatch(path)
    if not m:
        return None
    provider, folder, filename = m.groups()
    key = f"{folder}/{filename}"
    try:
        if provider == "b2":
            (bucket,) = _required("B2_BUCKET")
            return b2_client().generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
            )
        if provider == "cloudinary":
            client = cloudinary_client(for_write=False)
            public_id = _cloudinary_public_id(folder, filename)
            ext = filename.rsplit(".", 1)[-1]
            url, _ = client.utils.cloudinary_url(
                public_id, format=ext, secure=True,
                resource_type="image", type="upload",
            )
            if not isinstance(url, str) or not url.startswith("https://"):
                raise ImageStorageError("Không tạo được URL ảnh Cloudinary")
            return url
        if provider == "firebase":
            return firebase_bucket().blob(key).generate_signed_url(
                version="v4", expiration=timedelta(hours=1), method="GET"
            )
        return None
    except ImageStorageError:
        raise
    except Exception as exc:
        logging.exception("Could not sign remote image URL: %s", path)
        raise ImageStorageError("Không thể tạo đường dẫn đọc ảnh") from exc
