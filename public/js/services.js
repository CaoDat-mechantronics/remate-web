/* Danh sách dịch vụ công khai: lọc theo nhóm, tìm kiếm, realtime */
(function () {
  const groups = (window.SITE && SITE.serviceGroups) || [];
  const box = document.getElementById('svcCatalog');
  const filters = document.getElementById('svcFilters');
  const search = document.getElementById('svcSearch');
  const count = document.getElementById('svcCount');
  if (!box || !filters || !search) return;
  let items = [], active = '';
  const groupNames = groups.map((g) => g.title);
  const params = new URLSearchParams(location.search);
  if (groupNames.includes(params.get('group'))) active = params.get('group');
  document.getElementById('svcLive').innerHTML = liveBadge();

  const attributesText = (item) => (item.specs || []).map((s) => `${s.key} ${s.value}`).join(' ');
  const matches = (item, term) => !term || [item.title, item.category, item.summary, item.content, attributesText(item)]
    .join(' ').toLocaleLowerCase('vi-VN').includes(term);

  function render() {
    const keyword = search.value.trim().toLocaleLowerCase('vi-VN');
    const found = items.filter((item) => (!active || item.category === active) && matches(item, keyword));
    count.textContent = `${found.length} dịch vụ`;
    filters.innerHTML = [{title:'',label:`Tất cả (${items.length})`}, ...groups.map((g) =>
      ({title:g.title, label:`${g.title} (${items.filter((x) => x.category === g.title).length})`}))]
      .map((g) => `<button class="rm-service-filter" type="button" aria-pressed="${g.title === active}" data-group="${esc(g.title)}">${esc(g.label)}</button>`).join('');
    if (!found.length) {
      box.innerHTML = `<div class="empty">${items.length ? 'Không có dịch vụ phù hợp với bộ lọc hoặc từ khóa.' : 'Danh sách dịch vụ đang được cập nhật. Vui lòng quay lại sau.'}</div>`;
      return;
    }
    const sortedGroups = groups.filter((g) => found.some((x) => x.category === g.title));
    box.innerHTML = sortedGroups.map((g) => {
      const groupItems = found.filter((x) => x.category === g.title);
      const ordered = [...groupItems.filter((x) => x.featured), ...groupItems.filter((x) => !x.featured)];
      return `<section class="rm-service-group" id="nhom-${esc(g.id)}">
        <div class="rm-service-group-head"><span class="rm-service-group-icon">${ic(g.icon)}</span>
          <div><h3>${esc(g.title)}</h3><p>${esc(g.description || '')}</p></div>
          <span class="rm-service-group-count">${groupItems.length} dịch vụ</span></div>
        <div class="grid">${ordered.map((x) => cardHTML('services', x)).join('')}</div>
      </section>`;
    }).join('');
    reveal();
  }
  filters.addEventListener('click', (event) => {
    const btn = event.target.closest('button[data-group]');
    if (!btn) return;
    active = btn.dataset.group;
    render();
  });
  search.addEventListener('input', render);
  async function load() {
    try {
      items = await api('services');
      items = items.filter((x) => groupNames.includes(x.category));
      render();
    } catch (e) {
      box.innerHTML = '<div class="empty">Không thể tải danh sách dịch vụ. Vui lòng thử lại sau.</div>';
      count.textContent = 'Tạm thời không khả dụng';
    }
  }
  onLiveChange((data) => { if (data.type === 'services') load(); });
  load();
})();
