# HƯỚNG DẪN REMATE — LƯU CẢ DỮ LIỆU JSON VÀ ẢNH TRÊN BACKBLAZE B2

## 1. Có gì mới?

- `DATA_STORAGE=b2` (mặc định): **toàn bộ 7 nhóm dữ liệu JSON** gồm sản phẩm,
  dịch vụ, dự án, đối tác, album, ảnh 4 lĩnh vực, ảnh đại diện 3 nhóm dịch vụ
  được đọc/ghi lên B2. Không lưu thay đổi vào ổ đĩa Render.
- `IMAGE_STORAGE=b2` (mặc định): ảnh upload mới nằm trên B2 Private Bucket.
- Vẫn hỗ trợ `IMAGE_STORAGE=local|b2|firebase|cloudinary`. Cơ chế chuyển chỉ
  thay đổi nơi upload **ảnh mới**; đường dẫn ảnh cũ gắn với provider cũ.
- `DATA_STORAGE=local`: đọc/ghi JSON tại `DATA_DIR` nếu muốn chạy hoàn toàn
  local. Data storage độc lập với Image storage.
- Frontend và các đường dẫn API giữ nguyên.

## 2. Cấu hình `.env` cho máy tính hoặc Render → Environment

```env
HOST=0.0.0.0
PORT=3000
ADMIN_USER=admin
ADMIN_PASSWORD=THAY_MAT_KHAU_MANH

DATA_STORAGE=b2
IMAGE_STORAGE=b2
B2_DATA_PREFIX=data

B2_BUCKET=ten-bucket-thuc-te
B2_ENDPOINT=https://s3.us-west-004.backblazeb2.com
B2_KEY_ID=KEY_ID_CUA_BAN
B2_APP_KEY=APPLICATION_KEY_CUA_BAN
```

`B2_ENDPOINT` là ví dụ, thay bằng endpoint **thực tế** theo vùng bucket của bạn.
Cần key **Read and Write**, giới hạn vào đúng Private Bucket ReMate. KHÔNG
đưa `.env` hoặc `B2_APP_KEY` lên GitHub và không gửi khóa cho người khác.

Tại máy tính:

```bash
cp .env.example .env
# Sửa các giá trị trong .env bằng editor
pip install -r requirements.txt
python server.py
```

Windows có thể sao chép/đổi tên `.env.example` thành `.env` trong File Explorer.
Truy cập `http://localhost:3000`, `http://localhost:3000/admin.html`.

Trên Render: Build `pip install -r requirements.txt`, Start `python server.py`.
**Đặt toàn bộ biến môi trường tương ứng trong Render Environment**. Render
ưu tiên biến Environment của service hơn biến có trong `.env`.

## 3. Dữ liệu nằm ở đâu trên B2?

```text
B2 Private Bucket (ví dụ remate-images-2026)
├── data/
│   ├── .remate-initialized.json    # dấu đã khởi tạo; không xóa
│   ├── products.json
│   ├── services.json
│   ├── projects.json
│   ├── partners.json
│   ├── album.json
│   ├── expertise-images.json
│   └── service-covers.json
├── uploads/                       # ảnh sản phẩm, dịch vụ, dự án
├── album/                         # ảnh album
├── expertise/                     # ảnh 4 lĩnh vực
└── service-covers/                # ảnh bìa dịch vụ
```

Lần đầu chạy với B2 và namespace `data/` trống, server tự **upload 7 JSON
mẫu + ảnh local mà các JSON mẫu trỏ tới**, đổi đường dẫn ảnh đó sang
`/media/b2/...`, cuối cùng tạo `.remate-initialized.json`.
Sau khi có marker, startup **không bao giờ ghi đè** JSON từ source. Nếu mất
một JSON trên B2, service dừng/báo lỗi thay vì âm thầm reset bằng dữ liệu mẫu.

Các API sẽ đọc dữ liệu trực tiếp từ B2 ở mỗi request. Một thao tác lưu sẽ ghi
lại JSON tương ứng lên B2; lỗi đọc/ghi trả HTTP 503, không fallback xuống
file local. URL ảnh B2 được backend ký tạm thời và trả HTTP 302.

