/* Tab Album ảnh hoạt động: tải ảnh riêng, sửa chú thích, chọn nhiều ảnh và xóa. */
(() => {
  const $ = (id) => document.getElementById(id);
  const panel = $('albumPanel');
  const grid = $('albumAdminGrid');
  const input = $('albumFileInput');
  const selectAll = $('albumSelectAll');
  const deleteButton = $('albumDeleteSelected');
  const selected = new Set();
  let photos = [], busy = false;

  function token() { return sessionStorage.getItem('remate_token') || ''; }
  async function call(path, options = {}) {
    return api(path, { ...options, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() } });
  }
  function setStatus(msg) { $('albumStatus').textContent = msg; }
  function selectionUpdate() {
    $('albumSelectedCount').textContent = selected.size ? `(${selected.size})` : '';
    deleteButton.disabled = busy || !selected.size;
    selectAll.checked = photos.length > 0 && selected.size === photos.length;
    selectAll.indeterminate = selected.size > 0 && selected.size < photos.length;
  }
  function render() {
    $('albumCount').textContent = String(photos.length);
    grid.innerHTML = photos.length ? photos.map((p, i) => `<article class="album-admin-card">
      <label class="album-card-check"><input type="checkbox" data-select="${esc(p.id)}" ${selected.has(p.id) ? 'checked' : ''} aria-label="Chọn ảnh ${i+1}"> Chọn ảnh</label>
      <img src="${esc(p.src)}" alt="${esc(p.caption || 'Hình ảnh hoạt động ' + (i+1))}" loading="lazy">
      <div class="album-card-edit"><label for="album-caption-${esc(p.id)}">Chú thích ảnh</label>
        <input id="album-caption-${esc(p.id)}" value="${esc(p.caption || '')}" maxlength="250" placeholder="VD: Kiểm tra thiết bị tại nhà máy">
        <div class="album-card-actions"><button type="button" class="btn btn-outline btn-sm" data-save="${esc(p.id)}">Lưu chú thích</button>
        <button type="button" class="btn btn-danger btn-sm" data-delete="${esc(p.id)}">Xóa</button></div></div></article>`).join('')
      : '<div class="empty">Chưa có ảnh trong album. Chọn ảnh ở khu vực phía trên để thêm mới.</div>';
    selectionUpdate();
  }
  async function load() {
    try {
      photos = await call('album');
      const ids = new Set(photos.map(p => p.id));
      for (const id of selected) if (!ids.has(id)) selected.delete(id);
      render();
    } catch(e) { grid.innerHTML = `<div class="empty">${esc(e.message || 'Không tải được album')}</div>`; }
  }
  function readDataURL(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Không đọc được file ảnh'));
      reader.readAsDataURL(file);
    });
  }
  async function prepare(file) {
    if (!['image/png','image/jpeg','image/webp','image/gif'].includes(file.type)) throw new Error('Chỉ nhận JPG, PNG, WebP, GIF');
    if (file.type === 'image/gif') return readDataURL(file);
    const url = await readDataURL(file);
    return new Promise((resolve,reject) => {
      const image = new Image();
      image.onload = () => {
        const scale = Math.min(1, 1920 / Math.max(image.width, image.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(image.width*scale); canvas.height=Math.round(image.height*scale);
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffffff'; ctx.fillRect(0,0,canvas.width,canvas.height);
        ctx.drawImage(image,0,0,canvas.width,canvas.height);
        resolve(canvas.toDataURL('image/jpeg',0.84));
      };
      image.onerror = () => reject(new Error('Không thể xử lý ảnh'));
      image.src = url;
    });
  }
  async function upload(files) {
    if (busy || !files.length) return;
    busy = true; deleteButton.disabled = true;
    const allowed = [...files].filter(f => /^image\//.test(f.type));
    let ok = 0, failed = 0;
    for (const [index,file] of allowed.entries()) {
      setStatus(`Đang tải ảnh ${index+1}/${allowed.length}: ${file.name}`);
      try {
        const data = await prepare(file);
        if (data.length > 11.2 * 1024 * 1024) throw new Error('Ảnh lớn hơn 8 MB sau khi nén');
        await call('album', {method:'POST', body: JSON.stringify({image:data, caption:''})});
        ok++;
      } catch (e) { failed++; setStatus(`Không tải được ${file.name}: ${e.message}`); }
    }
    busy = false; setStatus(`Đã thêm ${ok} ảnh${failed ? `, có ${failed} ảnh lỗi (kiểm tra dung lượng hoặc định dạng).` : ' thành công.'}`);
    await load();
  }
  input.addEventListener('change', () => { upload(input.files); input.value = ''; });
  const drop = $('albumDrop');
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('over'));
  drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); upload(e.dataTransfer.files); });
  selectAll.addEventListener('change', () => { selected.clear(); if (selectAll.checked) photos.forEach(p => selected.add(p.id)); render(); });
  grid.addEventListener('change', e => {
    const id = e.target.dataset.select;
    if (!id) return;
    if (e.target.checked) selected.add(id); else selected.delete(id);
    selectionUpdate();
  });
  async function deleteIds(ids) {
    if (!ids.length || busy || !confirm(`Bạn chắc chắn muốn xóa ${ids.length} ảnh khỏi album? Thao tác không thể hoàn tác.`)) return;
    busy = true; selectionUpdate();
    try {
      // Backend giới hạn 500 ID mỗi yêu cầu để tránh request quá lớn, không giới hạn album.
      for (let i=0; i<ids.length; i+=500) {
        await call('album/selected', {method:'DELETE', body:JSON.stringify({ids:ids.slice(i,i+500)})});
      }
      selected.clear(); setStatus(`Đã xóa ${ids.length} ảnh khỏi album.`);
      await load();
    } catch (e) { setStatus(`Lỗi xóa ảnh: ${e.message}`); }
    finally { busy = false; selectionUpdate(); }
  }
  deleteButton.addEventListener('click', () => deleteIds([...selected]));
  grid.addEventListener('click', async (e) => {
    const button = e.target.closest('button'); if (!button || busy) return;
    if (button.dataset.delete) return deleteIds([button.dataset.delete]);
    if (button.dataset.save) {
      const id=button.dataset.save; const cap=$('album-caption-'+id).value.trim();
      button.disabled=true;
      try { await call('album/'+encodeURIComponent(id), {method:'PUT',body:JSON.stringify({caption:cap})}); setStatus('Đã cập nhật chú thích.'); await load(); }
      catch(e) { setStatus(`Không lưu được chú thích: ${e.message}`); }
      finally { button.disabled=false; }
    }
  });
  document.addEventListener('remate:album-open', load);
  onLiveChange(d => { if(d.type === 'album' && !panel.hidden && !busy) load(); });
})();
