/* =========================================================
   THÔNG TIN CÔNG TY — chỉ cần sửa file này để cập nhật toàn site
   ========================================================= */
window.SITE = {
  name: 'ReMate',
  fullName: 'CÔNG TY CỔ PHẦN VẬT TƯ TÁI SỬ DỤNG REMATE',
  slogan: 'Chi phí tối ưu – Giá trị tối đa',
  headline: 'Giải pháp bền vững cho sản xuất hiện đại',
  intro: 'ReMate cung cấp vật tư, máy móc đã qua sử dụng và triển khai các giải pháp kỹ thuật giúp doanh nghiệp tối ưu chi phí, tiết kiệm năng lượng, nâng cao hiệu suất sản xuất.',
  tagline: 'Đồng hành cùng doanh nghiệp trên hành trình phát triển bền vững',

  phone: '032 675 2517',
  phoneRaw: '0326752517',
  email: 'Datnguyenvan1903@gmail.com',
  address: 'Xóm 17, Xã Đồng Hỷ, Thái Nguyên',
  bankAccount: '8510205068978',
  bankName: 'Agribank',

  // ⚠️ THAY bằng link fanpage Facebook thật của công ty
  facebook: 'https://www.facebook.com/share/1GyrXUiFRZ/?mibextid=wwXIfr',
  zalo: 'https://zalo.me/0326752517',
  // TODO: chưa có link tài khoản TikTok chính thức; thay địa chỉ này bằng URL kênh ReMate.
  // Để chuỗi rỗng '' nếu muốn tạm ẩn nút TikTok.
  tiktok: 'https://www.tiktok.com/@dattotbung?_r=1&_t=ZS-9Aw6fqmqA7w',
  // Google Maps nhúng (tìm theo địa chỉ)
  mapEmbed: 'https://www.google.com/maps?q=X%C3%A3%20%C4%90%E1%BB%93ng%20H%E1%BB%B7%2C%20Th%C3%A1i%20Nguy%C3%AAn&output=embed',

  // 4 lĩnh vực hoạt động chính của ReMate (hiển thị ở trang chủ và footer).
  services: [
    { icon: 'recycle', title: 'Mua bán vật tư, máy móc đã qua sử dụng' },
    { icon: 'wrench', title: 'Kiểm tra, bảo trì thiết bị tại nhà máy' },
    { icon: 'gear', title: 'Thiết kế, gia công, chế tạo máy theo yêu cầu' },
    { icon: 'leaf', title: 'Đo đạc, tư vấn, triển khai các giải pháp tiết kiệm năng lượng' }
  ],
  // Danh sách đối tác hiện được quản lý trực tiếp từ trang admin (data/partners.json).
  // Nếu trước đây đã thêm đối tác thủ công, vẫn có thể giữ ở mảng sau (tương thích phiên bản cũ).
  partners: [],

  // Lĩnh vực hợp tác: đồng bộ tên và thứ tự với 4 lĩnh vực hoạt động trên trang chủ.
  partnerAreas: [
    { icon: 'recycle', title: 'Mua bán vật tư, máy móc đã qua sử dụng', description: 'Kết nối các đơn vị có nhu cầu mua bán, cung ứng hoặc tái sử dụng vật tư, máy móc công nghiệp.' },
    { icon: 'wrench', title: 'Kiểm tra, bảo trì thiết bị tại nhà máy', description: 'Phối hợp khảo sát, kiểm tra tình trạng thiết bị và triển khai công việc bảo trì tại nhà máy.' },
    { icon: 'gear', title: 'Thiết kế, gia công, chế tạo máy theo yêu cầu', description: 'Kết nối năng lực thiết kế kỹ thuật, gia công cơ khí và chế tạo máy đáp ứng nhu cầu thực tế.' },
    { icon: 'leaf', title: 'Đo đạc, tư vấn, triển khai các giải pháp tiết kiệm năng lượng', description: 'Phối hợp đo đạc, đánh giá hiện trạng và đề xuất các giải pháp sử dụng năng lượng hiệu quả.' }
  ],

  // 3 thế mạnh (theo ấn phẩm giới thiệu)
  highlights: [
    { icon: 'gear', img: '/img/p1.jpg', title: 'Kiểm tra – Bảo trì thiết bị', desc: 'Đảm bảo vận hành an toàn, ổn định' },
    { icon: 'wrench', img: '/img/p2.jpg', title: 'Gia công – Chế tạo kết cấu', desc: 'Linh hoạt theo yêu cầu khách hàng' },
    { icon: 'truck', img: '/img/p3.jpg', title: 'Vật tư công nghiệp đã qua sử dụng', desc: 'Đa dạng chủng loại – Chất lượng đảm bảo' }
  ]
};

/* Bộ icon SVG dùng chung */
window.ICONS = {
  recycle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 19H4.8a1.8 1.8 0 0 1-1.6-2.7l1.3-2.2"/><path d="M11 19h8.2a1.8 1.8 0 0 0 1.6-2.7l-1.2-2"/><path d="m14 16-3 3 3 3"/><path d="M8.3 13.6 7.2 9.4 3 10.5"/><path d="m9.3 5.6 1.1-1.9a1.8 1.8 0 0 1 3.1 0l3.9 6.8"/><path d="m13.4 9.4 4.2 1.1 1.1-4.2"/></svg>',
  leaf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M2 21c0-3 1.9-5.4 5.1-6"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 16v-3M11 16v-6M15 16V8M19 16V5"/><path d="m6 9 4-4 3 3 6-5"/></svg>',
  wrench: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9l-3.8 3.8Z"/></svg>',
  truck: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.6a1 1 0 0 0-.2-.6l-3.5-4.4A1 1 0 0 0 17.5 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1Z"/></svg>',
  mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z"/></svg>',
  bank: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2 2 7v2h20V7L12 2ZM4 11v7h3v-7H4Zm6.5 0v7h3v-7h-3ZM17 11v7h3v-7h-3ZM2 20v2h20v-2H2Z"/></svg>',
  facebook: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 13.5h2.5l1-4H14v-2c0-1 0-2 2-2h1.5V2.1A28 28 0 0 0 14.6 2C11.9 2 10 3.7 10 6.7v2.8H7v4h3V22h4v-8.5Z"/></svg>',
  zalo: '<svg viewBox="0 0 48 48"><text x="24" y="29" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="14" fill="#fff">Zalo</text></svg>',
  tiktok: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.7 2h-3.8v12.9a3.3 3.3 0 1 1-3.3-3.3c.3 0 .6 0 .9.1V7.8a7.2 7.2 0 0 0-.9-.1A7.2 7.2 0 1 0 16.8 15V8.3c1.4 1 3.1 1.6 4.9 1.7V6.2c-2.8-.2-4.6-1.8-5-4.2Z"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  live: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/></svg>'
};
