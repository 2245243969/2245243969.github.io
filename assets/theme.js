// Run before rendering so the saved theme does not flash.
document.documentElement.classList.add('js');
try {
  if (localStorage.getItem('personal-site-theme') === 'dark') {
    document.documentElement.dataset.theme = 'dark';
  }
} catch (_) { /* Browsing remains available if storage is disabled. */ }
