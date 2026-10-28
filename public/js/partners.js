/* Đối tác ReMate: dữ liệu được quản lý qua /admin.html → /api/partners.
   SITE.partners cũ vẫn được hỗ trợ để không làm mất những đối tác đã khai báo thủ công.
   Bài đã ẩn KHÔNG được gửi về phía khách; sự kiện SSE tự tải lại danh sách. */
(function () {
  'use strict';
  const S = window.SITE || {};
  const areas = Array.isArray(S.partnerAreas) ? S.partnerAreas : [];
  const e = window.esc || (s => String(s ?? ''));
  const icon = window.ic || (() => '');
  const safeLink = url => /^https?:\/\//i.test(String(url || '')) ? String(url) : '';
  const imageOK = src => /^(?:\/?(?:img|uploads)\/|https?:\/\/)/i.test(String(src || ''));
  const homeProfiles = document.getElementById('homePartnerProfiles');
  const grid = document.getElementById('partnersGrid');

  // Dữ liệu chuẩn từ backend dùng title/category/summary/images/website.
  function normalize(p) {
    return {
      id: p.id || '', name: p.title || p.name || '',
      logo: (p.images && p.images[0]) || p.logo || '',
      sector: p.category || p.sector || '',
      description: p.summary || p.description || '',
      website: p.website || '',
      featured: !!p.featured,
      createdAt: p.createdAt || ''
    };
  }
  function partnerCard(p) {
    const target = safeLink(p.website);
    const src = String(p.logo || '');
    const logo = imageOK(src)
      ? `<img src="${e(src)}" loading="lazy" alt="Logo ${e(p.name)}">`
      : `<span class="partner-letter" aria-hidden="true">${e(String(p.name).trim().charAt(0).toUpperCase())}</span>`;
    return `<article class="partner-profile reveal">
      <div class="partner-profile-logo">${logo}</div>
      <div class="partner-profile-info"><span class="partner-profile-sector">${e(p.sector || 'Đối tác')}</span><h3>${e(p.name)}</h3>${p.description ? `<p>${e(p.description)}</p>` : ''}
        ${target ? `<a href="${e(target)}" target="_blank" rel="noopener noreferrer" aria-label="Trang web ${e(p.name)}">Website đối tác ↗</a>` : ''}
      </div>
    </article>`;
  }
  const emptyHTML = `<div class="partner-empty reveal"><div class="partner-empty-badge" aria-hidden="true">${icon('recycle')}</div>
    <div><span class="partner-empty-overline">Thông tin đang cập nhật</span><h3>Đối tác sẽ được giới thiệu tại đây</h3>
    <p>ReMate sẽ bổ sung tên, logo và thông tin hợp tác sau khi xác nhận với từng đơn vị. Trong thời gian này, bạn có thể liên hệ để trao đổi cơ hội hợp tác.</p>
    <a href="#lien-he-hop-tac" class="partner-empty-link">Kết nối với ReMate <span aria-hidden="true">→</span></a></div></div>`;

  const areasGrid = document.getElementById('partnerAreas');
  if (areasGrid) areasGrid.innerHTML = areas.map((a, i) => `<article class="partner-area reveal">
    <div class="partner-area-top"><span class="partner-area-icon">${icon(a.icon)}</span><span class="partner-area-number">0${i+1}</span></div>
    <h3>${e(a.title)}</h3><p>${e(a.description)}</p><span class="partner-area-line" aria-hidden="true"></span>
  </article>`).join('');

  async function loadPartners() {
    let serverPartners = [];
    try { serverPartners = (await api('partners')).map(normalize); }
    catch (err) { console.warn('Không tải được danh sách đối tác:', err.message); }
    const legacy = Array.isArray(S.partners) ? S.partners.filter(p => p && p.name).map(normalize) : [];
    const known = new Set(serverPartners.map(p => p.name.trim().toLowerCase()));
    const partners = [...serverPartners, ...legacy.filter(p => !known.has(p.name.trim().toLowerCase()))];

    if (grid) grid.innerHTML = partners.length
      ? `<div class="partners-profiles-grid">${partners.map(partnerCard).join('')}</div>`
      : emptyHTML;
    if (homeProfiles) {
      const selected = [...partners.filter(p => p.featured), ...partners.filter(p => !p.featured)].slice(0, 4);
      homeProfiles.hidden = !selected.length;
      homeProfiles.innerHTML = selected.length
        ? `<div class="partners-home-profiles-head"><span>ĐƠN VỊ ĐỒNG HÀNH</span><a href="doi-tac.html#danh-sach-doi-tac">Xem tất cả đối tác →</a></div>
           <div class="partners-home-profiles">${selected.map(partnerCard).join('')}</div>`
        : '';
    }
    if (typeof window.reveal === 'function') window.reveal();
  }
  loadPartners();
  if (typeof window.onLiveChange === 'function') {
    window.onLiveChange(d => { if (d.type === 'partners') loadPartners(); });
  }
})();
