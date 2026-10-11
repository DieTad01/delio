// ondas.js — las señales del sitio
//
// 1. Mosaicos y carteles: cada elemento con data-onda="tipo" recibe un <svg>
//    con esa señal dibujada. El movimiento al pasar el mouse lo hace el CSS.
// 2. Portada: una onda animada en el <canvas data-onda-portada>.

(function () {
  'use strict';

  const TAU = Math.PI * 2;
  const SVG_NS = 'http://www.w3.org/2000/svg';

  // ---------- Catálogo de señales ----------
  // Todas describen UNA vuelta: u va de 0 a 1 y la altura de -1 a 1.
  // Deben terminar a la misma altura que empiezan (o con un salto vertical),
  // para que al repetirlas no se note la unión.

  // Curvas: una fórmula que se evalúa punto por punto.
  const curvas = {
    seno: (u) => Math.sin(TAU * 2 * u),
    // Portadora de radio: una onda rápida cuyo tamaño sube y baja.
    am: (u) => Math.sin(TAU * 11 * u) * (0.2 + 0.8 * Math.sin(Math.PI * u) ** 2),
    // Un golpe que se va apagando.
    amortiguada: (u) => Math.sin(TAU * 6 * u) * Math.exp(-4.5 * u),
  };

  // Repite un tramo `veces` a lo largo de la vuelta. `tramo` recibe dónde empieza (a) y cuánto mide (w).
  function repetir(veces, tramo) {
    const puntos = [];
    for (let k = 0; k < veces; k++) puntos.push(...tramo(k / veces, 1 / veces));
    return puntos;
  }

  function pulso(centro, mitad) {
    return [[centro - mitad, -0.5], [centro - mitad, 0.8], [centro + mitad, 0.8], [centro + mitad, -0.5]];
  }

  // Quebradas: listas de esquinas [u, altura] unidas con rectas.
  const quebradas = {
    cuadrada: repetir(3, (a, w) => [[a, -0.8], [a + w / 2, -0.8], [a + w / 2, 0.8], [a + w, 0.8]]),
    triangular: repetir(3, (a, w) => [[a, -0.8], [a + w / 2, 0.8], [a + w, -0.8]]),
    sierra: repetir(4, (a, w) => [[a, -0.8], [a + w, 0.8]]),
    escalera: repetir(5, (a, w) => [[a, -0.8 + a * 2], [a + w, -0.8 + a * 2]]),
    pulsos: [[0, -0.5], ...pulso(0.14, 0.035), ...pulso(0.36, 0.035), ...pulso(0.58, 0.035), ...pulso(0.82, 0.07), [1, -0.5]],
    latido: [
      [0, 0], [0.26, 0], [0.31, 0.16], [0.36, 0], [0.42, 0], [0.455, -0.22], [0.5, 1],
      [0.545, -0.5], [0.585, 0], [0.66, 0], [0.73, 0.28], [0.8, 0], [1, 0],
    ],
  };

  function unaVuelta(tipo) {
    if (quebradas[tipo]) return quebradas[tipo];
    const curva = curvas[tipo] || curvas.seno;
    const pasos = 240;
    const puntos = [];
    for (let i = 0; i <= pasos; i++) puntos.push([i / pasos, curva(i / pasos)]);
    return puntos;
  }

  // ---------- 1. Señales en SVG ----------
  // El lienzo mide 200 x 100: dos vueltas seguidas, de 100 de ancho cada una.
  function trazo(tipo) {
    const vuelta = unaVuelta(tipo);
    const partes = [];
    for (let n = 0; n < 2; n++) {
      for (const [u, altura] of vuelta) {
        const x = (n + u) * 100;
        const y = 50 - altura * 24;
        partes.push(x.toFixed(2) + ' ' + y.toFixed(2));
      }
    }
    return 'M' + partes.join('L');
  }

  function crearSenal(tipo) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'senal');
    svg.setAttribute('viewBox', '0 0 200 100');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');

    const camino = document.createElementNS(SVG_NS, 'path');
    camino.setAttribute('d', trazo(tipo));
    svg.appendChild(camino);
    return svg;
  }

  document.querySelectorAll('[data-onda]').forEach((caja) => {
    caja.prepend(crearSenal(caja.dataset.onda));
  });

  // ---------- 2. Onda de la portada ----------
  const lienzo = document.querySelector('[data-onda-portada]');
  if (!lienzo || !lienzo.getContext) return;

  const pincel = lienzo.getContext('2d');
  const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  let color = getComputedStyle(lienzo).color;

  let ancho = 0;
  let alto = 0;
  let aLaVista = true;
  let cuadro = null;

  function medir() {
    // En pantallas de alta densidad el canvas necesita más pixeles reales
    // que los que ocupa en CSS; si no, la línea se ve borrosa.
    const densidad = Math.min(window.devicePixelRatio || 1, 2);
    const caja = lienzo.getBoundingClientRect();
    ancho = caja.width;
    alto = caja.height;
    lienzo.width = Math.round(ancho * densidad);
    lienzo.height = Math.round(alto * densidad);
    pincel.setTransform(densidad, 0, 0, densidad, 0, 0);
  }

  function dibujar(segundos) {
    const medio = alto / 2;
    const amplitud = alto * 0.44;
    const centro = ancho / 2;
    const apertura = Math.min(ancho * 0.26, 300);

    pincel.clearRect(0, 0, ancho, alto);
    pincel.beginPath();
    for (let x = 0; x <= ancho; x += 1.5) {
      // Campana: la onda solo "abre" al centro, bajo el nombre, y se aplana hacia las orillas.
      const distancia = (x - centro) / apertura;
      const campana = Math.exp(-distancia * distancia);
      const respiro = 0.6 + 0.4 * Math.sin(x / 90 + segundos * 0.7);
      const y = medio - amplitud * campana * respiro * Math.sin(x / 5.2 - segundos * 2.2);
      if (x === 0) pincel.moveTo(x, y);
      else pincel.lineTo(x, y);
    }
    pincel.lineWidth = 2;
    pincel.lineJoin = 'round';
    pincel.strokeStyle = color;
    pincel.stroke();
  }

  function animar(ms) {
    dibujar(ms / 1000);
    cuadro = requestAnimationFrame(animar);
  }

  function arrancar() {
    cancelAnimationFrame(cuadro);
    cuadro = null;
    if (sinMovimiento.matches || !aLaVista) {
      dibujar(0);
      return;
    }
    cuadro = requestAnimationFrame(animar);
  }

  // Volver a medir cuando cambia el tamaño de la ventana.
  new ResizeObserver(() => {
    medir();
    arrancar();
  }).observe(lienzo);

  // No gastar batería animando algo que ya no está en pantalla.
  new IntersectionObserver((entradas) => {
    aLaVista = entradas[0].isIntersecting;
    arrancar();
  }).observe(lienzo);

  sinMovimiento.addEventListener('change', arrancar);

  // Al cambiar entre día y noche (js/tema.js avisa con este evento) la línea toma el color nuevo.
  document.addEventListener('tema-cambiado', () => {
    color = getComputedStyle(lienzo).color;
    if (cuadro === null) dibujar(0);
  });
})();
