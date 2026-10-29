/* Giới thiệu công ty và carousel album hoạt động: cuộn ngang, vuốt, mũi tên và tự chạy. */
(() => {
  const S = window.SITE;
  const fields = document.getElementById('aboutExpertise');
  function renderExpertise(images = []) {
    fields.innerHTML = S.services.map((s, i) => {
      const custom = images.find(x => x.index === i && x.src);
      const symbol = custom
        ? `<img class="rm-expertise-custom-image" src="${esc(custom.src)}" alt="Biểu tượng ${esc(s.title)}" loading="lazy">`
        : ic(s.icon);
      return `<article class="rm-expertise-card reveal"><span class="rm-expertise-number">0${i + 1}</span>
        <div class="rm-expertise-icon ${custom ? 'has-custom-image' : ''}">${symbol}</div><h3>${esc(s.title)}</h3>
        <span class="rm-expertise-underline"></span></article>`;
    }).join('');
    reveal();
  }
  async function loadExpertise() {
    try { renderExpertise(await api('expertise-images')); }
    catch { renderExpertise(); }
  }
  renderExpertise();
  loadExpertise();
  onLiveChange(d => { if (d.type === 'expertise-images') loadExpertise(); });

  const viewport = document.getElementById('albumViewport');
  const track = document.getElementById('albumTrack');
  const loading = document.getElementById('albumLoading');
  const controls = document.getElementById('albumControls');
  const count = document.getElementById('albumPosition');
  const dots = document.getElementById('albumDots');
  let images = [], position = 0, timer = null;
  const shouldAnimate = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function cardAt(i) { return track.children[i]; }
  function indexFromScroll() {
    if (!images.length) return 0;
    const left = viewport.scrollLeft;
    let closest = 0, distance = Infinity;
    for (let i = 0; i < images.length; i++) {
      const d = Math.abs(cardAt(i).offsetLeft - track.offsetLeft - left);
      if (d < distance) { distance = d; closest = i; }
    }
    return closest;
  }
  function indicators() {
    count.textContent = images.length ? `${String(position + 1).padStart(2, '0')} / ${String(images.length).padStart(2, '0')} ảnh` : '';
    dots.querySelectorAll('button').forEach((d, i) => d.setAttribute('aria-current', i === position ? 'true' : 'false'));
  }
  function go(i, smooth = true) {
    if (!images.length) return;
    position = (i + images.length) % images.length;
    const target = cardAt(position);
    track.style.paddingRight = `${Math.max(0, viewport.clientWidth - cardAt(0).clientWidth)}px`;
    viewport.scrollTo({ left: target.offsetLeft - track.offsetLeft, behavior: smooth && shouldAnimate ? 'smooth' : 'auto' });
    indicators();
  }
  const stop = () => { clearInterval(timer); timer = null; };
  const play = () => {
    stop();
    if (images.length < 2 || !shouldAnimate || document.hidden) return;
    timer = setInterval(() => go(position + 1), 4600);
  };
  document.getElementById('albumPrev').addEventListener('click', () => { go(position - 1); play(); });
  document.getElementById('albumNext').addEventListener('click', () => { go(position + 1); play(); });
  viewport.addEventListener('scroll', () => {
    cancelAnimationFrame(viewport._scrollRaf);
    viewport._scrollRaf = requestAnimationFrame(() => { position = indexFromScroll(); indicators(); });
  }, {passive:true});
  viewport.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') { e.preventDefault(); go(position + 1); play(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); go(position - 1); play(); }
  });
  viewport.addEventListener('mouseenter', stop);
  viewport.addEventListener('mouseleave', play);
  viewport.addEventListener('focusin', stop);
  viewport.addEventListener('focusout', play);
  document.addEventListener('visibilitychange', () => document.hidden ? stop() : play());

  async function loadAlbum() {
    try {
      const list = await api('album');
      const oldId = images[position] && images[position].id;
      images = Array.isArray(list) ? list : [];
      if (!images.length) {
        viewport.hidden = controls.hidden = true;
        loading.hidden = false;
        loading.innerHTML = '<span class="rm-album-empty-icon">▧</span><h3>Album hình ảnh đang được cập nhật</h3><p>ReMate sẽ giới thiệu những hình ảnh hoạt động mới tại đây.</p>';
        count.textContent = ''; dots.innerHTML = '';
        stop();
        return;
      }
      loading.hidden = true;
      viewport.hidden = false;
      controls.hidden = images.length < 2;
      track.innerHTML = images.map((x, i) => `<article class="rm-album-slide"><button type="button" class="rm-album-image" data-i="${i}" aria-label="Phóng to ảnh ${i + 1}"><img src="${esc(x.src)}" alt="${esc(x.caption || 'Hình ảnh hoạt động ReMate ' + (i + 1))}" loading="${i < 3 ? 'eager' : 'lazy'}"></button>${x.caption ? `<p class="rm-album-caption">${esc(x.caption)}</p>` : ''}</article>`).join('');
      dots.innerHTML = images.map((_,i) => `<button type="button" data-i="${i}" aria-label="Đến ảnh ${i+1}" aria-current="false"></button>`).join('');
      track.querySelectorAll('.rm-album-image').forEach((b) => b.addEventListener('click', () => lightbox(images[Number(b.dataset.i)].src)));
      dots.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {go(Number(b.dataset.i)); play();}));
      const currentIndex = images.findIndex(x => x.id === oldId);
      position = currentIndex >= 0 ? currentIndex : 0;
      requestAnimationFrame(() => go(position, false));
      play();
    } catch (e) {
      loading.hidden = false; viewport.hidden = true; controls.hidden = true; stop();
      loading.textContent = 'Không tải được album. Vui lòng thử tải lại trang.';
    }
  }
  onLiveChange(d => { if (d.type === 'album') loadAlbum(); });
  window.addEventListener('resize', () => { if(images.length) go(position, false); });
  loadAlbum();
})();
