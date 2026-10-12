// panel.js — el panel privado (panel.html)
//
// Esta página no trae datos: los pide al servidor (carpeta servidor/) con fetch.
// El servidor solo responde si hay sesión abierta; la sesión es una cookie que
// este script no puede leer (httponly), el navegador la manda solo.
//
// Las cuentas (márgenes, probabilidades) las hace el servidor en servidor/analisis.py.
// Aquí solo se dibujan: cada cifra que ves viene ya calculada.
//
// Todo lo que llega se pone en la página con textContent, nunca con innerHTML:
// así, si alguien escribe código en el formulario público, se ve como texto y no se ejecuta.

(function () {
  'use strict';

  const $ = (selector, raiz) => (raiz || document).querySelector(selector);
  const entrada = $('[data-entrada]');
  const panel = $('[data-panel]');
  const menu = $('[data-menu]');
  const aviso = $('[data-aviso]');
  if (!entrada || !panel) return;

  const pesos = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 });
  const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const CONFIANZA = {
    baja: 'pocos casos, tómalo como aproximado',
    media: 'historia suficiente para orientarte',
    alta: 'historia amplia',
  };
  let datos = null;

  // ---------- Hablar con el servidor ----------

  async function api(ruta, metodo, cuerpo) {
    const respuesta = await fetch('/api/' + ruta, {
      method: metodo || 'GET',
      // X-Delio: el servidor rechaza cualquier cambio que no traiga este encabezado (ver servidor/app.py).
      headers: { 'Content-Type': 'application/json', 'X-Delio': 'panel' },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
    if (respuesta.status === 401 && ruta !== 'entrar') {
      mostrarEntrada();
      throw new Error('Tu sesión terminó. Vuelve a entrar.');
    }
    const json = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) throw new Error(json.error || 'El servidor no respondió bien (' + respuesta.status + ').');
    return json;
  }

  function avisar(texto) {
    aviso.textContent = texto || '';
    aviso.hidden = !texto;
  }

  // ---------- Entrar y salir ----------

  function mostrarEntrada() {
    panel.hidden = true;
    menu.hidden = true;
    entrada.hidden = false;
  }

  async function mostrarPanel() {
    await cargar();
    ponerFechaDeHoy();
    entrada.hidden = true;
    panel.hidden = false;
    menu.hidden = false;
  }

  $('[data-entrar]').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const estado = $('[data-entrar-estado]');
    estado.textContent = '';
    try {
      await api('entrar', 'POST', { clave: formulario.elements.clave.value });
      formulario.reset();
      await mostrarPanel();
    } catch (error) {
      estado.textContent = error.message;
    }
  });

  $('[data-salir]').addEventListener('click', async () => {
    await api('salir', 'POST').catch(() => {});
    datos = null;
    mostrarEntrada();
  });

  // ---------- Piezas para pintar ----------

  // Crea un elemento con clase y texto. Es la única forma en que se escribe en la página.
  function pieza(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function plural(cuantos, uno, varios) {
    return cuantos + ' ' + (cuantos === 1 ? uno : varios);
  }

  const tope = (valor) => Math.max(0, Math.min(100, valor));

  // Una barra con pedazos. partes: [{ tipo: 'lleno' | 'rayado', desde, ancho }], en porcentaje.
  // marca: dónde va la raya de referencia (o null).  texto: lo que lee un lector de pantalla.
  function barra(partes, marca, texto, alta) {
    const caja = pieza('div', 'barra' + (alta ? ' barra--alta' : ''));
    caja.setAttribute('role', 'img');
    caja.setAttribute('aria-label', texto);
    partes.forEach((parte) => {
      if (!(parte.ancho > 0)) return;
      const pedazo = pieza('i', 'barra__parte barra__parte--' + parte.tipo);
      // Las medidas van como variables de CSS; css/panel.css las convierte en posición y ancho.
      pedazo.style.setProperty('--desde', tope(parte.desde) + '%');
      pedazo.style.setProperty('--ancho', Math.min(parte.ancho, 100 - tope(parte.desde)) + '%');
      caja.append(pedazo);
    });
    if (marca !== null && marca !== undefined) {
      const raya = pieza('i', 'barra__marca');
      raya.style.setProperty('--desde', tope(marca) + '%');
      caja.append(raya);
    }
    return caja;
  }

  // Un renglón de cualquier lista: título, dato a la derecha, barra, texto y pie.
  function registro({ titulo, dato, grafica, texto, pie, apagado }) {
    const renglon = pieza('li', 'registro' + (apagado ? ' registro--apagado' : ''));
    renglon.append(pieza('p', 'registro__titulo', titulo));
    renglon.append(pieza('p', 'registro__dato', dato || ''));
    if (grafica) {
      grafica.classList.add('registro__barra');
      renglon.append(grafica);
    }
    if (texto) renglon.append(pieza('p', 'registro__texto', texto));
    const partes = (pie || []).filter(Boolean);
    if (partes.length) {
      const fondo = pieza('p', 'registro__pie');
      partes.forEach((parte) => fondo.append(typeof parte === 'string' ? pieza('span', '', parte) : parte));
      renglon.append(fondo);
    }
    return renglon;
  }

  function llenar(nombre, filas, armar, vacio) {
    const lista = $('[data-lista="' + nombre + '"]');
    lista.replaceChildren(...filas.map(armar));
    if (!filas.length) lista.append(pieza('li', 'registros__vacio', vacio));
  }

  function botonBorrar(tabla, id, pregunta) {
    const boton = pieza('button', 'enlace', 'Borrar');
    boton.type = 'button';
    boton.addEventListener('click', async () => {
      if (!window.confirm(pregunta)) return;
      await accion(() => api(tabla + '/' + id, 'DELETE'));
    });
    return boton;
  }

  function selector(tabla, fila, opciones) {
    const lista = pieza('select');
    lista.setAttribute('aria-label', 'Estado');
    opciones.forEach((opcion) => {
      const elemento = pieza('option', '', opcion);
      elemento.value = opcion;
      lista.append(elemento);
    });
    lista.value = fila.estado;
    lista.addEventListener('change', () => accion(() => api(tabla + '/' + fila.id, 'PATCH', { estado: lista.value })));
    return lista;
  }

  // De la presentación larga del navegador ("Mozilla/5.0 (Windows NT 10.0…) Chrome/140…")
  // saca algo que se pueda reconocer de un vistazo: "Chrome en Windows".
  function dispositivo(agente) {
    const navegador = /Edg\//.test(agente) ? 'Edge' : /OPR\//.test(agente) ? 'Opera'
      : /Firefox\//.test(agente) ? 'Firefox' : /Chrome\//.test(agente) ? 'Chrome'
        : /Safari\//.test(agente) ? 'Safari' : 'Navegador desconocido';
    const sistema = /Android/.test(agente) ? 'Android' : /iPhone|iPad/.test(agente) ? 'iPhone o iPad'
      : /Windows/.test(agente) ? 'Windows' : /Mac OS X/.test(agente) ? 'Mac'
        : /Linux/.test(agente) ? 'Linux' : 'sistema desconocido';
    return navegador + ' en ' + sistema;
  }

  // El servidor manda las horas de las sesiones como segundos desde 1970.
  function momento(segundos) {
    return new Date(segundos * 1000).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
  }

  // ---------- Las gráficas del negocio ----------

  // Cómo se lee un margen frente al objetivo.
  function juicio(margen, objetivo) {
    if (margen === null) return '';
    if (margen < 0) return 'Pierdes dinero';
    return margen >= objetivo ? 'Arriba de tu objetivo' : 'Abajo de tu objetivo';
  }

  // La barra de un margen: a la izquierda lo que cuesta (rayado), a la derecha lo que queda (lleno),
  // y la raya donde debería empezar lo que queda para cumplir el objetivo.
  function barraDeMargen(margen, objetivo) {
    const queda = tope(margen);
    return barra(
      [{ tipo: 'rayado', desde: 0, ancho: 100 - queda }, { tipo: 'lleno', desde: 100 - queda, ancho: queda }],
      100 - objetivo,
      'De cada 100 pesos te quedan ' + Math.round(margen) + '. Tu objetivo es ' + Math.round(objetivo) + '.'
    );
  }

  function pintarMes(c) {
    const m = c.meta;
    const margenes = c.margenes;
    $('[data-cifra="cobrado"]').textContent = pesos.format(m.cobrado);
    $('[data-cifra="meta"]').textContent = m.meta ? pesos.format(m.meta) : 'Sin meta';
    $('[data-cifra="probabilidad"]').textContent = m.probabilidad === null ? '—' : m.probabilidad + '%';
    $('[data-cifra="margen"]').textContent = margenes.margen === null ? '—' : '$' + Math.round(margenes.margen);

    const frase = $('[data-meta-frase]');
    const caja = $('[data-meta-barra]');
    const explica = $('[data-meta-explica]');
    if (!m.meta) {
      frase.textContent = 'Todavía no hay una meta mensual. Ponla en tu Cotizador (Mis finanzas) e importa sus datos.';
      caja.replaceChildren();
      explica.textContent = '';
    } else {
      frase.textContent = m.falta > 0
        ? 'Vas en el día ' + m.dia + ' de ' + m.dias_del_mes + '. Te faltan ' + pesos.format(m.falta) + ' para tu meta.'
        : 'Ya llegaste a tu meta de este mes.';
      const cobrado = 100 * m.cobrado / m.meta;
      const esperado = 100 * m.esperado / m.meta;
      caja.replaceChildren(barra(
        [{ tipo: 'lleno', desde: 0, ancho: tope(cobrado) }, { tipo: 'rayado', desde: tope(cobrado), ancho: esperado }],
        100 * m.dia / m.dias_del_mes,
        'Cobrado ' + pesos.format(m.cobrado) + ' de ' + pesos.format(m.meta) + '. Esperado de lo abierto: ' + pesos.format(m.esperado) + '.',
        true
      ));
      const abierto = c.por_cerrar.filter((trato) => trato.monto).length;
      explica.textContent = (abierto
        ? 'La probabilidad sale de lo que hoy tienes abierto: ' + plural(abierto, 'trato', 'tratos') + ' por ' + pesos.format(m.por_cerrar)
          + ', de los que se espera ganar ' + pesos.format(m.esperado) + '. Supone que se deciden este mes.'
        : 'Hoy no tienes nada abierto que pueda sumar a la meta: por eso la probabilidad es ' + m.probabilidad + '%. Sube en cuanto haya cotizaciones pendientes o solicitudes nuevas.')
        + ' Al ritmo que llevas, cerrarías el mes en ' + pesos.format(m.proyeccion) + '.';
    }

    // Columnas: una por mes. La más alta mide 170 px; las demás, en proporción.
    const ALTO = 170;
    const maximo = Math.max(m.meta, ...c.meses.map((mes) => mes.ingresos), 1);
    const columnas = $('[data-columnas]');
    columnas.replaceChildren(...c.meses.map((mes, indice) => {
      const columna = pieza('li', 'columnas__mes' + (indice === c.meses.length - 1 ? ' columnas__mes--actual' : ''));
      const espacio = pieza('div', 'columnas__espacio');
      const cuerpo = pieza('i', 'columnas__barra');
      cuerpo.style.setProperty('--alto', Math.round(ALTO * mes.ingresos / maximo) + 'px');
      espacio.append(pieza('span', 'columnas__valor', mes.ingresos ? pesos.format(mes.ingresos) : ''), cuerpo);
      columna.append(espacio, pieza('span', 'columnas__nombre', MESES[Number(mes.mes.slice(5)) - 1] + (indice === c.meses.length - 1 ? ' (va)' : '')));
      return columna;
    }));
    if (m.meta) {
      const linea = pieza('li', 'columnas__meta', 'Meta ' + pesos.format(m.meta));
      linea.setAttribute('aria-hidden', 'true');
      linea.style.setProperty('--alto', Math.round(ALTO * m.meta / maximo) + 'px');
      columnas.append(linea);
    }
  }

  function pintarEmbudo(c) {
    const mayor = Math.max(...c.embudo.map((paso) => paso.cantidad), 1);
    llenar('embudo', c.embudo, (paso, indice) => {
      const anterior = indice ? c.embudo[indice - 1].cantidad : 0;
      // "De cada 100" solo tiene sentido si este paso es una parte del anterior.
      const tasa = anterior && paso.cantidad <= anterior
        ? Math.round(100 * paso.cantidad / anterior) + ' de cada 100 del paso anterior' : '';
      return registro({
        titulo: paso.paso,
        dato: String(paso.cantidad),
        grafica: barra([{ tipo: 'lleno', desde: 0, ancho: 100 * paso.cantidad / mayor }], null, paso.paso + ': ' + paso.cantidad),
        pie: [tasa],
        apagado: !paso.cantidad,
      });
    }, '');
  }

  function pintarPorCerrar(c) {
    llenar('por-cerrar', c.por_cerrar, (trato) => registro({
      titulo: trato.titulo,
      dato: trato.monto ? pesos.format(trato.monto) + (trato.monto_estimado ? ' aprox.' : '') : 'Sin monto',
      grafica: barra([{ tipo: 'lleno', desde: 0, ancho: trato.probabilidad }], null,
        'Probabilidad de ganarla: ' + trato.probabilidad + ' por ciento'),
      texto: trato.detalle,
      pie: [
        trato.probabilidad + '% de probabilidad',
        trato.esperado ? 'Valor esperado: ' + pesos.format(trato.esperado) : '',
        trato.servicio,
        trato.tipo === 'cotización'
          ? (trato.vencida ? 'Vencida: lleva ' + plural(trato.dias, 'día', 'días') : 'Hace ' + plural(trato.dias, 'día', 'días'))
          : 'Solicitud de hace ' + plural(trato.dias, 'día', 'días'),
        trato.monto_estimado && trato.monto ? 'Monto: lo que suele costar ese servicio' : '',
      ],
    }), 'No tienes cotizaciones pendientes ni solicitudes nuevas.');

    const m = c.meta;
    $('[data-por-cerrar-explica]').textContent = c.por_cerrar.length
      ? 'Si todo se ganara: ' + pesos.format(m.por_cerrar) + '. Valor esperado (cada monto por su probabilidad): ' + pesos.format(m.esperado) + '.'
      : '';

    const general = c.cierre.cotizaciones;
    const filas = [{ servicio: 'Todo el negocio', probabilidad: general.probabilidad, casos: general.cerradas,
      ganadas: general.ganadas, confianza: general.confianza }]
      .concat(c.por_servicio.filter((s) => s.casos));
    llenar('cierre', filas, (s) => registro({
      titulo: s.servicio,
      dato: s.probabilidad + '%',
      grafica: barra([{ tipo: 'lleno', desde: 0, ancho: s.probabilidad }], null, s.servicio + ': ' + s.probabilidad + ' por ciento'),
      pie: [
        s.casos ? 'Ganadas ' + s.ganadas + ' de ' + s.casos : 'Sin historia todavía: se parte de 50%',
        'Confianza ' + s.confianza + ': ' + CONFIANZA[s.confianza],
      ],
    }), '');
  }

  function pintarMargenes(c) {
    const m = c.margenes;
    const frase = $('[data-margen-frase]');
    if (m.margen === null) {
      frase.textContent = 'Todavía no hay cotizaciones ganadas para calcular tu margen. Importa los datos de tu Cotizador.';
    } else {
      frase.textContent = 'De cada $100 que cobras te quedan $' + Math.round(m.margen) + '. Tu objetivo es que te queden al menos $'
        + Math.round(m.objetivo) + ' (' + m.objetivo_sobre_costo + '% sobre tus costos). ' + juicio(m.margen, m.objetivo) + '.';
    }

    const conVentas = c.por_servicio.filter((s) => s.vendido > 0);
    llenar('margen-servicio', conVentas, (s) => registro({
      titulo: s.servicio,
      dato: Math.round(s.margen) + '%',
      grafica: barraDeMargen(s.margen, m.objetivo),
      pie: ['Vendido ' + pesos.format(s.vendido), 'Te costó ' + pesos.format(s.costo),
        'Te quedó ' + pesos.format(s.vendido - s.costo), juicio(s.margen, m.objetivo)],
    }), 'Sin ventas todavía.');

    llenar('margen-cotizacion', m.cotizaciones, (q) => registro({
      titulo: [q.folio, q.cliente].filter(Boolean).join(' · '),
      dato: q.margen === null ? '—' : Math.round(q.margen) + '%',
      grafica: q.margen === null ? null : barraDeMargen(q.margen, m.objetivo),
      texto: q.asunto,
      apagado: q.estado === 'rechazada',
      pie: [
        q.estado,
        'Precio ' + pesos.format(q.precio) + (q.mensual ? ' al mes' : ''),
        'Costo ' + pesos.format(q.costo),
        juicio(q.margen, m.objetivo),
        q.estimado ? 'Costo estimado' : 'Costo con desglose',
      ],
    }), 'Sin cotizaciones. Importa los datos de tu Cotizador.');

    $('[data-margen-explica]').textContent = m.cuantas
      ? 'El costo se calcula con los factores de tu Cotizador (tu hora, indirectos y financiamiento). '
        + (m.estimadas
          ? plural(m.estimadas, 'cotización no trae', 'cotizaciones no traen') + ' desglose de horas y materiales: su costo se estimó en '
            + m.costo_estimado_pct + '% del precio, así que esos márgenes son aproximados.'
          : 'Todas traen su desglose de horas y materiales.')
      : '';

    // Mensualidades y satisfacción: renglones sencillos.
    const renglones = c.mensualidades.clientes.map((cliente) => ({
      titulo: cliente.cliente + (cliente.servicio ? ' · ' + cliente.servicio : ''),
      dato: pesos.format(cliente.mensual) + ' al mes',
      pie: [cliente.vence ? 'Vence el ' + cliente.vence + (cliente.dias !== null ? ' (en ' + plural(cliente.dias, 'día', 'días') + ')' : '') : 'Sin fecha de vencimiento'],
    }));
    if (c.satisfaccion) {
      const s = c.satisfaccion;
      renglones.push({
        titulo: 'Satisfacción de tus clientes',
        dato: s.estrellas === null ? '' : s.estrellas + ' de 5 estrellas',
        pie: [s.nps === null ? '' : 'Recomendación (NPS): ' + s.nps + ' en una escala de -100 a 100',
          'Con ' + plural(s.respuestas, 'opinión', 'opiniones')],
      });
    }
    llenar('mensualidades', renglones, registro, 'Sin clientes de mensualidad ni opiniones registradas.');
  }

  // ---------- Lo demás ----------

  function pintar() {
    const c = datos.cuentas;
    pintarMes(c);
    pintarEmbudo(c);
    pintarPorCerrar(c);
    pintarMargenes(c);

    // El selector de servicio de "Ingresos" usa los mismos servicios de la página.
    // Al volver a pintar se respeta lo que ya estuviera elegido (la primera vez solo hay "Otro").
    const lista = $('[data-servicios]');
    const elegido = lista.options.length > 1 ? lista.value : '';
    lista.replaceChildren(...datos.servicios.concat('Otro').map((nombre) => pieza('option', '', nombre)));
    if (datos.servicios.concat('Otro').includes(elegido)) lista.value = elegido;

    const espera = {};
    c.sin_atender.forEach((s) => { espera[s.id] = s.dias; });
    llenar('solicitudes', datos.solicitudes, (s) => registro({
      titulo: 'Solicitud ' + s.id + ' · ' + s.nombre + (s.negocio ? ' · ' + s.negocio : ''),
      dato: s.creada,
      texto: s.mensaje,
      apagado: s.estado === 'perdida',
      pie: [
        s.servicio,
        espera[s.id] > 0 ? 'Lleva ' + plural(espera[s.id], 'día', 'días') + ' sin atender' : '',
        s.contacto ? 'Contacto: ' + s.contacto : 'Sin contacto: búscalo por nombre en WhatsApp',
        selector('solicitudes', s, ['nueva', 'cotizada', 'ganada', 'perdida']),
        botonBorrar('solicitudes', s.id, '¿Borrar la solicitud de ' + s.nombre + '? No se puede deshacer.'),
      ],
    }), 'Todavía no llega ninguna solicitud por el formulario.');

    llenar('ingresos', datos.ingresos, (i) => registro({
      titulo: i.cliente || i.concepto || i.servicio,
      dato: pesos.format(i.monto),
      pie: [i.fecha, i.servicio, i.cliente ? i.concepto : '',
        botonBorrar('ingresos', i.id, '¿Borrar este ingreso de ' + pesos.format(i.monto) + '?')],
    }), 'Sin ingresos sueltos.');

    llenar('objetivos', datos.objetivos, (o) => registro({
      titulo: o.titulo,
      dato: o.limite ? 'Para el ' + o.limite : '',
      texto: o.meta,
      apagado: o.estado !== 'activo',
      pie: [selector('objetivos', o, ['activo', 'logrado', 'pausado']),
        botonBorrar('objetivos', o.id, '¿Borrar este objetivo?')],
    }), 'Sin objetivos.');

    llenar('notas', datos.notas, (n) => registro({
      titulo: n.creada,
      texto: n.texto,
      pie: [botonBorrar('notas', n.id, '¿Borrar esta nota?')],
    }), 'Sin notas.');

    const visitas = datos.visitas;
    const problema = $('[data-visitas-problema]');
    problema.textContent = visitas.problema || '';
    problema.hidden = !visitas.problema;
    const masVistas = Math.max(...visitas.por_dia.map((d) => d.vistas), 1);
    llenar('visitas', visitas.por_dia, (d) => registro({
      titulo: d.fecha,
      dato: plural(d.vistas, 'vista', 'vistas') + ' · ' + plural(d.visitantes, 'persona', 'personas'),
      grafica: barra([{ tipo: 'lleno', desde: 0, ancho: 100 * d.vistas / masVistas }], null, d.fecha + ': ' + d.vistas + ' vistas'),
    }), 'Todavía no hay visitas contadas.');
    llenar('origenes', visitas.origenes, (o) => registro({
      titulo: o.sitio,
      dato: plural(o.veces, 'visita', 'visitas'),
    }), 'Sin datos: la mayoría llega escribiendo la dirección o desde WhatsApp, que no dice de dónde viene.');

    // Cotizador: qué se importó y cuándo.
    const importacion = c.importacion;
    $('[data-importacion]').textContent = importacion
      ? 'Última importación: ' + importacion.fecha + ' · ' + plural(importacion.cotizaciones, 'cotización', 'cotizaciones')
        + ', ' + plural(importacion.clientes, 'cliente', 'clientes') + ' y ' + plural(importacion.movimientos, 'movimiento', 'movimientos') + '.'
      : 'Todavía no se ha importado nada del Cotizador.';

    // Acceso: cómo está protegido el panel, quién tiene sesión y qué ha pasado.
    const acceso = datos.acceso;
    llenar('sesiones', acceso.sesiones, (s) => registro({
      titulo: dispositivo(s.agente) + (s.esta ? ' · esta sesión' : ''),
      dato: s.ip,
      pie: ['Abierta: ' + momento(s.creada), 'Último uso: ' + momento(s.usada)],
    }), 'Sin sesiones abiertas.');
    llenar('bitacora', acceso.bitacora, (b) => registro({
      titulo: b.suceso,
      dato: b.fecha,
      apagado: b.suceso === 'entró' || b.suceso === 'salió',
      pie: [b.ip, dispositivo(b.agente)],
    }), 'Sin movimientos todavía.');
    $('[data-cerrar-otras]').disabled = acceso.sesiones.length < 2;
  }

  async function cargar() {
    datos = await api('panel');
    pintar();
  }

  // Hace un cambio en el servidor y vuelve a pedir todo, para que la pantalla diga la verdad.
  async function accion(cambio) {
    avisar('');
    try {
      await cambio();
      await cargar();
    } catch (error) {
      avisar(error.message);
    }
  }

  $('[data-cerrar-otras]').addEventListener('click', () => {
    if (!window.confirm('¿Cerrar la sesión en todos los demás dispositivos?')) return;
    accion(() => api('acceso/cerrar-otras', 'POST'));
  });

  // ---------- Formularios para agregar ----------

  document.querySelectorAll('[data-agregar]').forEach((formulario) => {
    formulario.addEventListener('submit', (evento) => {
      evento.preventDefault();
      const valores = Object.fromEntries(new FormData(formulario));
      accion(async () => {
        await api(formulario.dataset.agregar, 'POST', valores);
        formulario.reset();
        ponerFechaDeHoy();
      });
    });
  });

  function ponerFechaDeHoy() {
    const fecha = $('#ingreso-fecha');
    if (datos && !fecha.value) fecha.value = datos.hoy;
  }

  // ---------- Importar del Cotizador ----------

  $('[data-importar]').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const estado = $('[data-importar-estado]');
    const archivo = formulario.elements.archivo.files[0];
    if (!archivo) return;
    estado.textContent = 'Importando…';
    try {
      // El archivo se lee aquí, en tu navegador, y lo que viaja al servidor es su contenido.
      const contenido = JSON.parse(await archivo.text());
      const resumen = await api('cotizador', 'POST', contenido);
      formulario.reset();
      await cargar();
      estado.textContent = 'Listo: ' + plural(resumen.cotizaciones, 'cotización', 'cotizaciones') + ' y '
        + plural(resumen.clientes, 'cliente', 'clientes') + '.';
    } catch (error) {
      estado.textContent = error instanceof SyntaxError ? 'Ese archivo no es un JSON válido.' : error.message;
    }
  });

  // ---------- Arranque ----------

  (async function () {
    if (!window.location.protocol.startsWith('http')) {
      avisar('El panel necesita su servidor. En tu PC: corre "python servidor/app.py" y abre http://localhost:8765/panel.html');
      return;
    }
    try {
      const estado = await api('estado');
      if (!estado.clave_lista) avisar('El panel todavía no tiene contraseña. Escríbela en DELIO_CLAVE, en el archivo de ajustes (mínimo 10 caracteres), y reinicia el servidor.');
      if (estado.dentro) {
        await mostrarPanel();
      } else {
        mostrarEntrada();
      }
    } catch (error) {
      avisar('No se pudo hablar con el servidor del panel. ' + error.message);
    }
  })();
})();
