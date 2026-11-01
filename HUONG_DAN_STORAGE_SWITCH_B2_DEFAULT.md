# ReMate — Chuyển nơi lưu ảnh bằng `IMAGE_STORAGE` (mặc định Backblaze B2)

Bản source này được cập nhật từ **`remate-website_current.zip`**. Frontend và API quản lý sản phẩm, dự án, đối tác, dịch vụ, album, ảnh 4 lĩnh vực và ảnh 3 nhóm dịch vụ giữ nguyên. Chỉ thay cơ chế ghi, đọc và xóa ảnh. **Không chứa key thật**.

> **Quan trọng:** `IMAGE_STORAGE` chỉ chọn nơi lưu **ảnh**. Các file `data/*.json` (sản phẩm, dịch vụ, dự án, album...) vẫn được ghi trên filesystem của server. Trên **Render Free**, chúng vẫn có thể mất khi service restart/redeploy. Cần thêm Postgres/Firestore hoặc Persistent Disk để dữ liệu bài đăng tồn tại bền vững. Không nhầm việc lưu ảnh trên B2 với việc đã bảo vệ toàn bộ dữ liệu website.

## 1. Chọn nơi upload ảnh mới

| Render Environment | Chức năng |
|---|---|
| `IMAGE_STORAGE=b2` | **Mặc định**: upload lên Backblaze B2 (Private Bucket); trình duyệt xem qua URL ký tạm 1 giờ |
| `IMAGE_STORAGE=local` | Upload vào `public/uploads`, `public/album`, `public/expertise`, `public/service-covers` hoặc thư mục do biến môi trường trỏ tới |
| `IMAGE_STORAGE=firebase` | Upload lên Firebase Cloud Storage, đọc qua signed URL |
| `IMAGE_STORAGE=cloudinary` | Upload lên Cloudinary, hiển thị bằng URL CDN công khai |

Bỏ trống `IMAGE_STORAGE` cũng mặc định là `b2`. Khi thay đổi trên Render, **Save, deploy/restart** để server đọc cấu hình mới. Nếu chọn `b2` nhưng chưa khai báo đủ B2 credentials, website vẫn chạy song **upload ảnh mới sẽ báo lỗi**; hệ thống **không tự fallback sang local** vì có thể gây mất ảnh trên Render Free.

URL lưu trong dữ liệu bài đăng có tính ổn định và gắn với **provider gốc**:

```text
/uploads/anh-cu.jpg                         # local (kể cả khi IMAGE_STORAGE=b2)
/media/b2/uploads/anh-001.webp             # Backblaze B2
/media/firebase/album/anh-002.jpg          # Firebase
/media/cloudinary/expertise/anh-003.webp   # Cloudinary
```

Khi chuyển từ B2 sang Cloudinary, **ảnh mới** lưu trên Cloudinary; **ảnh cũ** vẫn đọc từ B2 nếu giữ nguyên các biến B2 và bucket B2. Việc đổi switch **không chuyển file cũ** giữa các dịch vụ. Nếu xóa file ở nhà cung cấp cũ hoặc rút credentials, ảnh đó sẽ không hiển thị.

## 2. Cấu hình Backblaze B2 — khuyên dùng hiện tại

1. Backblaze **B2 Cloud Storage → Buckets → Create a Bucket**. Đặt tên bucket duy nhất, chọn **Private** và tắt Object Lock.
2. Mở **Application Keys → Add a New Application Key**. Chọn đúng bucket, quyền **Read and Write**, không giới hạn File name prefix nếu website cần lưu đủ 4 nhóm ảnh. Lưu `keyID` và `applicationKey` ở nơi riêng tư.
3. Xem S3 Endpoint/Region trong thông tin bucket.
4. Mở **Render → Web Service → Environment**, thêm:

```dotenv
IMAGE_STORAGE=b2
B2_BUCKET=TEN_BUCKET_THUC_TE
B2_ENDPOINT=https://s3.us-west-004.backblazeb2.com
B2_KEY_ID=KEY_ID_CUA_BAN
B2_APP_KEY=APPLICATION_KEY_CUA_BAN
# B2_REGION=us-west-004  # không bắt buộc nếu B2_ENDPOINT đúng dạng của Backblaze
```

`us-west-004` chỉ là **ví dụ**; dùng endpoint của **bucket thật**. `B2_KEY_ID` là **keyID**, `B2_APP_KEY` là **applicationKey**. Không đặt trong `public/js/config.js`, HTML, hoặc GitHub. Bucket Private vẫn đọc được: đường dẫn `/media/b2/...` nhận HTTP `302` tới URL B2 có chữ ký tạm thời. Khách xem website không cần đăng nhập Backblaze. B2 private không biến ảnh sản phẩm thành nội dung bí mật vì API media công khai của website cho phép ai biết URL có thể xem ảnh.

## 3. Cấu hình Firebase Storage (gói Blaze)

1. Tạo/đăng nhập Firebase project, bật **Cloud Storage**, nâng cấp **Blaze** nếu cần.
2. Xem đúng tên bucket trong Firebase Console (bucket mới có thể kết thúc bằng `.firebasestorage.app`; không tự suy ra tên).
3. Tạo **Service Account JSON** cho backend với quyền phù hợp trên bucket. Không commit JSON lên Git.
4. Nhập vào Render:

```dotenv
IMAGE_STORAGE=firebase
FIREBASE_STORAGE_BUCKET=TEN_BUCKET_FIREBASE
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account", "...":"..."}
```

