# Website ReMate – Công ty Cổ phần Vật tư Tái sử dụng ReMate

Website giới thiệu công ty + trang Sản phẩm + trang Dự án (cập nhật **thời gian thực**) + trang **Quản trị** để admin đăng bài theo mẫu.
Backend viết bằng **Python 3** – chỉ dùng thư viện chuẩn, **không cần `pip install`** (Python ≥ 3.8).

## 1. Chạy thử
```bash
cd remate-website
python server.py        # Windows có thể dùng: py server.py
```
- Website: http://localhost:3000
- Đăng nhập: http://localhost:3000/login.html  →  Quản trị: http://localhost:3000/admin.html — tài khoản mặc định `admin` / `remate@2026`

Đổi tài khoản/mật khẩu/cổng khi chạy thật:
```bash
# Linux / macOS
ADMIN_USER=quantri ADMIN_PASSWORD='MatKhauManh!2026' PORT=8080 python3 server.py

# Windows PowerShell
$env:ADMIN_USER='quantri'; $env:ADMIN_PASSWORD='MatKhauManh!2026'; python server.py
```
Biến môi trường khác: `HOST` (mặc định `0.0.0.0`), `DATA_DIR` (mặc định `./data`), `UPLOAD_DIR` (mặc định `./public/uploads`).

## 2. Cấu trúc
```
remate-website/
├── server.py            # Máy chủ Python: file tĩnh + API + realtime (SSE) + lưu ảnh
├── requirements.txt     # Trống – không có thư viện ngoài
├── README.md
├── .gitignore
├── tools/
│   └── make_images.py   # Tạo ảnh website từ ấn phẩm giới thiệu (cần Pillow)
├── data/
│   ├── products.json    # Dữ liệu sản phẩm (tự cập nhật khi admin đăng bài)
│   └── projects.json    # Dữ liệu dự án
└── public/
    ├── index.html       # Trang chủ: hero theo ấn phẩm, giới thiệu, SP nổi bật, dự án, liên hệ + bản đồ
    ├── san-pham.html    # Danh sách sản phẩm (tìm kiếm, lọc danh mục, sắp xếp)
    ├── du-an.html       # Danh sách dự án
    ├── chi-tiet.html    # Trang chi tiết (?type=products|projects&id=...)
    ├── admin.html       # Trang quản trị (đăng nhập, đăng/sửa/ẩn/xóa bài)
    ├── 404.html
    ├── css/style.css, css/admin.css
    ├── js/config.js     # ★ THÔNG TIN CÔNG TY – sửa tại đây
    ├── js/common.js     # Header, footer, nút liên hệ nổi, realtime
    ├── js/list.js, js/admin.js
    ├── img/             # logo-full.png, logo-icon.png, p1/p2/p3.jpg, flyer.jpg
    └── uploads/         # Ảnh admin tải lên
```

## 3. Ảnh
Ảnh trong `public/img/` được cắt từ ấn phẩm giới thiệu:
```bash
pip install pillow
python tools/make_images.py duong_dan/anh_an_pham.png   # ảnh thật
python tools/make_images.py --placeholder               # ảnh tạm để chạy thử
```

