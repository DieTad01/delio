// carrusel.js — carruseles cíclicos: flechas, contador y avance automático
//
// La pista se desliza con CSS (overflow + scroll-snap). Aquí se hace que:
//   1. no tenga fin: después del último mosaico vuelve a salir el primero,
//   2. las flechas la empujen y el contador diga en cuál va ("3 de 7"),
//   3. se deslice sola, poco a poco y sin parar, si trae el atributo data-carrusel-auto.

(function () {
  'use strict';

  const VELOCIDAD = 40;   // pixeles por segundo a los que se desliza sola
  const ESPERA = 1200;    // milisegundos que se queda quieta después de que alguien la mueve
  const COPIAS = 2;     // cuántas veces se repite la lista para dar la vuelta sin que se note

  const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

  document.querySelectorAll('[data-carrusel]').forEach((carrusel) => {
    const pista = carrusel.querySelector('[data-carrusel-pista]');
    const previo = carrusel.querySelector('[data-carrusel-previo]');
    const siguiente = carrusel.querySelector('[data-carrusel-siguiente]');
    const cuenta = carrusel.querySelector('[data-carrusel-cuenta]');
    const originales = Array.from(pista.children);
    const total = originales.length;
    if (!total) return;

    // ---------- 1. Sin fin ----------
    // El truco: la lista se repite completa detrás de sí misma. Cuando la pista
    // llega a la repetición, se ve exactamente igual que al principio; en ese
    // momento se regresa de golpe al principio y nadie nota el salto.
    for (let n = 0; n < COPIAS; n++) {
      originales.forEach((mosaico) => {
        const copia = mosaico.cloneNode(true);
        // Las copias son solo para la vista: se le ocultan al lector de pantalla
        // y al teclado para que no encuentren cada servicio tres veces.
        copia.setAttribute('aria-hidden', 'true');
        copia.querySelectorAll('a, button').forEach((el) => el.setAttribute('tabindex', '-1'));
        pista.appendChild(copia);
      });
    }

    // Lo que avanza la pista por cada mosaico: su ancho más el espacio entre ellos.
    function paso() {
      const hueco = parseFloat(getComputedStyle(pista).columnGap) || 0;
      return pista.firstElementChild.getBoundingClientRect().width + hueco;
    }

    // Lo que mide una vuelta completa (la lista original, sin copias).
    function vuelta() {
      return paso() * total;
    }

    // Cuántos mosaicos caben completos en pantalla (mínimo uno, máximo todos).
    function aLaVista() {
      const estilo = getComputedStyle(pista);
      const util = pista.clientWidth - parseFloat(estilo.paddingLeft) - parseFloat(estilo.paddingRight);
      const hueco = parseFloat(estilo.columnGap) || 0;
      return Math.min(total, Math.max(1, Math.floor((util + hueco) / paso())));
    }

    // Salto sin animación ("instant" le gana al scroll-behavior: smooth del CSS).
    function saltar(x) {
      pista.scrollTo({ left: x, behavior: 'instant' });
    }

    // Si la pista ya va por las copias, la regresa al lugar equivalente de la lista original.
    function acomodar() {
      const vueltas = Math.floor((pista.scrollLeft + 1) / vuelta());
      if (vueltas > 0) saltar(pista.scrollLeft - vueltas * vuelta());
    }

    // Empujón de las flechas: este sí va animado, salvo que la persona haya pedido menos movimiento.
    function empujar(distancia) {
      quietaHasta = performance.now() + ESPERA;
      acomodar();
      // Si no hay suficiente pista hacia atrás, primero se brinca una vuelta adelante (se ve igual).
      if (pista.scrollLeft + distancia < 0) saltar(pista.scrollLeft + vuelta());
      pista.scrollBy({ left: distancia, behavior: sinMovimiento.matches ? 'instant' : 'smooth' });
    }

    // Mientras "ahora" sea menor que esto, el deslizamiento automático no toca la pista.
    let quietaHasta = 0;

    // ---------- 2. Flechas y contador ----------
    function actualizar() {
      const primero = Math.round(pista.scrollLeft / paso()) % total;
      cuenta.textContent = (primero + 1) + ' de ' + total;
    }

    previo.addEventListener('click', () => empujar(-paso() * aLaVista()));
    siguiente.addEventListener('click', () => empujar(paso() * aLaVista()));

    // "passive" le avisa al navegador que aquí no se va a frenar el deslizamiento.
    pista.addEventListener('scroll', actualizar, { passive: true });
    new ResizeObserver(actualizar).observe(pista);
    actualizar();

    // ---------- 3. Deslizamiento automático ----------
    if (!carrusel.hasAttribute('data-carrusel-auto')) return;

    // Esta clase le quita a la pista el "imán" (scroll-snap) y la animación del CSS,
    // que jalarían cada mosaico a su lugar y no dejarían avanzar de poquito en poquito.
    carrusel.classList.add('carrusel--continuo');

    let cuadro = null;        // el requestAnimationFrame pendiente
    let antes = null;         // cuándo se dibujó el cuadro anterior
    let posicion = 0;         // dónde va la pista, con decimales
    let largoVuelta = vuelta();
    let enPantalla = false;
    let tecladoDentro = false;

    // Se llama unas 60 veces por segundo. Cada vez avanza lo que toca según el
    // tiempo que pasó, así la velocidad es la misma en cualquier pantalla.
    function deslizar(ahora) {
      cuadro = requestAnimationFrame(deslizar);
      const transcurrido = antes === null ? 0 : Math.min(ahora - antes, 100);
      antes = ahora;

      // Si alguien la está moviendo (o la movió con la rueda), se le sigue a esa persona.
      if (ahora < quietaHasta || Math.abs(pista.scrollLeft - posicion) > 2) {
        posicion = pista.scrollLeft;
        if (ahora < quietaHasta) return;
      }

      posicion += VELOCIDAD * transcurrido / 1000;
      if (posicion >= largoVuelta) posicion -= largoVuelta;   // aquí da la vuelta
      pista.scrollLeft = posicion;
    }

    // Se mueve siempre que esté en pantalla, también con el mouse encima.
    // Solo se detiene si alguien la recorre con el teclado, si la pestaña no
    // se está viendo o si la persona pidió menos movimiento en su sistema.
    function revisar() {
      const debeMoverse = enPantalla && !tecladoDentro && !document.hidden && !sinMovimiento.matches;
      if (debeMoverse && cuadro === null) {
        antes = null;
        posicion = pista.scrollLeft;
        cuadro = requestAnimationFrame(deslizar);
      }
      if (!debeMoverse && cuadro !== null) {
        cancelAnimationFrame(cuadro);
        cuadro = null;
      }
    }

    carrusel.addEventListener('focusin', (evento) => {
      tecladoDentro = evento.target.matches(':focus-visible');
      revisar();
    });
    carrusel.addEventListener('focusout', () => {
      tecladoDentro = false;
      revisar();
    });

    // Dedo, clic o rueda sobre la pista: se queda quieta un momento para no pelear con la persona.
    // Y mientras la pista se siga moviendo por ese gesto, la espera se va renovando.
    function esperar() {
      quietaHasta = performance.now() + ESPERA;
    }
    pista.addEventListener('pointerdown', esperar);
    pista.addEventListener('touchstart', esperar, { passive: true });
    pista.addEventListener('wheel', esperar, { passive: true });
    pista.addEventListener('scroll', () => {
      if (performance.now() < quietaHasta) esperar();
    }, { passive: true });

    new ResizeObserver(() => {
      largoVuelta = vuelta();
    }).observe(pista);

    // Dos avisos: cuando asoma el carrusel (para arrancar las señales de inmediato)
    // y cuando ya se ve casi la mitad (para empezar a deslizarlo).
    new IntersectionObserver((entradas) => {
      const entrada = entradas[entradas.length - 1];
      carrusel.classList.toggle('a-la-vista', entrada.isIntersecting);
      enPantalla = entrada.intersectionRatio >= 0.4;
      revisar();
    }, { threshold: [0, 0.4] }).observe(carrusel);

    document.addEventListener('visibilitychange', revisar);
    sinMovimiento.addEventListener('change', revisar);
  });
})();
