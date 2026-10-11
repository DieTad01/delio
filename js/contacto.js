// contacto.js — formulario de cotización
//
// No hay servidor ni base de datos: el formulario arma un mensaje
// y abre WhatsApp con el texto listo para enviar.
// El número sale del atributo "action" del <form> en index.html.

(function () {
  'use strict';

  const formulario = document.querySelector('[data-contacto]');
  if (!formulario) return;

  const campos = formulario.elements;
  const estado = formulario.querySelector('[data-contacto-estado]');

  // Los botones "Cotizar…" traen data-servicio="Nombre del servicio":
  // al hacer clic dejan ese servicio ya elegido en el formulario.
  document.addEventListener('click', (evento) => {
    const enlace = evento.target.closest('[data-servicio]');
    if (!enlace) return;
    const opcion = Array.from(campos.servicio.options).find((o) => o.value === enlace.dataset.servicio);
    if (opcion) campos.servicio.value = opcion.value;
  });

  // "submit" solo se dispara si el navegador ya validó los campos con required.
  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();

    const nombre = campos.nombre.value.trim();
    const negocio = campos.negocio.value.trim();
    const mensaje = campos.text.value.trim();

    const lineas = [
      'Hola Diego, soy ' + nombre + (negocio ? ' (' + negocio + ')' : '') + '.',
      'Me interesa: ' + campos.servicio.value + '.',
      '',
      mensaje,
    ];

    // encodeURIComponent convierte espacios, acentos y saltos de línea
    // a un formato que puede viajar dentro de una dirección web.
    const destino = formulario.getAttribute('action') + '?text=' + encodeURIComponent(lineas.join('\n'));
    window.open(destino, '_blank', 'noopener');

    estado.textContent = 'Se abrió WhatsApp con tu mensaje listo. Solo falta enviarlo.';
  });
})();
