#!/usr/bin/env bash
# =============================================================
# instalar.sh — instala o actualiza delioph.tech (página + panel)
# en un VPS Debian 13 / 12 o Ubuntu 24.04 / 22.04 (Hostinger).
#
# Uso, como root en la terminal del VPS (hPanel → VPS → Terminal):
#   curl -fsSLo instalar.sh https://raw.githubusercontent.com/DieTad01/delio/main/deploy/instalar.sh && bash instalar.sh
#
# Se puede correr las veces que quieras (por ejemplo, para actualizar
# el sitio): no borra datos ni cambia la contraseña que ya exista.
# Si en el VPS ya hay otros sitios (como diegorodriguezautos.com),
# no los toca: este solo agrega el suyo.
# =============================================================
set -euo pipefail

DOMINIO="${DOMINIO:-delioph.tech}"
REPO="${REPO:-https://github.com/DieTad01/delio.git}"
RAMA="${RAMA:-main}"
DIR="${DIR:-/var/www/delio}"
USUARIO_APP="delio"                 # el panel corre con este usuario, sin privilegios
VENV="/opt/delio/venv"              # las bibliotecas de Python del panel
AJUSTES="/etc/delio/panel.env"      # la contraseña del panel (nunca en GitHub)
SERVICIO="delio-panel"
SITIO_NGINX="delio"

paso()  { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }
ok()    { printf '\033[1;32m✔ %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;31m! %s\033[0m\n' "$*"; }
falla() { aviso "$*"; exit 1; }
# Si algo falla de forma inesperada, decirlo (nunca detenerse en silencio)
trap 'aviso "Se detuvo inesperadamente en la línea $LINENO de $(basename "$0"). Copia todo lo de arriba y pídele ayuda a Claude."' ERR
hay_terminal() { [ -r /dev/tty ] && [ -w /dev/tty ] && { : </dev/tty; } 2>/dev/null; }

# Ningún comando lee del teclado salvo las preguntas (que usan /dev/tty).
exec </dev/null

# ---------- 0. Revisiones ----------
[ "$(id -u)" -eq 0 ] || falla "Corre este script como root (o con: sudo bash instalar.sh)."
# shellcheck disable=SC1091
. /etc/os-release
case "${ID:-}" in
  debian|ubuntu) ok "Sistema: ${PRETTY_NAME:-$ID}" ;;
  *) falla "Este instalador es para Debian o Ubuntu y tu VPS tiene: ${PRETTY_NAME:-desconocido}." ;;
esac
if command -v ss >/dev/null; then
  OCUPA_80="$(ss -ltnpH 'sport = :80' 2>/dev/null | grep -v nginx || true)"
  if [ -n "$OCUPA_80" ]; then
    aviso "El puerto 80 ya lo usa otro programa:"
    echo "$OCUPA_80"
    falla "Tu VPS parece tener una plantilla con panel (Apache, OpenLiteSpeed...). Este sitio necesita Nginx."
  fi
fi

# ---------- 1. Paquetes del sistema ----------
paso "1/8 Instalando paquetes (puede tardar unos minutos)"
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
apt-get update -qq
apt-get install -y -qq curl git nginx python3 python3-venv ufw certbot python3-certbot-nginx ca-certificates iproute2 >/dev/null
ok "Nginx, Python, Git y Certbot listos"

# ---------- 2. Código ----------
paso "2/8 Descargando el código (rama $RAMA)"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch -q origin "$RAMA"
  git -C "$DIR" checkout -q -B "$RAMA" "origin/$RAMA"
  ok "Código actualizado"
else
  mkdir -p "$(dirname "$DIR")"
  git clone -q --branch "$RAMA" "$REPO" "$DIR"
  ok "Código descargado en $DIR"
fi
ok "Versión: $(git -C "$DIR" log -1 --format='%h %s')"

