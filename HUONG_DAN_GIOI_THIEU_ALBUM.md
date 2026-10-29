# ReMate – Hướng dẫn trang Giới thiệu riêng và Album hình ảnh hoạt động

## Các phần đã thêm

- `public/gioi-thieu.html`: Trang giới thiệu riêng biệt với nội dung giới thiệu doanh nghiệp, lĩnh vực hoạt động và khu vực **Hình ảnh hoạt động**.
- `public/js/about-album.js`: Tải album qua API và hiển thị **carousel cuộn ngang**. Hỗ trợ tự chuyển ảnh (~4,6 giây), mũi tên trái/phải, vuốt trên điện thoại, phím mũi tên trên bàn phím, chọn ảnh bằng dấu chấm, phóng to khi bấm ảnh. Tự dừng khi rê chuột, tập trung bàn phím hoặc ẩn tab; tôn trọng tùy chọn giảm chuyển động của người dùng.
- `public/admin.html`: Tab **📸 Album hoạt động**.
- `public/js/admin-album.js`: Upload nhiều ảnh, kéo thả, nén ảnh, sửa chú thích, chọn/xóa riêng lẻ hoặc xóa hàng loạt.
- `public/css/style.css`, `public/css/admin.css`: Giao diện responsive và thiết kế đồng nhất với ReMate.
- `server.py`: REST API ảnh mới, lưu ảnh album tách biệt.
- `data/album.json`: Danh sách metadata ảnh (tên, chú thích, thời gian tạo).
- `public/album/`: Thư mục ảnh hoạt động, riêng với `public/uploads/` của bài đăng.
- `public/js/common.js`: Menu và footer **Giới thiệu** trỏ đến `gioi-thieu.html`, không nhảy đến section trang chủ.

## Cách sử dụng

1. Mở Terminal tại thư mục ReMate và chạy `python server.py`.
2. Mở `http://localhost:3000/login.html` và đăng nhập.
3. Chọn tab **📸 Album hoạt động** trên Admin.
4. Chọn nhiều ảnh hoặc kéo thả vào khu vực upload. Ảnh JPG/PNG/WebP được tự nén cạnh dài tối đa 1920 px trước khi tải; GIF giữ nguyên để tránh mất chuyển động.
5. Khi ảnh đã được lưu, nhập chú thích và bấm **Lưu chú thích**. Chọn nhiều ảnh bằng các checkbox, có nút **Chọn tất cả** rồi **Xóa ảnh đã chọn**.
6. Truy cập `http://localhost:3000/gioi-thieu.html#hinh-anh-hoat-dong` để xem album. Khi thêm/xóa ảnh, trang công khai đang mở tự cập nhật nhờ SSE.

## Giới hạn và lưu trữ

- **Không đặt giới hạn tổng số ảnh trong album**. Có thể tiếp tục tải lên theo từng đợt.
- **Mỗi ảnh tối đa 8 MiB sau khi nén** trên backend. Mỗi HTTP request tối đa 25 MiB theo cấu hình gốc; ảnh được tải từng file, không gom vào một request.
- Tối đa 500 ID ảnh trong mỗi lệnh xóa hàng loạt ở API. Giao diện Admin tự chia thành đợt nếu chọn nhiều hơn, vì vậy không giới hạn tổng số ảnh có thể xóa.
- Cho phép JPG, PNG, WebP, GIF; backend kiểm tra chữ ký file cơ bản; không nhận SVG.
- Ảnh upload được lưu tại `public/album/`, metadata tại `data/album.json`. Không tự đặt các file vào thư mục `public/uploads`.
- Đặt `ALBUM_DIR` để thay thư mục lưu ảnh nếu dùng ổ đĩa bền vững. Ví dụ Linux: `ALBUM_DIR=/mnt/disk/album DATA_DIR=/mnt/disk/data python server.py`.
- **Cần sao lưu đồng thời `data/album.json` và `public/album/`**. Hai thành phần này phải đi cùng nhau.

## API

| Method | Endpoint | Quyền | Công dụng |
|---|---|---|---|
| GET | `/api/album` | Công khai | Danh sách ảnh, mới nhất trước |
| POST | `/api/album` | Admin | Thêm một ảnh base64 + chú thích (trả 201) |
| PUT | `/api/album/{id}` | Admin | Cập nhật chú thích |
| DELETE | `/api/album/{id}` | Admin | Xóa một ảnh |
| DELETE | `/api/album/selected` | Admin | Xóa một lô `{ "ids": ["...", "..."] }` |
| GET | `/album/<file>` | Công khai | Phân phát ảnh |

Mỗi thao tác tạo/sửa/xóa phát SSE `event: change` với `type: "album"` để trang giới thiệu tự tải lại.

## Cập nhật bản web đang sử dụng

Khuyến nghị sử dụng gói **file thay đổi**. Giải nén vào thư mục ReMate, giữ đường dẫn như trong ZIP, và không ghi đè `data/album.json` nếu đã có ảnh. Khi cập nhật từ bản ReMate cũ chưa có album, file này có thể được tạo mới rỗng `[]`.

Trên bản web đang hoạt động thực tế, **đừng xóa `public/album/` nếu đã upload ảnh**. Trước khi cập nhật hãy sao lưu cả thư mục `data/`, `public/uploads/`, `public/album/`.

## Hosting miễn phí

Nếu chạy trên Render Free và lưu file vào ổ đĩa cục bộ, album ảnh và dữ liệu JSON có thể mất khi dịch vụ ngủ hoặc khởi động lại. Muốn dùng lâu dài cần ổ đĩa bền vững (VPS/VM hoặc persistent disk) hoặc tích hợp lưu ảnh/dữ liệu trên dịch vụ ngoài. Phần lưu trữ mới có thể dùng `ALBUM_DIR` và `DATA_DIR` để trỏ vào ổ đĩa bền vững mà không sửa giao diện.

## Bảo mật

Không sử dụng mật khẩu admin mặc định `remate@2026` khi đưa website lên Internet. Đổi bằng biến môi trường `ADMIN_PASSWORD` và sử dụng HTTPS.
