/* Phần dùng chung: header, footer, nút liên hệ nổi, API, realtime */
(function () {
  const S = window.SITE, I = window.ICONS;
  const ic = (n) => `<span class="ic">${I[n] || ''}</span>`;
  const page = document.body.dataset.page || '';

  window.esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  window.ic = ic;
  window.fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString('vi-VN'); } catch { return ''; } };

  /* ---------- Header ---------- */
  const nav = [
    ['index.html', 'Trang chủ', 'home'], ['index.html#gioi-thieu', 'Giới thiệu', 'about'],
    ['du-an.html', 'Dự án', 'projects'],
    ['doi-tac.html', 'Đối tác', 'partners'], ['index.html#lien-he', 'Liên hệ', 'contact']
  ];
  const header = `
  <div class="topbar"><div class="container">
    <div><a href="tel:${S.phoneRaw}">${ic('phone')} ${S.phone}</a><a class="hide-sm" href="mailto:${S.email}">${ic('mail')} ${S.email}</a></div>
    <div><a class="hide-sm" href="index.html#lien-he" title="Xem địa chỉ hai cơ sở">${ic('pin')} 2 cơ sở: Thái Nguyên · Hà Nội</a><a href="${S.facebook}" target="_blank" rel="noopener">${ic('facebook')} Facebook</a></div>
  </div></div>
  <header class="header"><div class="container">
    <a class="brand" href="index.html"><img src="img/logo-icon.png" alt="ReMate logo"><span><b>ReMate</b><small>VẬT TƯ TÁI SỬ DỤNG</small></span></a>
    <nav class="nav" id="nav">
      ${nav.map(([h, t, k]) => `<a href="${h}" class="${k === page ? 'active' : ''}">${t}</a>`).join('')}
    </nav>
    <button class="burger" id="burger" aria-label="Mở menu"><span></span><span></span><span></span></button>
  </div></header>`;

  const footer = `
  <footer class="footer"><div class="container">
    <div class="footer-grid">
      <div><div class="logo-w"><img src="img/logo-icon.png" alt=""><b>ReMate</b></div>
        <p style="font-size:14.5px">${S.fullName}<br><i>${S.slogan}</i></p>
      </div>
      <div><h4>Danh mục</h4><ul>${nav.map(([h, t]) => `<li><a href="${h}">${t}</a></li>`).join('')}</ul></div>
      <div><h4>Lĩnh vực</h4><ul>${S.services.map((s) => `<li>${s.title}</li>`).join('')}</ul></div>
      <div><h4>Liên hệ</h4><ul>
        <li><a href="tel:${S.phoneRaw}">📞 ${S.phone}</a></li><li><a href="mailto:${S.email}">✉️ ${S.email}</a></li>
        ${(S.branches || []).map((b) => `<li>📍 <a href="${esc(b.mapsUrl)}" target="_blank" rel="noopener noreferrer"><strong>${esc(b.name)}:</strong> ${esc(b.address)}</a></li>`).join('')}<li>🏦 ${S.bankAccount} – ${S.bankName}</li></ul></div>
    </div>
    <div class="bottom">© ${new Date().getFullYear()} ${S.fullName}. ${S.tagline}.</div>
  </div></footer>
  <div class="float">
    <a class="f-fb" href="${S.facebook}" target="_blank" rel="noopener" title="Facebook">${ic('facebook')}</a>
    <a class="f-zl" href="${S.zalo}" target="_blank" rel="noopener noreferrer" title="Chat Zalo" aria-label="Chat Zalo">${ic('zalo')}</a>
    ${S.tiktok ? `<a class="f-tt" href="${S.tiktok}" target="_blank" rel="noopener noreferrer" title="TikTok ReMate (cập nhật liên kết chính thức trong config.js)" aria-label="TikTok">${ic('tiktok')}</a>` : ''}
    <a class="f-ph" href="tel:${S.phoneRaw}" title="Gọi ${S.phone}" aria-label="Gọi ${S.phone}">${ic('phone')}</a>
  </div>
  <div class="toast" id="toast"></div>
  <div class="lightbox" id="lightbox"><img alt=""></div>`;

  document.getElementById('site-header').innerHTML = header;
  document.getElementById('site-footer').innerHTML = footer;
  const navEl = document.getElementById('nav');
  document.getElementById('burger').addEventListener('click', () => navEl.classList.toggle('open'));
  navEl.addEventListener('click', (e) => { if (e.target.closest('a')) navEl.classList.remove('open'); });

  /* ---------- Tiện ích ---------- */
  window.toast = (msg) => {
    const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show');
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 3200);
  };
  window.lightbox = (src) => {
    const lb = document.getElementById('lightbox'); lb.querySelector('img').src = src; lb.classList.add('open');
  };
  document.getElementById('lightbox').addEventListener('click', (e) => e.currentTarget.classList.remove('open'));

  window.api = async (path, opt = {}) => {
    const r = await fetch('/api/' + path, opt);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || 'Lỗi máy chủ');
    return data;
  };

  const isNew = (iso) => Date.now() - new Date(iso).getTime() < 3 * 24 * 3600 * 1000;
  window.cardHTML = (type, x) => {
    const img = (x.images && x.images[0]) || 'img/logo-icon.png';
    const href = `chi-tiet.html?type=${type}&id=${encodeURIComponent(x.slug || x.id)}`;
    const meta = type === 'products'
      ? `<span class="price">${esc(x.price || 'Liên hệ')}</span>`
      : type === 'services' ? '<span class="service-card-label">Dịch vụ kỹ thuật</span>'
      : `<span>📅 ${esc(x.time || fmtDate(x.createdAt))}</span>`;
    return `<a class="card reveal" href="${href}">
      <div class="thumb"><img src="${esc(img)}" alt="${esc(x.title)}" loading="lazy">
        ${x.category ? `<span class="tag">${esc(x.category)}</span>` : ''}${isNew(x.createdAt) ? '<span class="new">MỚI</span>' : ''}</div>
      <div class="body"><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p>
        <div class="meta">${meta}<span class="more">Xem chi tiết ${ic('arrow')}</span></div></div></a>`;
  };

  /* ---------- Realtime (SSE) ---------- */
  const listeners = [];
  window.onLiveChange = (fn) => listeners.push(fn);
  function connect() {
    if (!window.EventSource) return;
    const es = new EventSource('/api/stream');
    const badges = () => document.querySelectorAll('.live');
    es.onopen = () => badges().forEach((b) => { b.classList.remove('off'); b.lastChild.textContent = ' Cập nhật trực tiếp'; });
    es.onerror = () => badges().forEach((b) => { b.classList.add('off'); b.lastChild.textContent = ' Đang kết nối lại…'; });
    es.addEventListener('change', (e) => {
      const d = JSON.parse(e.data);
      listeners.forEach((fn) => fn(d));
    });
  }
  connect();
  window.liveBadge = () => `<span class="live">${ic('live')}<span> Cập nhật trực tiếp</span></span>`;

  /* ---------- Hiệu ứng xuất hiện ---------- */
  const io = 'IntersectionObserver' in window ? new IntersectionObserver((es) => es.forEach((en) => {
    if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
  }), { threshold: 0.08 }) : null;
  window.reveal = () => document.querySelectorAll('.reveal:not(.in)').forEach((el) => io ? io.observe(el) : el.classList.add('in'));
  document.addEventListener('DOMContentLoaded', reveal);
})();