Bạn cần thay toàn bộ JSON mẫu bằng **toàn bộ nội dung Service Account JSON thật** trong một Environment Value; không gửi khóa lên chat. Hoặc thay bằng `FIREBASE_SERVICE_ACCOUNT_FILE=/duong/dan/an/toan/file.json` nếu service của bạn thực sự có file này. Ảnh được để private và backend cấp URL ký tạm (Firebase yêu cầu service account đủ quyền ký URL).

## 4. Cấu hình Cloudinary

1. Tạo tài khoản Cloudinary; vào Console → API Keys.
2. Render Environment: cấu hình một trong hai cách:

**Cách A — một biến Cloudinary:**

```dotenv
IMAGE_STORAGE=cloudinary
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

**Cách B — các biến riêng:**

```dotenv
IMAGE_STORAGE=cloudinary
CLOUDINARY_CLOUD_NAME=TEN_CLOUD
CLOUDINARY_API_KEY=API_KEY
CLOUDINARY_API_SECRET=API_SECRET
```

Ảnh upload lên `remate/uploads`, `remate/album`, `remate/expertise` và `remate/service-covers` trong Cloudinary. Chúng được phục vụ qua CDN **công khai** (khác B2 Private/Firebase). URL website `/media/cloudinary/...` tự chuyển hướng sang CDN. Nếu chuyển sang provider khác, cần giữ ít nhất `CLOUDINARY_CLOUD_NAME` (hoặc `CLOUDINARY_URL`) để link ảnh Cloudinary cũ hoạt động; giữ cả khóa khi cần xóa ảnh Cloudinary cũ.

## 5. Chế độ local

```dotenv
IMAGE_STORAGE=local
# Tùy chọn với Persistent Disk:
UPLOAD_DIR=/var/data/uploads
ALBUM_DIR=/var/data/album
EXPERTISE_DIR=/var/data/expertise
SERVICE_COVERS_DIR=/var/data/service-covers
```

Không nên lưu local trên Render Free nếu cần ảnh bền vững. Cần **Persistent Disk** cho các thư mục này (chỉ trên gói Render tương thích).

## 6. Deploy và kiểm thử

**Build Command**:

```bash
pip install -r requirements.txt
```

**Start Command**:

```bash
python server.py
```

Đừng quên đặt `ADMIN_USER` và **`ADMIN_PASSWORD` mạnh, riêng tư** trên Render.

Sau khi deploy:

1. Đăng nhập Admin, thêm một sản phẩm thử nghiệm kèm ảnh.
2. Kiểm tra JSON trả về từ `/api/products`: ảnh mới có `/media/b2/uploads/...` khi đang bật `b2`.
3. Vào Backblaze → Browse Files: có ảnh nằm trong `uploads/`.
4. Mở trang chi tiết sản phẩm ở tab ẩn danh; ảnh hiển thị (Private Bucket + HTTP 302).
5. Thử upload ảnh album, ảnh lĩnh vực, ảnh nhóm dịch vụ, kiểm tra các folder tương ứng.
6. Đổi `IMAGE_STORAGE=local` hoặc `cloudinary` (sau khi có credentials), restart, upload ảnh mới, và kiểm tra ảnh B2 cũ vẫn hiện.

**Xử lý lỗi:** Nếu upload trả 502, mở Render Logs; kiểm tra thiếu `B2_BUCKET`, `B2_ENDPOINT`, `B2_KEY_ID`, `B2_APP_KEY`, sai region, bucket không tồn tại, hoặc Application Key chưa có quyền Read/Write. Không nhập key thật vào ảnh chụp màn hình / chat. Lỗi 403 khi xem ảnh thường là thiếu quyền đọc/sai chữ ký. Không có chế độ chuyển sang local tự động.

## 7. Những điều bản này KHÔNG làm

- Không migrate ảnh cũ từ local sang B2 hoặc từ B2 sang Cloudinary/Firebase.
- Không chuyển file JSON của sản phẩm/dịch vụ sang cơ sở dữ liệu bền vững.
- Không tự kích hoạt tài khoản, bucket, billing hoặc tạo API Key trên bên thứ ba.
- Không xác nhận kết nối với tài khoản thực tế của bạn khi chưa nhập credentials trên Render.

Có thể kiểm thử phần xử lý và API trên máy trước khi deploy:

```bash
python -m unittest discover -s tests -v
```


## Chạy local bằng `.env`

Bản cập nhật này hỗ trợ `python-dotenv`. Chạy `pip install -r requirements.txt`, sao chép `.env.example` thành `.env`, thay giá trị thực và chạy `python server.py`. Load `.env` nằm đầu `server.py` trước khi import `image_storage` để `IMAGE_STORAGE` và khóa B2 được lấy đúng. Trên Render, các biến đặt tại Environment có ưu tiên cao hơn `.env`. Giữ kín `.env` và không commit lên GitHub.

Các biến gốc `HOST`, `PORT`, `ADMIN_USER`, `ADMIN_PASSWORD`, `DATA_DIR`, `UPLOAD_DIR`, `ALBUM_DIR`, `EXPERTISE_DIR`, `SERVICE_COVERS_DIR` đều còn được dùng; `.env.example` đã bổ sung đủ, bao gồm `FIREBASE_SERVICE_ACCOUNT_FILE` (thay thế cho JSON).
