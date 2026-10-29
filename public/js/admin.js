/* Trang quản trị nội dung: cần phiên đăng nhập hợp lệ từ login.html. */
(function () {
  const $ = (s) => document.querySelector(s);
  const form = $('#postForm');
  const F = form.elements;
  let token = sessionStorage.getItem('remate_token') || '';
  let type = 'products', editingId = null, images = [], items = [];
  const serviceGroups = (window.SITE && SITE.serviceGroups) || [];
  const serviceGroup = $('#serviceGroup');
  serviceGroup.innerHTML = '<option value="">-- Chọn nhóm dịch vụ --</option>' + serviceGroups.map((g) => `<option value="${esc(g.title)}">${esc(g.title)}</option>`).join('');

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
    if (t === 'album' || t === 'expertise-images' || t === 'service-covers') {
      type = t;
      document.querySelectorAll('.tab').forEach((x) => x.classList.toggle('active', x.dataset.type === t));
      document.querySelector('.a-grid').hidden = true;
      document.getElementById('albumPanel').hidden = t !== 'album';
      document.getElementById('expertisePanel').hidden = t !== 'expertise-images';
      document.getElementById('serviceCoversPanel').hidden = t !== 'service-covers';
      document.dispatchEvent(new CustomEvent(({album:'remate:album-open', 'expertise-images':'remate:expertise-open', 'service-covers':'remate:service-covers-open'})[t]));
      return;
    }
    document.querySelector('.a-grid').hidden = false;
    document.getElementById('albumPanel').hidden = true;
    document.getElementById('expertisePanel').hidden = true;
    document.getElementById('serviceCoversPanel').hidden = true;
    type = t;
    document.body.classList.toggle('partner-mode', t === 'partners');
    document.body.classList.toggle('service-mode', t === 'services');
    document.querySelectorAll('.tab').forEach((x) => x.classList.toggle('active', x.dataset.type === t));
    document.querySelectorAll('.only-p').forEach((el) => (el.style.display = t === 'products' ? '' : 'none'));
    document.querySelectorAll('.only-j').forEach((el) => (el.style.display = t === 'projects' ? '' : 'none'));
    document.querySelectorAll('.only-service').forEach((el) => (el.style.display = t === 'services' ? '' : 'none'));
    serviceGroup.disabled = t !== 'services';
    serviceGroup.required = t === 'services';
    F.category.disabled = t === 'services';
    document.querySelectorAll('.only-partner').forEach((el) => (el.style.display = t === 'partners' ? '' : 'none'));
    document.querySelectorAll('.only-post').forEach((el) => (el.style.display = t !== 'partners' ? '' : 'none'));
    $('#listTitle').textContent = ({products:'Danh sách sản phẩm', projects:'Danh sách dự án', partners:'Danh sách đối tác', services:'Danh sách dịch vụ'})[t];
    $('#mainTitleLabel').textContent = t === 'partners' ? 'Tên doanh nghiệp / đối tác' : t === 'services' ? 'Tên dịch vụ' : 'Tên';
    $('#categoryLabel').textContent = t === 'partners' ? 'Lĩnh vực hợp tác' : 'Danh mục / Lĩnh vực';
    F.category.closest('label').style.display = t === 'services' ? 'none' : '';
    $('#summaryLabel').textContent = t === 'partners' ? 'Giới thiệu ngắn về đối tác (hiển thị công khai)' : t === 'services' ? 'Mô tả ngắn dịch vụ (hiển thị trên danh sách)' : 'Mô tả ngắn (hiển thị trên thẻ)';
    $('#contentLabel').textContent = t === 'services' ? 'Mô tả chi tiết dịch vụ' : 'Nội dung chi tiết';
    $('#mediaTitle').textContent = t === 'partners' ? 'Logo đối tác' : 'Hình ảnh';
    $('#mediaHint').textContent = t === 'partners' ? '(1 logo, PNG/JPG/WebP; nên dùng ảnh vuông hoặc ngang, nền trong suốt)' : '(ảnh đầu tiên là ảnh đại diện – tối đa 12 ảnh)';
    $('#featuredLabel').textContent = t === 'partners' ? 'Ưu tiên giới thiệu trên trang chủ' : t === 'services' ? 'Nổi bật (ưu tiên trong nhóm dịch vụ)' : 'Nổi bật (ưu tiên trang chủ)';
    $('#fileIn').multiple = t !== 'partners';
    F.title.placeholder = t === 'partners' ? 'VD: Công ty TNHH ABC' : t === 'projects' ? 'VD: Lắp đặt hệ thống sản xuất' : t === 'services' ? 'VD: Bảo trì định kỳ hệ thống khí nén' : 'VD: Máy nén khí trục vít 37kW đã qua sử dụng';
    F.summary.placeholder = t === 'partners' ? 'Giới thiệu ngắn về năng lực và mối quan hệ hợp tác…' : t === 'services' ? 'Giới thiệu dịch vụ trong 1–2 câu…' : '1–2 câu tóm tắt';
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
          <a class="btn btn-sm btn-light" target="_blank" rel="noopener" href="${type === 'partners' ? 'doi-tac.html#danh-sach-doi-tac' : `chi-tiet.html?type=${type}&id=${encodeURIComponent(x.slug)}`}">↗ Xem</a>
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
  const FIELDS = ['title', 'category', 'summary', 'content', 'website', 'price', 'condition', 'quantity', 'origin', 'client', 'location', 'time', 'scope', 'result'];
  function resetForm() {
    editingId = null; images = []; form.reset(); F.published.checked = true;
    $('#specs').innerHTML = ''; $('#serviceSpecs').innerHTML = '';
    serviceGroup.value = '';
    if (type === 'products') { addSpec(); addSpec(); }
    if (type === 'services') { addSpec('', '', '#serviceSpecs'); }
    renderImgs(); renderList();
    $('#formTitle').textContent = ({products:'Đăng sản phẩm mới', projects:'Đăng dự án mới', partners:'Thêm đối tác mới', services:'Thêm dịch vụ mới'})[type];
    $('#saveBtn').textContent = type === 'partners' ? '💾 Thêm đối tác' : type === 'services' ? '💾 Đăng dịch vụ' : '💾 Đăng bài';
  }
  function fillForm(x) {
    resetForm(); editingId = x.id;
    FIELDS.forEach((f) => { if (F[f]) F[f].value = x[f] || ''; });
    if (type === 'services') serviceGroup.value = x.category || '';
    F.featured.checked = !!x.featured; F.published.checked = x.published !== false;
    images = [...(x.images || [])]; renderImgs();
    $('#specs').innerHTML = ''; $('#serviceSpecs').innerHTML = '';
    (x.specs || []).forEach((s) => addSpec(s.key, s.value, type === 'services' ? '#serviceSpecs' : '#specs'));
    if (type === 'products' && !(x.specs || []).length) addSpec();
    if (type === 'services' && !(x.specs || []).length) addSpec('', '', '#serviceSpecs');
    $('#formTitle').textContent = 'Sửa: ' + x.title; $('#saveBtn').textContent = '💾 Lưu thay đổi';
    renderList(); form.scrollIntoView({ behavior: 'smooth' });
  }
  $('#resetBtn').addEventListener('click', resetForm);

  function addSpec(k = '', v = '', target = '#specs') {
    if ($(target).querySelectorAll('.spec').length >= 30) { toast('Tối đa 30 thuộc tính'); return; }
    const d = document.createElement('div'); d.className = 'spec';
    d.innerHTML = `<input placeholder="Thông số (VD: Công suất)" value="${esc(k)}"><input placeholder="Giá trị (VD: 37 kW)" value="${esc(v)}"><button type="button" title="Xóa">✕</button>`;
    d.querySelector('button').onclick = () => d.remove();
    $(target).appendChild(d);
  }
  $('#addSpec').addEventListener('click', () => addSpec());
  $('#addServiceSpec').addEventListener('click', () => addSpec('', '', '#serviceSpecs'));

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
      const limit = type === 'partners' ? 1 : 12;
      if (images.length >= limit) { toast(type === 'partners' ? 'Mỗi đối tác sử dụng 1 logo. Xóa logo cũ trước khi chọn logo mới.' : 'Tối đa 12 ảnh'); break; }
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
    if (type === 'services') d.category = serviceGroup.value;
    d.specs = [...document.querySelectorAll(type === 'services' ? '#serviceSpecs .spec' : '#specs .spec')].map((r) => ({ key: r.children[0].value.trim(), value: r.children[1].value.trim() })).filter((s) => s.key).slice(0, 30);
    return d;
  }
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!images.length && !confirm(type === 'partners' ? 'Đối tác chưa có logo. Vẫn lưu? (Trang công khai sẽ hiển thị chữ cái đại diện)' : 'Bài chưa có hình ảnh. Vẫn đăng?')) return;
    const btn = $('#saveBtn'); btn.disabled = true; const old = btn.textContent; btn.textContent = '⏳ Đang lưu…';
    try {
      if (editingId) await authApi(`${type}/${editingId}`, { method: 'PUT', body: JSON.stringify(collect()) });
      else await authApi(type, { method: 'POST', body: JSON.stringify(collect()) });
      toast(editingId ? '✅ Đã cập nhật – website hiển thị ngay' : type === 'partners' ? '✅ Đã lưu đối tác – website đã đồng bộ' : '✅ Đã đăng bài – website hiển thị ngay');
      resetForm(); loadList();
    } catch (err) { toast('❌ ' + err.message); if (/đăng nhập/i.test(err.message)) redirectToLogin(); }
    finally { btn.disabled = false; if (btn.textContent.startsWith('⏳')) btn.textContent = old; }
  });

  /* ---------- Xem trước ---------- */
  $('#previewBtn').addEventListener('click', () => {
    const d = collect(); d.createdAt = new Date().toISOString(); d.title = d.title || '(Chưa có tên)';
    $('#pvCard').innerHTML = type === 'partners'
      ? `<article class="partner-profile"><div class="partner-profile-logo">${d.images[0] ? `<img src="${esc(d.images[0])}" alt="">` : `<span class="partner-letter">${esc(d.title.slice(0,1).toUpperCase())}</span>`}</div>
          <div class="partner-profile-info"><span class="partner-profile-sector">${esc(d.category || 'Đối tác')}</span><h3>${esc(d.title)}</h3><p>${esc(d.summary)}</p>${/^https?:\/\//i.test(d.website || '') ? `<span class="partner-preview-url">Website đối tác ↗</span>` : ''}</div></article>`
      : cardHTML(type, d).replace('reveal', 'reveal in');
    $('#preview').classList.add('open');
  });
  $('#closePv').addEventListener('click', () => $('#preview').classList.remove('open'));
  $('#pvCard').addEventListener('click', (e) => e.preventDefault());

  /* Đồng bộ khi có admin khác thay đổi */
  onLiveChange((d) => { if (type !== 'album' && d.type === type && !$('#appView').hidden) loadList(); });

  check();
})();
