// logo.js — el logo de la portada, con la onda en movimiento
//
// En la imagen del logo (img/logo-delio.svg) la onda ya viene dibujada y no se
// puede mover. Aquí se dibuja el logo desde cero en un <canvas>, con las letras
// rectas de js/logo-puntos.js, y en cada cuadro se le aplica la misma onda
// recorrida un poquito: cada "renglón" de la letra se desliza a un lado según su altura.
//
// Si no hay JavaScript se queda la imagen fija. Si la persona pidió menos
// movimiento, el logo se dibuja aquí pero quieto (así toma el color del modo nocturno).

(function () {
  'use strict';

  const VUELTAS_POR_SEGUNDO = 0.12;   // qué tan rápido corre la onda por las letras (más bajo, más lento)

  const datos = window.DELIO_LOGO;
  const marca = document.querySelector('.marca');
  const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (!datos || !marca) return;

  const lienzo = document.createElement('canvas');
  lienzo.className = 'marca__lienzo';
  lienzo.setAttribute('aria-hidden', 'true');   // el nombre lo sigue dando el alt de la imagen
  const pincel = lienzo.getContext('2d');
  if (!pincel) return;

  marca.appendChild(lienzo);
  marca.classList.add('marca--viva');           // el CSS esconde la imagen fija y deja el lienzo

  const TAU = Math.PI * 2;
  let color = getComputedStyle(marca).color;
  let escala = 1;
  let aLaVista = true;
  let cuadro = null;

  function medir() {
    // Más pixeles reales que los de CSS en pantallas de alta densidad, para que no se vea borroso.
    const densidad = Math.min(window.devicePixelRatio || 1, 2);
    const ancho = lienzo.getBoundingClientRect().width;
    lienzo.width = Math.round(ancho * densidad);
    lienzo.height = Math.round(ancho * densidad * datos.alto / datos.ancho);
    escala = lienzo.width / datos.ancho;
  }

  function dibujar(segundos) {
    const fase = TAU * VUELTAS_POR_SEGUNDO * segundos;
    pincel.clearRect(0, 0, lienzo.width, lienzo.height);
    pincel.fillStyle = color;

    for (const letra of datos.letras) {
      pincel.beginPath();
      for (const contorno of letra) {
        for (let i = 0; i < contorno.length; i += 2) {
          const altura = contorno[i + 1];
          // La onda: cuánto se recorre este punto a los lados, según su altura y el momento.
          const x = contorno[i] + datos.fuerza * Math.sin(TAU * altura / datos.largo + fase);
          const y = datos.base - altura;
          if (i === 0) pincel.moveTo(x * escala, y * escala);
          else pincel.lineTo(x * escala, y * escala);
        }
        pincel.closePath();
      }
      // "evenodd": un contorno dentro de otro es un hueco (el centro de la D, la e y la o).
      pincel.fill('evenodd');
    }
  }

  function animar(ms) {
    dibujar(ms / 1000);
    cuadro = requestAnimationFrame(animar);
  }

  function arrancar() {
    cancelAnimationFrame(cuadro);
    cuadro = null;
    if (!aLaVista || document.hidden || sinMovimiento.matches) {
      dibujar(0);
      return;
    }
    cuadro = requestAnimationFrame(animar);
  }

  new ResizeObserver(() => {
    medir();
    arrancar();
  }).observe(lienzo);

  // No animar lo que ya no está en pantalla.
  new IntersectionObserver((entradas) => {
    aLaVista = entradas[0].isIntersecting;
    arrancar();
  }).observe(lienzo);

  document.addEventListener('visibilitychange', arrancar);
  sinMovimiento.addEventListener('change', arrancar);

  // Al cambiar entre día y noche el logo toma el color nuevo.
  document.addEventListener('tema-cambiado', () => {
    color = getComputedStyle(marca).color;
    if (cuadro === null) dibujar(0);
  });
})();