# ---------- 3. El panel: usuario y bibliotecas ----------
paso "3/8 Programa del panel (Python)"
id "$USUARIO_APP" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$USUARIO_APP"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip >/dev/null
"$VENV/bin/pip" install -q -r "$DIR/servidor/requirements.txt" >/dev/null
ok "Usuario '$USUARIO_APP' (sin contraseña ni permisos) y bibliotecas en $VENV"

# ---------- 4. La contraseña del panel ----------
paso "4/8 Contraseña del panel ($AJUSTES)"
umask 077
mkdir -p "$(dirname "$AJUSTES")"
if [ ! -f "$AJUSTES" ]; then
  printf 'DELIO_CLAVE=\nDELIO_DATOS=/var/lib/delio\nDELIO_LOG=/var/log/nginx/delio.access.log*\n' > "$AJUSTES"
  ok "Archivo de ajustes creado"
else
  ok "El archivo de ajustes ya existía: se conserva"
fi
CLAVE_ACTUAL="$(sed -n 's/^DELIO_CLAVE=//p' "$AJUSTES" | head -1)"
if [ "${#CLAVE_ACTUAL}" -lt 10 ]; then
  if hay_terminal; then
    echo "Escribe la contraseña para entrar al panel (no se ve al escribirla)."
    echo "Mínimo 10 caracteres, sin espacios, comillas, \\ ni \$."
    while :; do
      read -rsp "  Contraseña: " CLAVE1 </dev/tty; echo
      read -rsp "  Repítela:   " CLAVE2 </dev/tty; echo
      if [ "${#CLAVE1}" -lt 10 ]; then aviso "Muy corta."
      elif [ "$CLAVE1" != "$CLAVE2" ]; then aviso "No coinciden."
      elif printf '%s' "$CLAVE1" | grep -q '[[:space:]"'\''\$]'; then aviso "Tiene espacios, comillas, \\ o \$."
      else break; fi
    done
    # Se reescribe el renglón sin usar sed, para que ningún carácter de la contraseña lo rompa.
    { printf 'DELIO_CLAVE=%s\n' "$CLAVE1"; grep -v '^DELIO_CLAVE=' "$AJUSTES" || true; } > "$AJUSTES.nuevo"
    mv "$AJUSTES.nuevo" "$AJUSTES"
    unset CLAVE1 CLAVE2
    ok "Contraseña guardada"
  else
    aviso "Sin terminal para preguntar: escribe tu contraseña con  nano $AJUSTES  (renglón DELIO_CLAVE) y luego  systemctl restart $SERVICIO"
  fi
fi
unset CLAVE_ACTUAL
chown root:root "$AJUSTES"
chmod 600 "$AJUSTES"   # solo root la puede leer; systemd se la pasa al panel al arrancarlo
umask 022
ok "Solo root puede leer $AJUSTES"

# ---------- 5. Arrancar el panel ----------
paso "5/8 Arrancando el panel (systemd)"
cp "$DIR/servidor/delio-panel.service" "/etc/systemd/system/$SERVICIO.service"
systemctl daemon-reload
systemctl enable "$SERVICIO" >/dev/null 2>&1
systemctl restart "$SERVICIO"
for _ in $(seq 1 15); do curl -fs -o /dev/null http://127.0.0.1:8765/api/estado && break; sleep 1; done
curl -fsS -o /dev/null http://127.0.0.1:8765/api/estado || { journalctl -u "$SERVICIO" -n 30 --no-pager || true; falla "El panel no respondió. Arriba están sus últimos mensajes."; }
ok "El panel responde en 127.0.0.1:8765 y arranca solo si el VPS se reinicia"

