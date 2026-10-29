/* Tab quản lý ảnh đại diện 4 lĩnh vực hoạt động ở gioi-thieu.html. */
(() => {
  const $ = id => document.getElementById(id);
  const grid = $('expertiseAdminGrid');
  const groups = (window.SITE && SITE.services) || [];
  let stored = [], busy = false;

  function status(message) { $('expertiseStatus').textContent = message; }
  function call(path, options = {}) {
    return api(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + (sessionStorage.getItem('remate_token') || ''),
        ...(options.headers || {})
      }
    });
  }
  function render() {
    grid.innerHTML = groups.slice(0, 4).map((group, index) => {
      const item = stored.find(x => x.index === index);
      const uploaded = item && item.src;
      return `<article class="expertise-admin-card" data-index="${index}">
        <span class="expertise-admin-index">LĨNH VỰC 0${index + 1}</span>
        <div class="expertise-admin-image">${uploaded
          ? `<img src="${esc(item.src)}" alt="Hình đại diện ${esc(group.title)}">`
          : ic(group.icon)}</div>
        <h3>${esc(group.title)}</h3>
        <small>${uploaded ? 'Đang sử dụng ảnh tùy chỉnh' : 'Đang sử dụng biểu tượng mặc định'}</small>
        <div class="expertise-admin-actions">
          <label class="btn btn-primary btn-sm expertise-admin-upload ${busy ? 'is-busy' : ''}">
            ${uploaded ? 'Thay ảnh' : 'Tải ảnh lên'}
            <input type="file" data-upload="${index}" accept="image/jpeg,image/png,image/webp,image/gif" ${busy ? 'disabled' : ''} aria-label="Tải ảnh lĩnh vực ${index + 1}">
          </label>
          <button type="button" class="btn btn-outline btn-sm" data-reset="${index}" ${!uploaded || busy ? 'disabled' : ''}>Mặc định</button>
        </div>
      </article>`;
    }).join('');
  }
  async function load() {
    try {
      stored = await call('expertise-images');
      render();
    } catch(e) { grid.innerHTML = `<div class="empty">${esc(e.message || 'Không tải được hình ảnh lĩnh vực')}</div>`; }
  }
  function readFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Không đọc được file ảnh'));
      reader.readAsDataURL(file);
    });
  }
  async function compress(file) {
    const accepted = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (!accepted.includes(file.type)) throw new Error('Chỉ chấp nhận JPG, PNG, WebP hoặc GIF');
    if (file.size > 20 * 1024 * 1024) throw new Error('Ảnh gốc quá lớn (tối đa 20 MB)');
    const raw = await readFile(file);
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const dimension = 900;
        const factor = Math.min(1, dimension / Math.max(img.width, img.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(img.width * factor));
        canvas.height = Math.max(1, Math.round(img.height * factor));
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
        let data = canvas.toDataURL('image/webp', 0.86); // Giữ nền trong suốt của logo PNG
        if (!data.startsWith('data:image/webp;')) data = canvas.toDataURL('image/png');
        if (data.length > 7 * 1024 * 1024) return reject(new Error('Ảnh quá lớn sau khi nén (giới hạn 5 MB)'));
        resolve(data);
      };
      img.onerror = () => reject(new Error('Không thể xử lý ảnh'));
      img.src = raw;
    });
  }
  grid.addEventListener('change', async e => {
    const input = e.target.closest('input[data-upload]');
    if (!input || !input.files || !input.files[0] || busy) return;
    const index = Number(input.dataset.upload);
    const file = input.files[0];
    busy = true; render(); status(`Đang xử lý ảnh lĩnh vực ${index + 1}…`);
    try {
      const image = await compress(file);
      await call('expertise-images/' + index, {method:'PUT', body:JSON.stringify({image})});
      status(`Đã cập nhật ảnh lĩnh vực ${index + 1}. Trang Giới thiệu được cập nhật tự động.`);
      await load();
    } catch(err) { status('Không tải được ảnh: ' + err.message); }
    finally { busy = false; render(); }
  });
  grid.addEventListener('click', async e => {
    const reset = e.target.closest('button[data-reset]');
    if (!reset || busy) return;
    const index = Number(reset.dataset.reset);
    if (!confirm(`Khôi phục biểu tượng mặc định cho lĩnh vực ${index + 1}?`)) return;
    busy = true; render();
    try {
      await call('expertise-images/' + index, {method:'DELETE'});
      status(`Đã khôi phục biểu tượng mặc định cho lĩnh vực ${index + 1}.`);
      await load();
    } catch(err) { status('Không khôi phục được: ' + err.message); }
    finally { busy = false; render(); }
  });
  document.addEventListener('remate:expertise-open', load);
  onLiveChange(e => { if (e.type === 'expertise-images' && !grid.closest('[hidden]')) load(); });
})();
