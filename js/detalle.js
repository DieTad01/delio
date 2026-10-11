// detalle.js — sección "Qué incluye"
//
// En el HTML está una lista por servicio. Aquí se deja visible una sola,
// la que diga el selector o el mosaico en el que se hizo clic.

(function () {
  'use strict';

  const filtro = document.querySelector('[data-detalle-filtro]');
  const paneles = Array.from(document.querySelectorAll('[data-detalle-panel]'));
  if (!filtro || !paneles.length) return;

  function mostrar(clave) {
    const existe = paneles.some((panel) => panel.dataset.detallePanel === clave);
    if (!existe) clave = paneles[0].dataset.detallePanel;

    paneles.forEach((panel) => {
      panel.hidden = panel.dataset.detallePanel !== clave;
    });
    filtro.value = clave;
  }

  filtro.addEventListener('change', () => mostrar(filtro.value));

  // Los mosaicos de servicios traen data-detalle="clave". El panel se muestra
  // antes de que el navegador salte al ancla, así el salto llega a algo visible.
  document.addEventListener('click', (evento) => {
    const enlace = evento.target.closest('[data-detalle]');
    if (enlace) mostrar(enlace.dataset.detalle);
  });

  // Si alguien llega con un enlace directo (…/#incluye-wifi), abre ese panel.
  const desdeEnlace = /^#incluye-(.+)$/.exec(window.location.hash);
  mostrar(desdeEnlace ? desdeEnlace[1] : filtro.value);
})();
