/* Ảnh lớn của 3 nhóm trên trang Dịch vụ, có thể đổi từ Admin. */
(() => {
  const defaults = ['img/p1.jpg', 'img/p2.jpg'];
  async function refresh() {
    let entries;
    try { entries = await api('service-covers'); }
    catch (e) { console.warn('Không tải được ảnh nhóm dịch vụ:', e); return; }
    document.querySelectorAll('[data-cover-index]').forEach(section => {
      const index = Number(section.dataset.coverIndex);
      const item = entries.find(x => x.index === index);
      const src = (item && item.src) || '';
      const img = section.querySelector(':scope > img');
      if (!img) return;
      const illustration = section.querySelector('.rm-energy-visual-inner');
      if (index < 2) {
        const desired = src || defaults[index];
        if (img.getAttribute('src') !== desired) img.setAttribute('src', desired);
      } else {
        if (src) {
          if (img.getAttribute('src') !== src) img.setAttribute('src', src);
          img.hidden = false;
          if (illustration) illustration.hidden = true;
        } else {
          img.hidden = true;
          img.removeAttribute('src');
          if (illustration) illustration.hidden = false;
        }
      }
    });
  }
  refresh();
  onLiveChange(e => { if (e.type === 'service-covers') refresh(); });
})();
