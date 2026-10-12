// contacto.js — formulario de cotización
//
// El formulario arma un mensaje y abre WhatsApp con el texto listo para enviar.
// El número sale del atributo "action" del <form> en index.html.
//
// Además manda una copia de la solicitud al servidor del panel (servidor/app.py),
// para que quede registrada aunque la persona no llegue a enviar el WhatsApp.

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

    // La copia para el panel. No se espera la respuesta ni se avisa si falla:
    // lo importante para la persona es que WhatsApp ya se abrió.
    // (Al abrir index.html con doble clic no hay servidor, por eso la condición.)
    if (window.location.protocol.startsWith('http')) {
      fetch('/api/solicitudes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre, negocio, mensaje,
          contacto: campos.contacto.value.trim(),
          servicio: campos.servicio.value,
        }),
        keepalive: true,   // que termine de enviarse aunque la persona cambie de pestaña
      }).catch(() => {});
    }

    estado.textContent = 'Se abrió WhatsApp con tu mensaje listo. Solo falta enviarlo.';
  });
})();
