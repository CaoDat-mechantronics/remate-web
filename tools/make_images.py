"""
Tạo các ảnh của website từ ẢNH ẤN PHẨM GIỚI THIỆU ReMate (1536x1024).
Cách dùng:  python tools/make_images.py <đường_dẫn_ảnh_ấn_phẩm.png>
            python tools/make_images.py --placeholder   (chưa có ảnh ấn phẩm → tạo ảnh tạm màu xanh để chạy thử)
Yêu cầu:    pip install pillow   (chỉ cần cho bước tạo ảnh; server.py KHÔNG cần)
Kết quả:    public/img/logo-full.png, logo-icon.png (nền trong suốt), p1.jpg, p2.jpg, p3.jpg, flyer.jpg
"""
import sys
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "public" / "img"


def transparent(img):
    """Biến nền sáng (gần trắng) thành trong suốt cho logo."""
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if r > 200 and g > 200 and b > 195:
                px[x, y] = (r, g, b, 0)
    return img


def main(src):
    OUT.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    if im.size != (1536, 1024):
        im = im.resize((1536, 1024))
    transparent(im.crop((215, 30, 640, 300))).save(OUT / "logo-full.png")   # logo + chữ ReMate
    transparent(im.crop((295, 30, 525, 215))).save(OUT / "logo-icon.png")   # chỉ biểu tượng
    im.crop((0, 600, 262, 895)).save(OUT / "p1.jpg", quality=90)           # Kiểm tra – bảo trì thiết bị
    im.crop((335, 600, 625, 895)).save(OUT / "p2.jpg", quality=90)         # Gia công – chế tạo kết cấu
    im.crop((705, 610, 1005, 895)).save(OUT / "p3.jpg", quality=90)        # Vật tư đã qua sử dụng
    im.save(OUT / "flyer.jpg", quality=88)                                 # Ấn phẩm đầy đủ
    print("Đã tạo ảnh trong", OUT)


def placeholder():
    """Tạo ảnh tạm (khi chưa có ảnh ấn phẩm) để website chạy được ngay."""
    from PIL import ImageDraw
    OUT.mkdir(parents=True, exist_ok=True)
    green, light = (36, 96, 58), (214, 229, 208)

    def block(size, label, bg=green, fg=(255, 255, 255), mode="RGB"):
        img = Image.new(mode, size, bg)
        d = ImageDraw.Draw(img)
        w, h = size
        d.rectangle([4, 4, w - 5, h - 5], outline=fg, width=3)
        d.text((w // 2, h // 2), label, fill=fg, anchor="mm")
        return img

    block((425, 270), "ReMate (logo)", (0, 0, 0, 0), green, "RGBA").save(OUT / "logo-full.png")
    block((230, 185), "ReMate", (0, 0, 0, 0), green, "RGBA").save(OUT / "logo-icon.png")
    block((262, 295), "Anh 1 - Bao tri").save(OUT / "p1.jpg", quality=90)
    block((290, 295), "Anh 2 - Gia cong").save(OUT / "p2.jpg", quality=90)
    block((300, 285), "Anh 3 - Vat tu").save(OUT / "p3.jpg", quality=90)
    block((1536, 1024), "An pham gioi thieu ReMate", light, green).save(OUT / "flyer.jpg", quality=88)
    print("Đã tạo ẢNH TẠM trong", OUT, "- thay bằng ảnh thật khi có.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Cách dùng: python tools/make_images.py <anh_an_pham.png> | --placeholder")
    if sys.argv[1] == "--placeholder":
        placeholder()
    else:
        main(sys.argv[1])
