/* Trang danh sách dùng chung cho Sản phẩm / Dự án — realtime */
(function () {
  const type = document.body.dataset.type; // products | projects
  const box = document.getElementById('list');
  const q = document.getElementById('q');
  const sort = document.getElementById('sort');
  const chips = document.getElementById('chips');
  let all = [], cat = '';
  document.getElementById('live').innerHTML = liveBadge();

  function render() {
    const kw = q.value.trim().toLowerCase();
    let list = all.filter((x) => (!cat || x.category === cat) &&
      (!kw || [x.title, x.summary, x.category, x.client, x.location].join(' ').toLowerCase().includes(kw)));
    if (sort.value === 'old') list = list.slice().reverse();
    if (sort.value === 'az') list = list.slice().sort((a, b) => a.title.localeCompare(b.title, 'vi'));
    document.getElementById('count').textContent = `${list.length} ${type === 'products' ? 'sản phẩm' : 'dự án'}`;
    box.innerHTML = list.length ? list.map((x) => cardHTML(type, x)).join('') : '<div class="empty">Không có kết quả phù hợp.</div>';
    reveal();
  }
  function renderChips() {
    const cats = [...new Set(all.map((x) => x.category).filter(Boolean))];
    if (cat && !cats.includes(cat)) cat = '';
    chips.innerHTML = ['', ...cats].map((c) => `<button class="chip ${c === cat ? 'active' : ''}" data-c="${esc(c)}">${esc(c || 'Tất cả')}</button>`).join('');
  }
  chips.addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (!b) return; cat = b.dataset.c; renderChips(); render(); });
  q.addEventListener('input', render); sort.addEventListener('change', render);

  async function load() {
    try { all = await api(type); renderChips(); render(); }
    catch { box.innerHTML = '<div class="empty">Không tải được dữ liệu.</div>'; }
  }
  load();
  onLiveChange((d) => { if (d.type === type) { load(); if (d.action === 'create') toast('🆕 Vừa có bài đăng mới!'); } });
})();
