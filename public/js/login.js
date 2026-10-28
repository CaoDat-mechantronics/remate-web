/* Chỉ xử lý đăng nhập và hiển thị/ẩn mật khẩu trên login.html. */
(function () {
  'use strict';
  const form = document.getElementById('loginForm');
  const username = document.getElementById('username');
  const password = document.getElementById('password');
  const eye = document.getElementById('togglePassword');
  const error = document.getElementById('loginErr');
  const submit = document.getElementById('loginBtn');
  const tokenKey = 'remate_token';

  eye.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    eye.setAttribute('aria-pressed', String(visible));
    eye.setAttribute('aria-label', visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
    eye.title = visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu';
    eye.querySelector('.eye-open').hidden = visible;
    eye.querySelector('.eye-closed').hidden = !visible;
    password.focus({ preventScroll: true });
  });

  // Nếu phiên đang còn hiệu lực, mở thẳng khu vực quản trị.
  (async () => {
    const token = sessionStorage.getItem(tokenKey);
    if (!token) return;
    try {
      const res = await fetch('/api/me', {
        headers: { Authorization: 'Bearer ' + token },
        cache: 'no-store'
      });
      if (res.ok) { window.location.replace('admin.html'); return; }
    } catch (_) { /* Không kết nối được: cho phép thử đăng nhập lại. */ }
    if (sessionStorage.getItem(tokenKey) === token) sessionStorage.removeItem(tokenKey);
  })();

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    error.textContent = '';
    submit.disabled = true;
    submit.textContent = 'Đang đăng nhập…';
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.value.trim(), password: password.value }),
        cache: 'no-store'
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.token) throw new Error(data.error || 'Không thể đăng nhập.');
      sessionStorage.setItem(tokenKey, data.token);
      password.value = '';
      window.location.replace('admin.html');
    } catch (err) {
      error.textContent = err.message || 'Không thể kết nối máy chủ.';
      submit.disabled = false;
      submit.textContent = 'Đăng nhập';
      password.focus();
    }
  });
})();
