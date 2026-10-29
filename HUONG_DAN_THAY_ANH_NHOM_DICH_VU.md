# Thay ảnh đại diện 3 nhóm dịch vụ – ReMate

## Kết quả

Thêm tab **🏭 Ảnh nhóm dịch vụ** vào `admin.html`, cho phép tải ảnh riêng cho 3 khung lớn trên `dich-vu.html` (không phải ảnh của bài đăng dịch vụ). Nhóm 1 và 2 mặc định dùng `p1.jpg`, `p2.jpg`; nhóm 3 dùng minh họa ENERGY. Nút **Mặc định** khôi phục thiết kế này.

- API: `GET /api/service-covers` công khai (3 bản ghi, `index` 0–2).
- API cần token Admin: `PUT /api/service-covers/<index>` với body JSON `{"image":"data:image/webp;base64,..."}`, `DELETE /api/service-covers/<index>`.
- Ảnh lưu ở `public/service-covers/`, thông tin lưu ở `data/service-covers.json`. Mỗi nhóm 1 ảnh, tối đa 6 MiB/ảnh sau nén.
- Upload/thay/xóa sẽ thông báo SSE `change`, `type: service-covers`.

## Cập nhật website có sẵn

1. Sao lưu thư mục `data/`, `public/uploads/`, `public/album/`, `public/expertise/`.
2. Giải nén gói cập nhật vào gốc `remate-website`, giữ đúng đường dẫn. **Nếu `data/service-covers.json` đã có ảnh, không ghi đè file này.**
3. Khởi động lại `python server.py`; truy cập `login.html`, mở tab **🏭 Ảnh nhóm dịch vụ**.
4. Chọn ảnh từng nhóm; mở `dich-vu.html` để xác nhận. Bấm Ctrl+F5 nếu còn bản cache cũ.

Lưu ý: Với hosting có ổ đĩa tạm, cần lưu bền vững hoặc sao lưu cả `data/service-covers.json` và `public/service-covers/` để không mất ảnh mới upload.
