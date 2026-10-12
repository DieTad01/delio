"""analisis.py — las cuentas del negocio: márgenes y probabilidades

Aquí no hay inteligencia artificial ni nada oculto: son sumas, divisiones y un poco
de probabilidad, con las mismas fórmulas cada vez. Todo lo que el panel dibuja sale
de este archivo, y cada cifra se puede revisar a mano.

MÁRGENES
    De cada cotización se calcula cuánto te cuesta hacerla, con los mismos factores
    que usa tu Cotizador (costo de tu hora, indirectos, financiamiento):
        margen = (lo que cobras − lo que te cuesta) ÷ lo que cobras
    Un margen de 40% quiere decir: de cada $100 que cobras, te quedan $40.

PROBABILIDADES
    La probabilidad de que una cotización se gane se estima con tu propia historia:
    de las que ya tuvieron desenlace, cuántas se ganaron. Con pocos casos ese
    porcentaje engaña (1 de 1 no es "100% seguro"), así que se suaviza: se parte de
    50% y cada caso real lo va moviendo. Entre más historia, más pesa lo tuyo.

    Con esas probabilidades se calcula el "valor esperado" de lo que tienes abierto
    (monto × probabilidad) y qué tan probable es llegar a tu meta del mes.
"""

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

import cotizador
import sitio
from almacen import listar

# Los factores del Cotizador, por si todavía no se ha importado nada.
BASE = {
    "apu_costo_hora": 120, "apu_fsr": 1.25, "apu_herramienta": 3, "apu_equipo_hora": 20,
    "apu_indirectos": 15, "apu_financiamiento": 2, "apu_utilidad": 12, "apu_cd_libre": 50,
    "gen_iva": 16, "gen_urgente": 25, "gen_express": 50, "gen_vigencia": 15,
    "fin_meta": 0, "fin_mensual": 1,
}
GANADA = {"aceptada", "entregada"}
PESO = 2   # cuántos "casos" vale la tasa general al estimar la de un servicio con poca historia


