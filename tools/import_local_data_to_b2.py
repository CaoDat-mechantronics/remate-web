"""One-time import of all seven local JSON collections and referenced images.

Run from the project directory with an existing, EMPTY B2 data namespace:
    python tools/import_local_data_to_b2.py --data-dir ./data --public-dir ./public
    python tools/import_local_data_to_b2.py --data-dir ./data --public-dir ./public --apply

It never overwrites existing B2 JSON or the initialization marker, even on --apply.
Run BEFORE deploying ReMate with DATA_STORAGE=b2, unless B2 is already initialized.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

import data_storage as ds


def main():
    parser = argparse.ArgumentParser(description="Sao chép dữ liệu và ảnh ReMate local sang B2 lần đầu")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data", help="Thư mục chứa 7 file JSON")
    parser.add_argument("--public-dir", type=Path, default=ROOT / "public", help="Thư mục chứa ảnh uploads/ album/ expertise/ service-covers/")
    parser.add_argument("--apply", action="store_true", help="Thực hiện upload. Mặc định chỉ kiểm tra.")
    args = parser.parse_args()
    source_dir = args.data_dir.resolve()
    public_dir = args.public_dir.resolve()

    contents = {}
    local_refs = set()

    def collect(obj):
        if isinstance(obj, dict):
            for v in obj.values(): collect(v)
        elif isinstance(obj, list):
            for v in obj: collect(v)
        elif isinstance(obj, str):
            from image_storage import LOCAL_URL
            match = LOCAL_URL.fullmatch(obj)
            if match:
                folder, filename = match.groups()
                src = public_dir / folder / filename
                if not src.is_file():
                    raise SystemExit(f"Thiếu ảnh: {src}. Hãy lấy lại file từ backup trước khi import.")
                local_refs.add(obj)

    for kind in ds.KINDS:
        path = source_dir / f"{kind}.json"
        if not path.is_file():
            raise SystemExit(f"Thiếu dữ liệu: {path}")
        contents[kind] = ds._parse_array(path.read_bytes(), kind)
        collect(contents[kind])

    print(f"JSON: {len(contents)} bộ dữ liệu; ảnh local cần chuyển: {len(local_refs)}")
    print("B2 Bucket:", ds._bucket(), "| prefix:", ds.PREFIX)
    if not args.apply:
        print("Chưa upload. Chạy lại với --apply để import vào namespace dữ liệu B2 đang trống.")
        return

    # Refuse to mutate an existing deployment's data. Prevent accidental loss.
    if ds._get_object(ds.MARKER) is not None:
        raise SystemExit("B2 đã được khởi tạo. Không import ghi đè dữ liệu đang dùng.")
    existing = [kind for kind in ds.KINDS if ds._get_object(ds._key(kind)) is not None]
    if existing:
        raise SystemExit("B2 đã có JSON: " + ", ".join(existing) + ". Dừng để tránh ghi đè.")

    uploaded = set()
    for kind in ds.KINDS:
        items = ds._migrate_local_urls(contents[kind], uploaded, public_dir)
        ds._put_object(ds._key(kind), json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))
        print("Đã lưu B2:", ds._key(kind), f"({len(items)} mục)")
    ds._put_object(ds.MARKER, json.dumps({
        "app": "remate", "schema": 1, "collections": list(ds.KINDS)
    }).encode("utf-8"))
    print(f"HOÀN THÀNH: {len(contents)} JSON + {len(uploaded)} ảnh trên Backblaze B2.")


if __name__ == "__main__":
    main()
