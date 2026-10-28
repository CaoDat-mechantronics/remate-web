/* Trang quản trị nội dung: cần phiên đăng nhập hợp lệ từ login.html. */
(function () {
  const $ = (s) => document.querySelector(s);
  const form = $('#postForm');
  const F = form.elements;
  let token = sessionStorage.getItem('remate_token') || '';
  let type = 'products', editingId = null, images = [], items = [];

  const redirectToLogin = () => {
    sessionStorage.removeItem('remate_token');
    token = '';
    window.location.replace('login.html');
  };

  const authApi = async (path, opt = {}) => {
    try {
      return await api(path, { ...opt, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token, ...(opt.headers || {}) } });
    } catch (err) {
      if (/cần đăng nhập admin|unauthorized/i.test(err.message)) redirectToLogin();
      throw err;
    }
  };

  /* ---------- Kiểm tra quyền vào trang quản trị ---------- */
  async function check() {
    if (!token) { redirectToLogin(); return; }
    try {
      const result = await authApi('me');
      if (!result.ok) { redirectToLogin(); return; }
      $('#authGate').hidden = true;
      $('#appView').hidden = false;
      switchType('products');
    } catch (_) { redirectToLogin(); }
  }

  $('#logout').addEventListener('click', async () => {
    await authApi('logout', { method: 'POST' }).catch(() => {});
    redirectToLogin();
  });

  /* ---------- Chuyển tab ---------- */
  document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => switchType(t.dataset.type)));
  function switchType(t) {
    type = t;
    document.querySelectorAll('.tab').forEach((x) => x.classList.toggle('active', x.dataset.type === t));
    document.querySelectorAll('.only-p').forEach((el) => (el.style.display = t === 'products' ? '' : 'none'));
    document.querySelectorAll('.only-j').forEach((el) => (el.style.display = t === 'projects' ? '' : 'none'));
    $('#listTitle').textContent = t === 'products' ? 'Danh sách sản phẩm' : 'Danh sách dự án';
    resetForm(); loadList();
  }

  /* ---------- Danh sách ---------- */
  async function loadList() {
    try { items = await authApi(type); } catch (e) { if (/đăng nhập/i.test(e.message)) return redirectToLogin(); items = []; }
    $('#catList').innerHTML = [...new Set(items.map((x) => x.category).filter(Boolean))].map((c) => `<option>${esc(c)}</option>`).join('');
    renderList();
  }
  function renderList() {
    const kw = $('#filter').value.toLowerCase();
    const list = items.filter((x) => !kw || x.title.toLowerCase().includes(kw));
    $('#postList').innerHTML = list.length ? list.map((x) => `
      <div class="post ${x.id === editingId ? 'editing' : ''}" data-id="${x.id}">
        <img src="${esc((x.images || [])[0] || 'img/logo-icon.png')}" alt="">
        <div><b>${esc(x.title)}${x.featured ? '<span class="pill star">★ Nổi bật</span>' : ''}${x.published ? '' : '<span class="pill hide">Ẩn</span>'}</b>
          <small>${esc(x.category || '—')} · ${fmtDate(x.createdAt)}</small></div>
        <div class="acts">
          <button class="btn btn-sm btn-light" data-act="edit">✏️ Sửa</button>
          <button class="btn btn-sm btn-light" data-act="toggle">${x.published ? '🙈 Ẩn' : '👁 Hiện'}</button>
          <a class="btn btn-sm btn-light" target="_blank" href="chi-tiet.html?type=${type}&id=${x.slug}">↗ Xem</a>
          <button class="btn btn-sm btn-danger" data-act="del">🗑 Xóa</button>
        </div></div>`).join('') : '<div class="empty">Chưa có bài nào.</div>';
  }
  $('#filter').addEventListener('input', renderList);
  $('#postList').addEventListener('click', async (e) => {
    const b = e.target.closest('button[data-act]'); if (!b) return;
    const x = items.find((i) => i.id === b.closest('.post').dataset.id);
    if (b.dataset.act === 'edit') return fillForm(x);
    if (b.dataset.act === 'toggle') {
      await authApi(`${type}/${x.id}`, { method: 'PUT', body: JSON.stringify({ ...x, published: !x.published }) });
      toast(x.published ? 'Đã ẩn bài' : 'Đã hiển thị bài'); return loadList();
    }
    if (b.dataset.act === 'del' && confirm(`Xóa "${x.title}"? Thao tác không thể hoàn tác.`)) {
      await authApi(`${type}/${x.id}`, { method: 'DELETE' });
      if (editingId === x.id) resetForm();
      toast('Đã xóa'); loadList();
    }
  });

  /* ---------- Form ---------- */
  const FIELDS = ['title', 'category', 'summary', 'content', 'price', 'condition', 'quantity', 'origin', 'client', 'location', 'time', 'scope', 'result'];
  function resetForm() {
    editingId = null; images = []; form.reset(); F.published.checked = true;
    $('#specs').innerHTML = ''; if (type === 'products') { addSpec(); addSpec(); }
    renderImgs(); renderList();
    $('#formTitle').textContent = type === 'products' ? 'Đăng sản phẩm mới' : 'Đăng dự án mới';
    $('#saveBtn').textContent = '💾 Đăng bài';
  }
  function fillForm(x) {
    resetForm(); editingId = x.id;
    FIELDS.forEach((f) => { if (F[f]) F[f].value = x[f] || ''; });
    F.featured.checked = !!x.featured; F.published.checked = x.published !== false;
    images = [...(x.images || [])]; renderImgs();
    $('#specs').innerHTML = ''; (x.specs || []).forEach((s) => addSpec(s.key, s.value)); if (type === 'products' && !(x.specs || []).length) addSpec();
    $('#formTitle').textContent = 'Sửa: ' + x.title; $('#saveBtn').textContent = '💾 Lưu thay đổi';
    renderList(); form.scrollIntoView({ behavior: 'smooth' });
  }
  $('#resetBtn').addEventListener('click', resetForm);

  function addSpec(k = '', v = '') {
    const d = document.createElement('div'); d.className = 'spec';
    d.innerHTML = `<input placeholder="Thông số (VD: Công suất)" value="${esc(k)}"><input placeholder="Giá trị (VD: 37 kW)" value="${esc(v)}"><button type="button" title="Xóa">✕</button>`;
    d.querySelector('button').onclick = () => d.remove();
    $('#specs').appendChild(d);
  }
  $('#addSpec').addEventListener('click', () => addSpec());

  /* ---------- Ảnh: nén phía trình duyệt ---------- */
  function compress(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => {
        const img = new Image();
        img.onload = () => {
          const max = 1600, k = Math.min(1, max / Math.max(img.width, img.height));
          const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          resolve(c.toDataURL('image/jpeg', 0.85));
        };
        img.onerror = reject; img.src = r.result;
      };
      r.onerror = reject; r.readAsDataURL(file);
    });
  }
  async function addFiles(files) {
    for (const f of [...files].filter((f) => f.type.startsWith('image/'))) {
      if (images.length >= 12) { toast('Tối đa 12 ảnh'); break; }
      images.push(await compress(f));
    }
    renderImgs();
  }
  function renderImgs() {
    $('#imgs').innerHTML = images.map((s, i) => `<div class="it"><img src="${s}" alt=""><div class="ctl">
      ${i ? `<button type="button" data-i="${i}" data-a="first" title="Đặt làm ảnh đại diện">★</button>` : ''}
      <button type="button" data-i="${i}" data-a="rm" title="Xóa ảnh">✕</button></div></div>`).join('');
  }
  $('#imgs').addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    const i = +b.dataset.i;
    if (b.dataset.a === 'rm') images.splice(i, 1);
    else images.unshift(images.splice(i, 1)[0]);
    renderImgs();
  });
  $('#fileIn').addEventListener('change', (e) => { addFiles(e.target.files); e.target.value = ''; });
  const drop = $('#drop');
  ['dragover', 'dragenter'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove('over')));
  drop.addEventListener('drop', (e) => { e.preventDefault(); addFiles(e.dataTransfer.files); });

  /* ---------- Lưu ---------- */
  function collect() {
    const d = {};
    FIELDS.forEach((f) => { if (F[f]) d[f] = F[f].value.trim(); });
    d.featured = F.featured.checked; d.published = F.published.checked; d.images = images;
    d.specs = [...document.querySelectorAll('#specs .spec')].map((r) => ({ key: r.children[0].value.trim(), value: r.children[1].value.trim() })).filter((s) => s.key);
    return d;
  }
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!images.length && !confirm('Bài chưa có hình ảnh. Vẫn đăng?')) return;
    const btn = $('#saveBtn'); btn.disabled = true; const old = btn.textContent; btn.textContent = '⏳ Đang lưu…';
    try {
      if (editingId) await authApi(`${type}/${editingId}`, { method: 'PUT', body: JSON.stringify(collect()) });
      else await authApi(type, { method: 'POST', body: JSON.stringify(collect()) });
      toast(editingId ? '✅ Đã cập nhật – website hiển thị ngay' : '✅ Đã đăng bài – website hiển thị ngay');
      resetForm(); loadList();
    } catch (err) { toast('❌ ' + err.message); if (/đăng nhập/i.test(err.message)) redirectToLogin(); }
    finally { btn.disabled = false; if (btn.textContent.startsWith('⏳')) btn.textContent = old; }
  });

  /* ---------- Xem trước ---------- */
  $('#previewBtn').addEventListener('click', () => {
    const d = collect(); d.createdAt = new Date().toISOString(); d.title = d.title || '(Chưa có tên)';
    $('#pvCard').innerHTML = cardHTML(type, d).replace('reveal', 'reveal in');
    $('#preview').classList.add('open');
  });
  $('#closePv').addEventListener('click', () => $('#preview').classList.remove('open'));
  $('#pvCard').addEventListener('click', (e) => e.preventDefault());

  /* Đồng bộ khi có admin khác thay đổi */
  onLiveChange((d) => { if (d.type === type && !$('#appView').hidden) loadList(); });

  check();
})();
