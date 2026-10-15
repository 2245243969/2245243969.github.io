// Keep double-clicked local previews working while published Home links use /.
if (location.protocol === 'file:') {
  for (const link of document.querySelectorAll('[data-home-link]')) {
    link.href = new URL('index.html', link.href).href;
  }
}
const themeSwitch = document.querySelector('#themer');
const themeState = document.querySelector('#theme-state');
function updateTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  if (themeSwitch) themeSwitch.checked = dark;
  if (themeState) themeState.textContent = dark ? '开 · On' : '关 · Off';
}
updateTheme(document.documentElement.dataset.theme === 'dark');
themeSwitch?.addEventListener('change', () => {
  updateTheme(themeSwitch.checked);
  try { localStorage.setItem('personal-site-theme', themeSwitch.checked ? 'dark' : 'light'); } catch (_) {}
});
const menuButton = document.querySelector('#menu-button');
const menu = document.querySelector('#navigation-list');
menuButton?.addEventListener('click', () => {
  const expanded = menuButton.getAttribute('aria-expanded') !== 'true';
  menuButton.setAttribute('aria-expanded', String(expanded));
  menu.classList.toggle('open', expanded);
  menuButton.querySelector('[data-menu-state]').textContent = expanded ? '−' : '+';
});
