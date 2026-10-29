/* Quản lý 3 ảnh lớn trên trang dich-vu.html, không ảnh hưởng ảnh bài đăng. */
(() => {
  const grid = document.getElementById('serviceCoversGrid');
  const status = document.getElementById('serviceCoversStatus');
  const groups = (window.SITE && SITE.serviceGroups) || [];
  const defaults = ['img/p1.jpg', 'img/p2.jpg'];
  let current = [], busy = false;

  const call = (path, opt = {}) => api(path, {
    ...opt,
    headers: {'Content-Type': 'application/json',
      Authorization: 'Bearer ' + (sessionStorage.getItem('remate_token') || ''),
      ...(opt.headers || {})}
  });
  const report = msg => { status.textContent = msg; };

  function render() {
    grid.innerHTML = groups.slice(0, 3).map((group, index) => {
      const found = current.find(x => x.index === index);
      const uploaded = found && found.src;
      const source = uploaded || defaults[index];
      const preview = source
        ? `<img src="${esc(source)}" alt="Ảnh nhóm dịch vụ ${index + 1}">`
        : `<div class="service-cover-default">⚡<small>Minh họa năng lượng mặc định</small></div>`;
      return `<article class="service-covers-admin-card" data-index="${index}">
        <span class="expertise-admin-index">NHÓM 0${index + 1}</span>
        <div class="service-covers-admin-image">${preview}</div>
        <h3>${esc(group.title)}</h3>
        <small>${uploaded ? 'Ảnh tùy chỉnh đang được sử dụng' : 'Đang sử dụng ảnh / minh họa mặc định'}</small>
        <div class="expertise-admin-actions">
          <label class="btn btn-primary btn-sm expertise-admin-upload ${busy ? 'is-busy' : ''}">
            ${uploaded ? 'Thay ảnh' : 'Tải ảnh mới'}
            <input type="file" data-upload="${index}" accept="image/jpeg,image/png,image/webp,image/gif" ${busy ? 'disabled' : ''} aria-label="Chọn ảnh nhóm dịch vụ ${index + 1}">
          </label>
          <button type="button" class="btn btn-outline btn-sm" data-reset="${index}" ${!uploaded || busy ? 'disabled' : ''}>Mặc định</button>
        </div>
      </article>`;
    }).join('');
  }

  async function load() {
    try { current = await call('service-covers'); render(); }
    catch (err) { report('Không tải được ảnh nhóm dịch vụ: ' + err.message); }
  }

  function compress(file) {
    return new Promise((resolve, reject) => {
      if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type))
        return reject(new Error('Chỉ hỗ trợ JPG, PNG, WebP, GIF'));
      if (file.size > 24 * 1024 * 1024) return reject(new Error('File gốc tối đa 24 MB'));
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('Không đọc được ảnh'));
      reader.onload = () => {
        const img = new Image();
        img.onerror = () => reject(new Error('Ảnh không hợp lệ'));
        img.onload = () => {
          const ratio = Math.min(1, 1800 / Math.max(img.width, img.height));
          const c = document.createElement('canvas');
          c.width = Math.max(1, Math.round(img.width * ratio));
          c.height = Math.max(1, Math.round(img.height * ratio));
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          let data = c.toDataURL('image/webp', .86);
          if (!data.startsWith('data:image/webp;')) data = c.toDataURL('image/jpeg', .82);
          if (data.length > 8 * 1024 * 1024) return reject(new Error('Ảnh sau nén vượt quá 6 MB'));
          resolve(data);
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    });
  }

  grid.addEventListener('change', async e => {
    const input = e.target.closest('input[data-upload]');
    if (!input || !input.files?.[0] || busy) return;
    const index = Number(input.dataset.upload);
    const file = input.files[0];
    busy = true; render(); report(`Đang xử lý ảnh cho nhóm ${index + 1}…`);
    try {
      const image = await compress(file);
      await call('service-covers/' + index, {method:'PUT', body:JSON.stringify({image})});
      await load(); report(`Đã cập nhật ảnh nhóm ${index + 1}. Trang Dịch vụ sẽ tự làm mới.`);
    } catch(err) { report('Không lưu được ảnh: ' + err.message); }
    finally { busy = false; render(); }
  });
  grid.addEventListener('click', async e => {
    const button = e.target.closest('button[data-reset]');
    if (!button || busy) return;
    const index = Number(button.dataset.reset);
    if (!confirm(`Khôi phục ảnh mặc định cho nhóm dịch vụ ${index + 1}?`)) return;
    busy = true; render(); report(`Đang khôi phục nhóm ${index + 1}…`);
    try {
      await call('service-covers/' + index, {method:'DELETE'});
      await load(); report(`Đã khôi phục ảnh mặc định cho nhóm ${index + 1}.`);
    } catch(err) { report('Không khôi phục được: ' + err.message); }
    finally { busy = false; render(); }
  });
  document.addEventListener('remate:service-covers-open', load);
  onLiveChange(e => {
    if (e.type === 'service-covers' && !document.getElementById('serviceCoversPanel').hidden) load();
  });
})();
