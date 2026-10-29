# ReMate – Giới hạn danh mục Sản phẩm và Dự án

## Danh mục mới trong Admin

**Tab Sản phẩm** chỉ có 3 lựa chọn:
1. Phế liệu
2. Vật tư
3. Máy móc - thiết bị

**Tab Dự án** chỉ có 4 lựa chọn:
1. Bảo trì - bảo dưỡng
2. Thiết kế - gia công
3. Cải tiến - cải tạo
4. Tư vấn - giải pháp

Danh mục được chọn bằng `select` và bắt buộc khi tạo/sửa bài. Backend trong `server.py` cũng kiểm tra danh mục, ngăn việc gửi một giá trị khác thông qua API.

**Bài đăng cũ:** Không xóa và không tự đổi nhãn cũ. Khi mở bài đang dùng danh mục cũ để **Sửa**, Admin hiển thị cảnh báo và yêu cầu bạn chọn một trong các danh mục mới trước khi lưu. Các nút Ẩn/Hiện của bài cũ vẫn dùng được mà không cần đổi danh mục ngay.

Tab **Đối tác** vẫn có thể nhập lĩnh vực tùy ý; tab **Dịch vụ** vẫn dùng 3 nhóm dịch vụ đã quy định.

## Cập nhật vào website hiện tại

Sao lưu `data/` và `public/uploads/` trước khi cập nhật. Giải nén gói cập nhật và ghi đè đúng bốn file:

- `public/admin.html`
- `public/js/admin.js`
- `public/css/admin.css`
- `server.py`

**Không ghi đè** `data/products.json`, `data/projects.json` hoặc các thư mục ảnh.

Khởi động lại `python server.py`, sau đó vào `http://localhost:3000/login.html`, đăng nhập Admin, nhấn Ctrl+F5.

## Kiểm tra

- Backend/HTTP: 26 trường hợp đạt (danh mục hợp lệ, danh mục sai, sửa bài cũ, ẩn/hiện, bảo toàn tab khác).
- Giao diện Chromium mô phỏng: lựa chọn đúng 3 và 4, hiện cảnh báo danh mục cũ, tab Đối tác và Dịch vụ không bị ảnh hưởng.
- Python và JavaScript qua kiểm tra cú pháp.
