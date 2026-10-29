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


## Trang Đối tác (bổ sung)

- Trang công khai: `http://localhost:3000/doi-tac.html`. Thanh menu có tab **Đối tác**.
- Trang chủ có section **Mạng lưới hợp tác** ngay trước mục Liên hệ.
- Danh sách được lấy từ **`GET /api/partners`**, quản lý trong `admin.html` và lưu vào `data/partners.json`.
- Logo tải trực tiếp từ admin sẽ lưu trong `public/uploads/`; không cần tạo file ảnh hay chỉnh sửa mã nguồn thủ công.
- Các nhóm lĩnh vực hợp tác được cấu hình qua `SITE.partnerAreas` trong `public/js/config.js`.
- Các mục `SITE.partners` đã khai báo thủ công từ phiên bản trước vẫn được hiển thị để tương thích; không cần khai báo thủ công cho đối tác mới.
- Các đối tác chưa được đồng ý công khai nên để trạng thái **Ẩn** trong admin.


## Quản lý Đối tác từ Admin — Bản cập nhật

1. Mở `http://localhost:3000/login.html`, đăng nhập tài khoản quản trị.
2. Trong `admin.html`, chọn tab **🤝 Đối tác** → **+ Bài mới**.
3. Nhập **Tên đối tác**, **Lĩnh vực hợp tác**, **Giới thiệu ngắn**, **Website** (không bắt buộc, http/https) và tải **1 logo**.
4. Chọn **Ưu tiên giới thiệu trên trang chủ** nếu muốn đối tác xuất hiện trước; bật **Hiển thị công khai** khi đã được phép công bố.
5. Nhấn **Thêm đối tác**. Trang `/doi-tac.html` và mục Đối tác trên trang chủ sẽ tự cập nhật qua SSE, không cần F5.
6. Trong danh sách bên phải có thể **Sửa / Ẩn-Hiện / Xem / Xóa**. Ảnh logo đã upload sẽ được xóa khi thay hoặc xóa đối tác.

API: `GET /api/partners` công khai (chỉ bài published); `POST /api/partners`, `PUT /api/partners/:id`, `DELETE /api/partners/:id` đòi token quản trị.
Dữ liệu lưu trong `data/partners.json` và `public/uploads/`. **Không mất dữ liệu** khi cập nhật mã nguồn nếu giữ nguyên hai đường dẫn này; hosting ổ đĩa tạm như Render Free vẫn có rủi ro mất nội dung khi khởi động lại.


## Giao diện dịch vụ và TikTok (cập nhật)

- `public/dich-vu.html`: trang **Dịch vụ cung cấp**, liên kết từ nút ở phần hero của trang chủ.
- `public/san-pham.html` vẫn hoạt động như cũ nhưng không nằm trên thanh menu hoặc danh mục footer. Khách có thể mở trang bằng các nút **Sản phẩm kinh doanh** và **Tất cả sản phẩm** trên trang chủ (URL trực tiếp vẫn hoạt động).
- `public/du-an.html` và quản trị dự án được giữ nguyên.
- TikTok được thêm vào cụm nút nổi (và footer, trang Liên hệ, trang Chi tiết). **Hãy sửa `tiktok` trong `public/js/config.js` thành URL kênh TikTok chính thức của ReMate**; mặc định đang dẫn đến `https://www.tiktok.com/` vì chưa có đường dẫn cụ thể. Đặt `tiktok: ''` để ẩn nút khi chưa có kênh.


## Nâng cấp: Quản lý Dịch vụ (từ bản source `remate-website(1).zip`)

- `admin.html` có tab **🛠️ Dịch vụ**, bên cạnh Sản phẩm, Dự án, Đối tác.
- Bài dịch vụ gồm: tên (bắt buộc), **nhóm dịch vụ** (chọn trong 3 nhóm), mô tả ngắn (bắt buộc), mô tả chi tiết, hình ảnh tối đa 12, tối đa 30 thuộc tính tùy chỉnh (tương tự thông số sản phẩm), Nổi bật, Hiển thị công khai.
- Ba nhóm cố định được định nghĩa trong `SITE.serviceGroups` ở `public/js/config.js`; backend dùng danh sách cùng tên trong `SERVICE_GROUPS` tại `server.py`. Nếu thay đổi tên nhóm, **phải sửa đồng bộ ở hai file**.
- API mới: `GET /api/services` (khách chỉ thấy bài công khai), `GET /api/services/{id-hoặc-slug}`, `POST /api/services`, `PUT /api/services/{id}`, `DELETE /api/services/{id}` (các thao tác ghi cần token admin).
- Dữ liệu nằm trong `data/services.json` và ảnh đăng từ Admin nằm trong `public/uploads/`. `data/services.json` ban đầu là mảng rỗng (`[]`).
- Trang `public/dich-vu.html` vẫn giữ nguyên giới thiệu ba nhóm và thêm phần **Các dịch vụ ReMate cung cấp** bên dưới: tìm kiếm theo tên/mô tả/thuộc tính, lọc nhóm, chia danh sách thành từng nhóm, thẻ dịch vụ và cập nhật realtime SSE.
- Khách bấm vào thẻ để mở `chi-tiet.html?type=services&id=<slug>` và xem thuộc tính cùng hình ảnh.
- **Khi nâng cấp website có dữ liệu thật**: Sao lưu `data/` và `public/uploads/`, chỉ chép các file trong gói cập nhật thay vì ghi đè toàn bộ; nếu đã có `data/services.json` thì không thay thế bằng file mẫu rỗng.
- Nếu dùng Render Free với lưu trữ JSON/ảnh hiện tại, nội dung mới có thể mất khi máy ngủ hoặc deploy lại. Cần ổ lưu trữ bền vững để vận hành lâu dài.
