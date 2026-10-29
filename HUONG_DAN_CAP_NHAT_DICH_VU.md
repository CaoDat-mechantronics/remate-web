# ReMate — Bổ sung quản lý và danh sách Dịch vụ

Bản nâng cấp này được thực hiện trên **chính source code `remate-website(1).zip`** được cung cấp trong phiên làm việc. Không tái sử dụng bản source khác.

## Chức năng mới

**Admin (`/admin.html`):** Thêm tab `🛠️ Dịch vụ` với biểu mẫu tên dịch vụ, chọn 1 trong 3 nhóm đã xác định, mô tả ngắn bắt buộc, mô tả chi tiết, tối đa 12 hình, 30 thuộc tính tùy chỉnh, nổi bật và công khai. Hỗ trợ thêm, sửa, ẩn/hiện, xóa và xem trước. Ảnh bị gỡ hoặc xóa bài sẽ được xóa khỏi thư mục uploads như các loại bài đăng khác.

**Trang công khai (`/dich-vu.html`):** Giữ nguyên phần giới thiệu 3 nhóm, thêm phần `Các dịch vụ ReMate cung cấp` sau các phần giới thiệu; lọc theo nhóm (có số lượng), tìm kiếm theo tiêu đề, nhóm, mô tả và thuộc tính, hiển thị dịch vụ chia theo các nhóm. Có cập nhật realtime. Mỗi dịch vụ có trang `chi-tiet.html?type=services&id=<slug>` với bảng thuộc tính và hình ảnh.

**Dữ liệu & API:** Thêm `data/services.json` (mặc định `[]`), `GET /api/services`, `GET /api/services/{id hoặc slug}`, `POST /api/services`, `PUT /api/services/{id}`, `DELETE /api/services/{id}`. Các thao tác ghi yêu cầu phiên Admin hợp lệ. Bài ẩn không hiển thị với khách.

## Danh sách 3 nhóm mặc định

1. Kiểm tra, bảo trì thiết bị tại nhà máy
2. Thiết kế, gia công, chế tạo máy theo yêu cầu
3. Đo đạc, tư vấn, triển khai các giải pháp tiết kiệm năng lượng

Mã nguồn phía frontend định nghĩa nhóm tại `public/js/config.js` (SITE.serviceGroups), phía server xác nhận nhóm trong `server.py` (SERVICE_GROUPS). Muốn sửa tên nhóm, sửa cả hai nơi và cân nhắc cập nhật các bài đã lưu trong `data/services.json`.

## Hướng dẫn cập nhật nếu website đang chạy

1. **Sao lưu thư mục `data/` và `public/uploads/`** trước khi cập nhật.
2. Dùng file `remate-cap-nhat-tu-source-da-gui.zip` để giải nén đè vào thư mục gốc của dự án (nơi có `server.py`). Các đường dẫn bên trong ZIP khớp cấu trúc thư mục hiện tại.
3. Nếu đã có `data/services.json` với dữ liệu thật, **không ghi đè** bằng file `[]` trong gói cập nhật.
4. Khởi động lại `python server.py` (hoặc restart dịch vụ đang chạy).
5. Truy cập `/login.html` → `/admin.html` → tab `🛠️ Dịch vụ` → thêm dịch vụ.
6. Truy cập `/dich-vu.html#dich-vu-da-dang`, nhấn `Ctrl + F5` nếu trình duyệt còn cache file JS/CSS cũ.

Nếu muốn dựng website mới từ đầu, giải nén `remate-website-da-bo-sung-quan-ly-dich-vu.zip` rồi chạy `python server.py`.

## Phần được giữ nguyên

- Hai cơ sở Thái Nguyên và Hà Nội, vị trí Google Maps, số điện thoại, email, mạng xã hội, ngân hàng.
- Trang Sản phẩm, Dự án, Đối tác; giao diện đăng nhập riêng, quản trị nội dung cũ.
- Toàn bộ ảnh logo, favicon, flyer, p1, p2, p3 trong ZIP gốc.

**Lưu ý hosting:** Lưu trữ JSON và `public/uploads/` cần ổ đĩa bền vững. Deploy trên hosting có hệ thống file tạm có thể làm mất nội dung mới sau khi khởi động lại.
