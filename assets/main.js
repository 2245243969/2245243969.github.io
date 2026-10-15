const themeSwitch = document.querySelector('#themer');
const themeState = document.querySelector('#theme-state');
function updateTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  if (themeSwitch) themeSwitch.checked = dark;
  if (themeState) themeState.textContent = dark ? 'on' : 'off';
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
