document.querySelectorAll('[data-tex]').forEach((element) => {
  if (!window.katex) return;
  try {
    katex.render(element.dataset.tex, element, {
      displayMode: element.classList.contains('math-display'),
      throwOnError: true,
      strict: 'warn',
      trust: false,
      output: 'htmlAndMathml'
    });
    element.dataset.mathRendered = 'true';
  } catch (error) {
    element.dataset.mathError = 'true';
    console.error('Math rendering failed:', error.message);
  }
});