## 4. Quan trọng: Dữ liệu đã thêm từ phiên bản Render cũ

Bản mới KHÔNG thể tự khôi phục dữ liệu chỉ tồn tại trong filesystem cũ của
Render. **Trước khi deploy bản mới**:

1. Sao lưu 7 JSON đang có trong thư mục `data/` của phiên bản cũ, cùng với
   ảnh có liên kết trong `public/uploads`, `public/album`,
   `public/expertise`, `public/service-covers`. Bạn có thể dùng bộ source
   chứa dữ liệu hiện tại hoặc một bản backup đã xuất.
2. Trên máy tính, đặt đúng 7 JSON vào `data/`, và ảnh vào các thư mục trên.
3. Đảm bảo bucket chưa chứa `data/*.json` hay `data/.remate-initialized.json`.
4. Sau khi khai báo `.env`, chạy kiểm tra trước:

   ```bash
   python tools/import_local_data_to_b2.py
   ```

5. Nếu danh sách đầy đủ, chạy upload **một lần**:

   ```bash
   python tools/import_local_data_to_b2.py --apply
   ```

6. Sau đó deploy website lên Render với `DATA_STORAGE=b2` và `IMAGE_STORAGE=b2`.

**Nếu B2 đã có dữ liệu thật**, script sẽ TỪ CHỐI ghi đè. Không xóa JSON hoặc
marker đang hoạt động để cố import lại. Muốn di chuyển một bản dữ liệu mới
vào bucket đã có dữ liệu, cần sao lưu và lập kế hoạch nhập/gộp riêng.

## 5. Kiểm tra sau khi deploy

1. Render Logs phải xuất hiện `DATA_STORAGE=b2` và `IMAGE_STORAGE=b2`.
2. Backblaze Browse Files → Bucket, kiểm tra có cả `data/` và các thư mục ảnh.
3. Tạo một sản phẩm + ảnh bằng Admin, xem `data/products.json` có bản ghi
   và thư mục `uploads/` có file mới.
4. Reload trang, thử sửa mô tả, kiểm tra thông tin còn trên B2.
5. Khởi động lại Render rồi mở trang: thông tin/ảnh không biến mất.

**Đừng chỉ xem thấy ảnh rồi kết luận rằng JSON đã lưu**: cần kiểm tra
`data/products.json` trên B2 và thử đọc lại sau restart.

## 6. Điều kiện vận hành & sao lưu

- B2 là object storage, không có transaction khi cùng lúc sửa một JSON.
  Server có mutex cho nhiều request của **một** tiến trình. Chỉ chạy **một
  process/replica** ghi dữ liệu. Không cấu hình `gunicorn --workers 2+`.
- B2 giữ phiên bản object; các phiên bản JSON cũ có thể dùng để khôi phục,
  nhưng có thể bị xóa theo Lifecycle Rules. Nên thiết lập chính sách giữ bản
  cũ và định kỳ tải bản sao lưu độc lập. Các bản cũ vẫn dùng dung lượng B2.
- `DATA_STORAGE=b2` chỉ đảm bảo bền vững khi bucket, key, kết nối B2 hoạt động.
  Nếu bị lỗi mạng/quyền, server báo lỗi chứ không tự chuyển sang local.
- Chuyển `DATA_STORAGE=local` không tự đồng bộ JSON từ B2 về máy. Không tùy tiện
  thay đổi `B2_DATA_PREFIX` sau khi đã lưu dữ liệu.
- Nếu ảnh upload trước đây thuộc Firebase, Cloudinary hoặc B2 khác, hãy giữ
  thông tin kết nối cũ để đọc được ảnh hiện hữu; switch không chuyển ảnh cũ.
- Nếu website có nhiều admin, lưu lượng lớn hoặc triển khai nhiều instance,
  hãy chuyển metadata sang PostgreSQL/Firestore để tránh tranh chấp ghi.

## 7. Kiểm thử source (không cần key thật)

```bash
python -m unittest discover -s tests -v
```

Các test dùng B2 giả lập trong bộ nhớ, không truy cập tài khoản của bạn.
Chưa có kiểm thử end-to-end với bucket và key thật của bạn.
