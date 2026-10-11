// tema.js — botón de modo nocturno
//
// El modo es un atributo en <html>: data-tema="oscuro". El CSS (css/base.css)
// cambia los colores según ese atributo; aquí solo se pone, se quita y se recuerda.

(function () {
  'use strict';

  const CLAVE = 'delio-tema';
  const raiz = document.documentElement;
  const boton = document.querySelector('[data-tema-boton]');
  if (!boton) return;

  const colorDelNavegador = document.querySelector('meta[name="theme-color"]');

  // El botón siempre dice a qué modo cambia, no en cuál está.
  function pintar() {
    const oscuro = raiz.dataset.tema === 'oscuro';
    boton.textContent = oscuro ? 'Día' : 'Noche';
    boton.setAttribute('aria-label', oscuro ? 'Cambiar a modo de día' : 'Cambiar a modo nocturno');
    // La barra del navegador en el celular toma el mismo color que el fondo.
    if (colorDelNavegador) colorDelNavegador.content = getComputedStyle(raiz).getPropertyValue('--fondo').trim();
  }

  boton.addEventListener('click', () => {
    const nuevo = raiz.dataset.tema === 'oscuro' ? 'claro' : 'oscuro';
    raiz.dataset.tema = nuevo;
    // Se guarda en el navegador de la persona para la próxima visita.
    try {
      localStorage.setItem(CLAVE, nuevo);
    } catch (error) {
      // si no se puede guardar, el cambio vale solo para esta visita
    }
    pintar();
    // Aviso para lo que se dibuja con JavaScript (la onda de la portada).
    document.dispatchEvent(new CustomEvent('tema-cambiado'));
  });

  pintar();
})();