## 4. Cập nhật thông tin liên hệ
Mở `public/js/config.js`:
- `facebook`: **thay bằng link fanpage thật** (hiện đang để https://www.facebook.com/)
- `zalo`: https://zalo.me/0326752517
- Số điện thoại, email, địa chỉ, tài khoản ngân hàng, slogan, 4 lĩnh vực, 3 thế mạnh.

## 5. Mẫu bài đăng (trang quản trị)
| Sản phẩm | Dự án |
|---|---|
| Tên*, Danh mục, Giá (số hoặc "Liên hệ") | Tên*, Lĩnh vực, Thời gian thực hiện |
| Mô tả ngắn* | Mô tả ngắn* |
| Tình trạng, Số lượng, Xuất xứ | Khách hàng, Địa điểm |
| Bảng thông số kỹ thuật (thêm dòng tùy ý) | Phạm vi công việc, Kết quả đạt được |
| Hình ảnh (≤12, ảnh đầu = ảnh đại diện, tự nén) | Hình ảnh (≤12) |
| Nội dung chi tiết, Nổi bật, Hiển thị công khai | Nội dung chi tiết, Nổi bật, Hiển thị công khai |

Khi admin bấm **Đăng bài / Lưu**, mọi khách đang mở website sẽ thấy bài mới **ngay lập tức** (không cần tải lại trang).
2 sản phẩm + 2 dự án có sẵn là **BÀI MẪU** – admin xóa/sửa trong trang quản trị.

## 6. API
| Phương thức | Đường dẫn | Quyền | Mô tả |
|---|---|---|---|
| POST | `/api/login` · `/api/logout` | – | Đăng nhập / đăng xuất (trả token) |
| GET | `/api/me` | admin | Kiểm tra phiên |
| GET | `/api/products` · `/api/projects` | công khai | Danh sách (admin thấy cả bài ẩn) |
| GET | `/api/{type}/{id hoặc slug}` | công khai | Chi tiết |
| POST | `/api/{type}` | admin | Tạo bài |
| PUT | `/api/{type}/{id}` | admin | Sửa bài (ảnh bị gỡ sẽ tự xóa file) |
| DELETE | `/api/{type}/{id}` | admin | Xóa bài + ảnh |
| GET | `/api/stream` | công khai | Realtime (Server-Sent Events) |

## 7. Triển khai
- **VPS**: chạy bằng systemd + Nginx reverse proxy + HTTPS (certbot). Với Nginx cần tắt buffer cho realtime:
  `location /api/stream { proxy_pass http://127.0.0.1:3000; proxy_buffering off; proxy_read_timeout 1h; }`
- **Render/hosting PaaS**: Start command `python server.py`. Gói miễn phí có ổ đĩa tạm → mất bài đăng/ảnh khi khởi động lại;
  cần gói có Persistent Disk và đặt `DATA_DIR`, `UPLOAD_DIR` vào thư mục của disk.
- **Sao lưu** định kỳ `data/` và `public/uploads/`. Bắt buộc đổi mật khẩu admin và dùng HTTPS khi chạy thật.


## Logo icon và favicon (bổ sung)
- `public/img/logo-icon.png`: icon xanh nền trong suốt, hiển thị góc trái header.
- `public/favicon.ico`: favicon trình duyệt đa kích thước.
- `public/img/favicon-32.png`: favicon PNG 32 × 32.
- `public/img/apple-touch-icon.png`: icon cho thiết bị Apple 180 × 180.
- Có thể cần Ctrl + F5 để xóa cache favicon cũ trên trình duyệt.


## Đăng nhập / quản trị tách riêng (bản cập nhật)

- `/login.html`: form đăng nhập độc lập, có nút hình mắt để hiện/ẩn mật khẩu khi nhập.
- `/admin.html`: chỉ hiển thị giao diện quản trị sau khi kiểm tra token bằng `/api/me`; nếu chưa đăng nhập hoặc hết phiên, tự chuyển về `/login.html`.
- `public/js/login.js`: xử lý nút hiện mật khẩu, gửi yêu cầu `/api/login`, lưu token vào `sessionStorage`, chuyển tới quản trị.
- `public/js/admin.js`: xác thực phiên trước khi mở quản trị và xử lý đăng xuất, CRUD như trước.
- Đăng xuất sẽ huỷ phiên trên máy chủ rồi chuyển về `/login.html`.
- API ghi/sửa/xóa vẫn yêu cầu token hợp lệ trên backend. Các trang HTML là tài nguyên tĩnh, vì vậy chuyển hướng bằng JavaScript **không thay thế** cơ chế xác thực API ở máy chủ.