def _n(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _dia(texto):
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _pct(parte, total):
    return round(100 * parte / total, 1) if total else None


def _servicio(nombre):
    """Un solo nombre para "no sé cuál": lo que no es un servicio de la página va a "Otro"."""
    nombre = (nombre or "").strip()
    return "Otro" if not nombre or nombre.lower().startswith("otro") else nombre


# ---------- Márgenes ----------

def costo_de(partida, t):
    """Lo que te cuesta una partida de una cotización. Regresa (costo, es_estimado).

    Si la partida trae su desglose (horas y materiales) se calcula con él. Si no,
    se estima como un porcentaje de su precio (el ajuste "costo estimado sin desglose").
    """
    desglose = partida.get("cd") if isinstance(partida.get("cd"), dict) else {}
    estimado = not desglose or bool(desglose.get("est"))
    if estimado:
        directo = _n(partida.get("amount")) * t["apu_cd_libre"] / 100
    else:
        horas = max(0.0, _n(desglose.get("horas")))
        mano_de_obra = horas * t["apu_costo_hora"] * t["apu_fsr"]
        directo = (max(0.0, _n(desglose.get("mat"))) + mano_de_obra
                   + mano_de_obra * t["apu_herramienta"] / 100
                   + max(0.0, _n(desglose.get("eq"))) + horas * t["apu_equipo_hora"])
    indirectos = directo * t["apu_indirectos"] / 100
    financiamiento = (directo + indirectos) * t["apu_financiamiento"] / 100
    return directo + indirectos + financiamiento, estimado


def leer_cotizacion(c, t):
    """Convierte una cotización del Cotizador en las cifras que usa el panel."""
    partidas = [p for p in (c.get("items") or []) if isinstance(p, dict)]
    unico = sum(_n(p.get("amount")) for p in partidas if not p.get("rec"))
    recargo = {"urgente": t["gen_urgente"], "express": t["gen_express"]}.get(c.get("urgencia"), 0)
    urgencia = unico * recargo / 100
    descuento = (unico + urgencia) * min(100.0, max(0.0, _n(c.get("descuento")))) / 100
    # El descuento o recargo de la cotización se reparte entre sus pagos únicos.
    factor = (unico + urgencia - descuento) / unico if unico else 1.0

    precio = costo = cobro_unico = mensual = 0.0
    estimado, partes, mayor = False, [], (-1.0, "Otro")
    for p in partidas:
        nombre = cotizador.SERVICIOS.get(p.get("svc"), "Otro")
        cobro = _n(p.get("amount")) * (1.0 if p.get("rec") else factor)
        gasto, aproximado = costo_de(p, t)
        precio += cobro
        costo += gasto
        estimado = estimado or aproximado
        if p.get("rec"):
            mensual += cobro
        else:
            cobro_unico += cobro
        partes.append((nombre, cobro, gasto))
        mayor = max(mayor, (cobro, nombre))

    estado = c.get("estado") if c.get("estado") in ("pendiente", "aceptada", "entregada", "rechazada") else "pendiente"
    return {
        "id": c.get("id"), "folio": c.get("folio") or "", "cliente": c.get("cliente") or "",
        "asunto": c.get("asunto") or (partidas[0].get("title") if partidas else ""),
        "fecha": str(c.get("fecha") or "")[:10], "estado": estado,
        "situacion": "ganada" if estado in GANADA else "perdida" if estado == "rechazada" else "abierta",
        "servicio": mayor[1], "partes": partes,
        "precio": round(precio, 2), "costo": round(costo, 2), "utilidad": round(precio - costo, 2),
        "margen": _pct(precio - costo, precio), "estimado": estimado,
        "unico": round(cobro_unico, 2), "mensual": round(mensual, 2),
    }


# ---------- Lo que ha entrado ----------

def _meses_entre(inicio, fin):
    """Los meses "2026-09", "2026-10"… desde el de `inicio` hasta el de `fin`."""
    anio, mes = inicio.year, inicio.month
    while (anio, mes) <= (fin.year, fin.month):
        yield f"{anio}-{mes:02d}"
        anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def libro(crudo, cotizaciones, ingresos_panel, t, hoy):
    """Todos los ingresos y gastos, vengan de donde vengan, como renglones sueltos.

    Sigue las reglas del Cotizador: una cotización cuenta como ingreso cuando se
    entrega (o cuando se registra cada pago, si tiene plan de pagos), y un cliente
    de mensualidad cuenta cada mes mientras siga vigente.
    """
    entradas, salidas = [], []
    iva = 1 + t["gen_iva"] / 100
    por_id = {c["id"]: c for c in cotizaciones}

    for c in crudo["cotizaciones"]:
        leida = por_id.get(c.get("id"))
        divisor = iva if c.get("factura") else 1.0
        pagos = c.get("pagosHechos") if isinstance(c.get("pagosHechos"), dict) else {}
        if pagos:
            for pago in pagos.values():
                if isinstance(pago, dict) and _dia(pago.get("fecha")):
                    entradas.append((str(pago["fecha"])[:10], _n(pago.get("monto")) / divisor,
                                     leida["servicio"], c.get("cliente") or ""))
        elif c.get("estado") == "entregada" and _dia(c.get("entregada")) and _n(c.get("total")) > 0:
            entradas.append((str(c["entregada"])[:10], _n(c["total"]) / divisor, leida["servicio"], c.get("cliente") or ""))
        if c.get("estado") == "entregada" and _dia(c.get("entregada")):
            compra = sum(_n((p.get("cd") or {}).get("compra")) for p in (c.get("items") or [])
                         if isinstance(p, dict) and isinstance(p.get("cd"), dict))
            if compra > 0:
                salidas.append((str(c["entregada"])[:10], compra))

    if t["fin_mensual"]:
        con_cliente = {cl.get("quoteId") for cl in crudo["clientes"]}
        for cl in crudo["clientes"]:
            inicio = _dia(cl.get("inicio"))
            if _n(cl.get("mensual")) <= 0 or not inicio:
                continue
            limite = min(d for d in (hoy, _dia(cl.get("vence")), _dia((cl.get("baja") or {}).get("fecha"))) if d)
            servicio = por_id[cl["quoteId"]]["servicio"] if cl.get("quoteId") in por_id else "Otro"
            for mes in _meses_entre(inicio, limite):
                entradas.append((f"{mes}-01", _n(cl["mensual"]), servicio, cl.get("nombre") or ""))
        # Mensualidades entregadas que todavía no pasaste a tu lista de clientes.
        for c in crudo["cotizaciones"]:
            entrega = _dia(c.get("entregada"))
            if c.get("estado") != "entregada" or not entrega or _n(c.get("mensual")) <= 0 or c.get("id") in con_cliente:
                continue
            renovacion = c.get("renovacion") or {}
            limite = min(hoy, _dia(renovacion.get("fecha")) or hoy) if renovacion.get("estado") == "no" else hoy
            for mes in _meses_entre(entrega, limite):
                entradas.append((f"{mes}-01", _n(c["mensual"]) / (iva if c.get("factura") else 1.0),
                                 por_id[c["id"]]["servicio"], c.get("cliente") or ""))

    for m in crudo["movimientos"]:
        if not _dia(m.get("fecha")) or _n(m.get("monto")) <= 0:
            continue
        if m.get("tipo") == "gasto":
            salidas.append((str(m["fecha"])[:10], _n(m["monto"])))
        else:
            entradas.append((str(m["fecha"])[:10], _n(m["monto"]), "Otro", m.get("cliente") or ""))

    for i in ingresos_panel:
        entradas.append((i["fecha"], _n(i["monto"]), _servicio(i["servicio"]), i["cliente"]))
    return entradas, salidas


# ---------- Probabilidades ----------

def probabilidad(ganadas, cerradas, general=None):
    """Probabilidad suavizada de ganar, de 0 a 1.

    Sin `general`:  (ganadas + 1) ÷ (cerradas + 2). Con cero casos da 50%; con 4 de 4, 83%.
    Con `general`:  la historia de un servicio se mezcla con la tasa de todo el negocio,
                    que pesa como PESO casos. Así un servicio con 1 solo caso no salta a 0% o 100%.
    """
    if general is None:
        return (ganadas + 1) / (cerradas + 2)
    return (ganadas + PESO * general) / (cerradas + PESO)


def confianza(casos):
    return "baja" if casos < 5 else "media" if casos < 20 else "alta"


def _historia(tratos):
    """De una lista de (servicio, situación) saca la probabilidad general y la de cada servicio."""
    cuenta = defaultdict(lambda: [0, 0])   # servicio -> [ganadas, cerradas]
    for servicio, situacion in tratos:
        if situacion in ("ganada", "perdida"):
            cuenta[servicio][1] += 1
            cuenta[servicio][0] += situacion == "ganada"
    ganadas = sum(g for g, _ in cuenta.values())
    cerradas = sum(c for _, c in cuenta.values())
    general = probabilidad(ganadas, cerradas)

    def de(servicio):
        g, c = cuenta.get(servicio, (0, 0))
        return probabilidad(g, c, general), c

    return {"ganadas": ganadas, "cerradas": cerradas, "p": general, "de": de}


def probabilidad_de_juntar(falta, tratos):
    """Probabilidad de que lo que se gane de `tratos` sume al menos `falta`.

    tratos: lista de (monto, probabilidad). Cada trato se gana o no, sin depender de
    los demás. Se lleva la cuenta de todas las sumas posibles y qué tan probable es
    cada una; al final se suman las que alcanzan.
    """
    if falta <= 0:
        return 1.0
    sumas = {0: 1.0}
    for monto, p in tratos:
        nuevas = defaultdict(float)
        for suma, probable in sumas.items():
            nuevas[suma] += probable * (1 - p)
            nuevas[min(falta, suma + round(monto))] += probable * p   # pasar de la meta es lo mismo que llegar
        sumas = nuevas
    return sum(probable for suma, probable in sumas.items() if suma >= falta)


# ---------- Todo junto ----------

def resumen(bd, visitas, hoy=None):
    hoy = hoy or date.today()
    crudo = cotizador.leer(bd)
    t = {**BASE, **{clave: _n(valor) for clave, valor in crudo["tarifas"].items() if clave in BASE}}
    solicitudes = listar(bd, "solicitudes", 5000)
    ingresos_panel = listar(bd, "ingresos", 5000)
    cotizaciones = [leer_cotizacion(c, t) for c in crudo["cotizaciones"]]
    hay_cotizador = bool(crudo["importacion"])

    # --- probabilidades de cierre
    cierre = _historia((c["servicio"], c["situacion"]) for c in cotizaciones)
    cierre_solicitudes = _historia(
        (_servicio(s["servicio"]), {"ganada": "ganada", "perdida": "perdida"}.get(s["estado"], "abierta"))
        for s in solicitudes)

    # --- lo que cuesta en promedio un trabajo ganado, por servicio (para estimar solicitudes sin monto)
    montos = defaultdict(list)
    for c in cotizaciones:
        if c["situacion"] == "ganada" and (c["unico"] or c["mensual"]):
            montos[c["servicio"]].append(c["unico"] or c["mensual"])
    todos = [m for lista in montos.values() for m in lista]

    def ticket(servicio):
        lista = montos.get(servicio) or todos
        return sum(lista) / len(lista) if lista else None

    # --- lo que está por cerrarse
    tratos = []
    for c in cotizaciones:
        if c["situacion"] != "abierta":
            continue
        p, casos = cierre["de"](c["servicio"])
        dias = (hoy - (_dia(c["fecha"]) or hoy)).days
        monto = c["unico"] or c["mensual"]
        tratos.append({
            "tipo": "cotización", "titulo": " · ".join(x for x in (c["folio"], c["cliente"]) if x),
            "detalle": c["asunto"], "servicio": c["servicio"], "monto": round(monto, 2), "monto_estimado": False,
            "probabilidad": round(100 * p), "confianza": confianza(casos), "esperado": round(monto * p, 2),
            "dias": dias, "vencida": dias > t["gen_vigencia"],
        })
    sin_atender = []
    for s in solicitudes:
        creada = _dia(s["creada"]) or hoy
        if s["estado"] == "nueva":
            sin_atender.append({"id": s["id"], "dias": (hoy - creada).days})
        # Una solicitud ya cotizada debe estar en el Cotizador: no se cuenta dos veces.
        if s["estado"] == "nueva" or (s["estado"] == "cotizada" and not hay_cotizador):
            servicio = _servicio(s["servicio"])
            p, casos = cierre_solicitudes["de"](servicio)
            monto = ticket(servicio)
            tratos.append({
                "tipo": "solicitud", "titulo": f"Solicitud {s['id']}" + (f" · {s['negocio']}" if s["negocio"] else ""),
                "detalle": "", "servicio": servicio, "monto": round(monto, 2) if monto else None,
                "monto_estimado": True, "probabilidad": round(100 * p), "confianza": confianza(casos),
                "esperado": round(monto * p, 2) if monto else None, "dias": (hoy - creada).days, "vencida": False,
            })
    tratos.sort(key=lambda trato: -(trato["esperado"] or 0))
    con_monto = [trato for trato in tratos if trato["monto"]]

    # --- ingresos y gastos, y la meta del mes
    entradas, salidas = libro(crudo, cotizaciones, ingresos_panel, t, hoy)
    por_mes, gastos_mes, por_servicio_ingreso = defaultdict(float), defaultdict(float), defaultdict(float)
    for fecha, monto, servicio, _cliente in entradas:
        por_mes[fecha[:7]] += monto
        por_servicio_ingreso[servicio] += monto
    for fecha, monto in salidas:
        gastos_mes[fecha[:7]] += monto

    este_mes = hoy.strftime("%Y-%m")
    dias_del_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    cobrado = por_mes.get(este_mes, 0.0)
    meta = t["fin_meta"]
    falta = max(0.0, meta - cobrado)
    esperado = sum(trato["esperado"] for trato in con_monto)
    por_juntar = [(trato["monto"], trato["probabilidad"] / 100) for trato in con_monto]
    seis_meses = list(_meses_entre((hoy.replace(day=1) - timedelta(days=150)).replace(day=1), hoy))[-6:]

    # --- márgenes (de lo que sí se vendió)
    vendidas = [c for c in cotizaciones if c["situacion"] == "ganada"]
    precio_total = sum(c["precio"] for c in vendidas)
    costo_total = sum(c["costo"] for c in vendidas)
    margen_servicio = defaultdict(lambda: [0.0, 0.0])
    for c in vendidas:
        for nombre, cobro, gasto in c["partes"]:
            margen_servicio[nombre][0] += cobro
            margen_servicio[nombre][1] += gasto
    sobre_costo = t["apu_utilidad"]   # tu utilidad objetivo, como la escribes en el Cotizador

    # --- embudo de los últimos 30 días
    desde = hoy - timedelta(days=29)
    reciente = lambda texto: desde <= (_dia(texto) or date.min) <= hoy   # noqa: E731
    recientes = [c for c in cotizaciones if reciente(c["fecha"])]
    embudo = [
        {"paso": "Visitas a la página", "cantidad": sum(d["vistas"] for d in visitas.get("por_dia", []) if reciente(d["fecha"]))},
        {"paso": "Abrieron un servicio", "cantidad": sum(i["veces"] for i in visitas.get("interes", []))},
        {"paso": "Pidieron cotización en la página", "cantidad": sum(1 for s in solicitudes if reciente(s["creada"]))},
        {"paso": "Cotizaciones hechas", "cantidad": len(recientes)},
        {"paso": "Cotizaciones ganadas", "cantidad": sum(1 for c in recientes if c["situacion"] == "ganada")},
    ]

    # --- una fila por servicio: primero los de la página, en su orden
    nombres = sitio.servicios()
    interes = defaultdict(int)
    for dato in visitas.get("interes", []):
        interes[nombres.get(dato["servicio"], "Otro")] += dato["veces"]
    orden = list(nombres.values())
    vistos = {c["servicio"] for c in cotizaciones} | {_servicio(s["servicio"]) for s in solicitudes} | set(por_servicio_ingreso)
    orden += sorted(vistos - set(orden))
    por_servicio = []
    for nombre in orden:
        suyas = [c for c in cotizaciones if c["servicio"] == nombre]
        p, casos = cierre["de"](nombre)
        cobro, gasto = margen_servicio.get(nombre, (0.0, 0.0))
        por_servicio.append({
            "servicio": nombre, "interes": interes.get(nombre, 0),
            "solicitudes": sum(1 for s in solicitudes if _servicio(s["servicio"]) == nombre),
            "cotizaciones": len(suyas),
            "ganadas": sum(1 for c in suyas if c["situacion"] == "ganada"),
            "perdidas": sum(1 for c in suyas if c["situacion"] == "perdida"),
            "abiertas": sum(1 for c in suyas if c["situacion"] == "abierta"),
            "probabilidad": round(100 * p), "casos": casos, "confianza": confianza(casos),
            "vendido": round(cobro, 2), "costo": round(gasto, 2), "margen": _pct(cobro - gasto, cobro),
            "ingresos": round(por_servicio_ingreso.get(nombre, 0.0), 2),
        })

    # --- mensualidades y satisfacción (vienen de la lista de clientes del Cotizador)
    mensualidades = []
    opiniones = []
    for cl in crudo["clientes"]:
        opiniones += [o for o in (cl.get("opiniones") or []) if isinstance(o, dict)]
        vence = _dia(cl.get("vence"))
        if _n(cl.get("mensual")) > 0 and not cl.get("baja") and (not vence or vence >= hoy):
            mensualidades.append({"cliente": cl.get("nombre") or "", "servicio": cl.get("servicio") or "",
                                  "mensual": _n(cl["mensual"]), "vence": cl.get("vence") or "",
                                  "dias": (vence - hoy).days if vence else None})
    notas_nps = [_n(o.get("nps")) for o in opiniones if o.get("nps") is not None]
    estrellas = [_n(o.get("estrellas")) for o in opiniones if o.get("estrellas")]
    satisfaccion = None
    if opiniones:
        promotores = sum(1 for nota in notas_nps if nota >= 9)
        detractores = sum(1 for nota in notas_nps if nota <= 6)
        satisfaccion = {
            "respuestas": len(opiniones),
            "estrellas": round(sum(estrellas) / len(estrellas), 1) if estrellas else None,
            "nps": round(100 * (promotores - detractores) / len(notas_nps)) if notas_nps else None,
        }

    return {
        "hay_cotizador": hay_cotizador,
        "importacion": crudo["importacion"],
        "meta": {
            "meta": round(meta, 2), "cobrado": round(cobrado, 2), "falta": round(falta, 2),
            "gastos": round(gastos_mes.get(este_mes, 0.0), 2),
            "por_cerrar": round(sum(trato["monto"] for trato in con_monto), 2),
            "esperado": round(esperado, 2),
            "probabilidad": round(100 * probabilidad_de_juntar(round(falta), por_juntar)) if meta > 0 else None,
            # Si el resto del mes entrara al mismo ritmo que lo que va:
            "proyeccion": round(cobrado / hoy.day * dias_del_mes, 2),
            "dia": hoy.day, "dias_del_mes": dias_del_mes,
        },
        "meses": [{"mes": mes, "ingresos": round(por_mes.get(mes, 0.0), 2), "gastos": round(gastos_mes.get(mes, 0.0), 2)}
                  for mes in seis_meses],
        "embudo": embudo,
        "por_cerrar": tratos,
        "cierre": {
            "cotizaciones": {"ganadas": cierre["ganadas"], "cerradas": cierre["cerradas"],
                             "probabilidad": round(100 * cierre["p"]), "confianza": confianza(cierre["cerradas"])},
            "solicitudes": {"ganadas": cierre_solicitudes["ganadas"], "cerradas": cierre_solicitudes["cerradas"],
                            "probabilidad": round(100 * cierre_solicitudes["p"]),
                            "confianza": confianza(cierre_solicitudes["cerradas"])},
        },
        "margenes": {
            # 12% sobre el costo equivale a que te queden $10.7 de cada $100 cobrados.
            "objetivo": round(100 * sobre_costo / (100 + sobre_costo), 1),
            "objetivo_sobre_costo": sobre_costo,
            "vendido": round(precio_total, 2), "costo": round(costo_total, 2),
            "utilidad": round(precio_total - costo_total, 2), "margen": _pct(precio_total - costo_total, precio_total),
            "estimadas": sum(1 for c in vendidas if c["estimado"]), "cuantas": len(vendidas),
            "costo_estimado_pct": t["apu_cd_libre"],
            "cotizaciones": [{clave: c[clave] for clave in ("folio", "cliente", "asunto", "fecha", "estado", "servicio",
                                                           "precio", "costo", "utilidad", "margen", "estimado", "mensual")}
                             for c in sorted(cotizaciones, key=lambda c: c["fecha"], reverse=True)],
        },
        "por_servicio": por_servicio,
        "mensualidades": {"total": round(sum(m["mensual"] for m in mensualidades), 2), "clientes": mensualidades},
        "satisfaccion": satisfaccion,
        "sin_atender": sorted(sin_atender, key=lambda s: -s["dias"]),
    }
