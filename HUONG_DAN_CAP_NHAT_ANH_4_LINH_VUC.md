# ReMate — Quản lý ảnh bốn lĩnh vực trên trang Giới thiệu

## Chức năng mới

Mở `/login.html`, đăng nhập quản trị, chọn tab **🖼️ Ảnh lĩnh vực**. Bốn thẻ tương ứng bốn lĩnh vực hoạt động trong `/gioi-thieu.html` sẽ xuất hiện theo đúng thứ tự.

- **Tải ảnh lên / Thay ảnh:** chọn ảnh JPG, PNG, WebP hoặc GIF. Trình duyệt tự thu nhỏ ảnh tối đa 900 px cạnh dài và ưu tiên WebP để giữ nền trong suốt. Giới hạn server 5 MiB/ảnh.
- **Mặc định:** xóa ảnh tùy chỉnh của thẻ đó và quay về biểu tượng SVG gốc.
- Chỉ thay ảnh đại diện của mỗi thẻ, **không thay tên, thứ tự hoặc nội dung** bốn lĩnh vực.
- Trang `gioi-thieu.html` tải dữ liệu mới và nhận thông báo realtime qua SSE, không cần sửa JS thủ công.

## Tổ chức dữ liệu

```text
data/expertise-images.json    # 4 bản ghi chỉ số 0–3, URL ảnh, ngày cập nhật
public/expertise/           # Ảnh đã tải lên (khác thư mục Album hoạt động)
```

API: `GET /api/expertise-images` công khai. `PUT /api/expertise-images/0..3` (body JSON `{ "image": "data:image/...;base64,..." }`) và `DELETE /api/expertise-images/0..3` cần Bearer token admin. Xóa hoặc thay ảnh sẽ xóa file ảnh cũ tương ứng. Mỗi lần cập nhật phát SSE `change` với `type = expertise-images`.

## Các file thay đổi / bổ sung

- `server.py` — API và thư mục chứa ảnh theo lĩnh vực
- `public/admin.html` — tab và bảng quản trị bốn ô
- `public/js/admin.js` — chuyển tab
- `public/js/admin-expertise.js` — tải, thay, trả về mặc định
- `public/js/about-album.js` — hiển thị ảnh mới hoặc SVG cũ, cập nhật realtime
- `public/css/admin.css`, `public/css/style.css` — style
- `data/expertise-images.json` — dữ liệu khởi tạo `[]`
- `public/expertise/.gitkeep` — giữ thư mục trống

## Cập nhật vào dự án đang dùng

1. Sao lưu `data/` và `public/` (đặc biệt `public/uploads/`, `public/album/`).
2. Giải nén ZIP **gói cập nhật** vào thư mục gốc ReMate, giữ đúng cấu trúc và ghi đè file trùng.
3. Nếu đã có `data/expertise-images.json` chứa ảnh được lưu trước đó, **không ghi đè** bằng file `[]` trong gói.
4. Khởi động lại `python server.py` để nạp backend mới. Mở `/login.html`, vào `admin.html`, tab **Ảnh lĩnh vực**.
5. Tải ảnh, kiểm tra trong `/gioi-thieu.html`. Nếu trình duyệt giữ ảnh cũ, nhấn `Ctrl+F5`.

Trên Render Free, ảnh mới có thể mất khi dịch vụ tái khởi động: cần volume lưu trữ bền vững hoặc sao lưu `data/expertise-images.json` và `public/expertise/`. Nếu dùng biến môi trường `EXPERTISE_DIR`, hãy trỏ tới thư mục ảnh bền vững phù hợp với hosting.
