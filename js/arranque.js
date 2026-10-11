// Marca la página como "con JavaScript" antes de que se pinte.
// El CSS usa esta clase para decidir qué mostrar (selector, flechas del carrusel);
// si el script no carga, la página se queda en su versión completa sin JS.
document.documentElement.classList.add('con-js');

// Si la persona ya había elegido el modo nocturno, se aplica desde aquí
// para que la página no parpadee en claro antes de oscurecerse.
// (try/catch: algunos navegadores bloquean localStorage en modo privado.)
try {
  if (localStorage.getItem('delio-tema') === 'oscuro') {
    document.documentElement.dataset.tema = 'oscuro';
  }
} catch (error) {
  // sin memoria guardada, se queda en modo de día
}