# ---------- 6. Nginx ----------
paso "6/8 Nginx (recibe el tráfico del dominio)"
cp "$DIR/nginx/delio.conf" "/etc/nginx/sites-available/$SITIO_NGINX"
# Si el servidor no tiene IPv6, se quita esa línea para que Nginx pueda arrancar
[ -e /proc/net/if_inet6 ] || sed -i '/listen \[::\]:80;/d' "/etc/nginx/sites-available/$SITIO_NGINX"
ln -sf "/etc/nginx/sites-available/$SITIO_NGINX" "/etc/nginx/sites-enabled/$SITIO_NGINX"
rm -f /etc/nginx/sites-enabled/default
nginx -t 2>/dev/null || { nginx -t; falla "La configuración de Nginx tiene un error."; }
systemctl enable --now nginx >/dev/null 2>&1
systemctl reload nginx
ok "Nginx listo"

# ---------- 7. Firewall ----------
paso "7/8 Firewall (solo SSH, HTTP y HTTPS)"
PUERTO_SSH="$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}' || true)"
if ufw allow "${PUERTO_SSH:-22}/tcp" >/dev/null 2>&1 && ufw allow 80/tcp >/dev/null 2>&1 \
   && ufw allow 443/tcp >/dev/null 2>&1 && ufw --force enable >/dev/null 2>&1; then
  ok "Abiertos: SSH (${PUERTO_SSH:-22}), 80 y 443. El panel (8765) queda cerrado hacia afuera"
else
  aviso "No se pudo activar el firewall ufw (se continúa). El panel solo escucha dentro del servidor, así que no queda expuesto."
fi

# ---------- 8. HTTPS ----------
paso "8/8 HTTPS con Let's Encrypt"
IP_VPS="$(curl -4fs --max-time 10 https://api.ipify.org || true)"
ip_de() { getent ahostsv4 "$1" 2>/dev/null | awk 'NR==1{print $1}' || true; }
IP_DOM="$(ip_de "$DOMINIO")"
IP_WWW="$(ip_de "www.$DOMINIO")"
if [ -n "$IP_VPS" ] && [ "$IP_DOM" = "$IP_VPS" ]; then
  DOMINIOS=(-d "$DOMINIO")
  [ "$IP_WWW" = "$IP_VPS" ] && DOMINIOS+=(-d "www.$DOMINIO") || aviso "www.$DOMINIO aún no apunta a este VPS; el certificado será solo para $DOMINIO (vuelve a correr el script cuando apunte)."
  CORREO=""
  if hay_terminal && [ ! -d /etc/letsencrypt/accounts ]; then
    read -rp "  Correo para avisos del certificado (Enter para omitir): " CORREO </dev/tty
  fi
  if [ -n "$CORREO" ]; then OPC_CORREO=(-m "$CORREO" --no-eff-email); else OPC_CORREO=(--register-unsafely-without-email); fi
  # --keep-until-expiring: si ya hay certificado, solo lo vuelve a poner en la configuración de Nginx
  if certbot --nginx "${DOMINIOS[@]}" --redirect --agree-tos --non-interactive --keep-until-expiring "${OPC_CORREO[@]}"; then
    ok "HTTPS activo y se renueva solo"
  else
    aviso "Certbot falló. Revisa que el dominio apunte a $IP_VPS y vuelve a correr el script."
  fi
else
  aviso "El dominio aún no apunta a este VPS (dominio: ${IP_DOM:-sin registro}, VPS: ${IP_VPS:-desconocida})."
  echo "  En hPanel → Dominios → $DOMINIO → DNS: registros A de '@' y 'www' con valor ${IP_VPS:-<IP del VPS>}."
  echo "  Cuando propague (minutos a horas), vuelve a correr: bash instalar.sh"
fi

# ---------- Resumen ----------
printf '\n\033[1;32m===== Listo =====\033[0m\n'
echo "  Página:       https://$DOMINIO   (o http://${IP_VPS:-IP-del-VPS} mientras propaga el DNS)"
echo "  Panel:        https://$DOMINIO/panel.html   (la contraseña sale de $AJUSTES)"
echo "  Código:       $DIR   ·   Datos del panel: /var/lib/delio"
echo "  Ver errores:  journalctl -u $SERVICIO -n 50"
echo "  Actualizar:   sube los cambios a GitHub y vuelve a correr  bash instalar.sh"
