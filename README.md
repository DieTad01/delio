# Sitio de Delio

Página principal de una sola pantalla larga (portada, servicios, proyectos, qué incluye cada servicio y contacto por WhatsApp) más el aviso de privacidad. La parte pública son archivos que Nginx entrega tal cual.

Además tiene un **panel privado** (`panel.html`): junta las solicitudes del formulario, las visitas y los datos de tu Cotizador, y te los enseña en gráficas con márgenes y probabilidades. No usa inteligencia artificial: son cuentas fijas que puedes revisar. El panel sí necesita un programa corriendo en el VPS; está en la carpeta `servidor/` y se explica en "El panel".

## Una carpeta por tecnología

| Tecnología | Dónde está | Para qué sirve |
|---|---|---|
| HTML | `index.html`, `aviso-de-privacidad.html`, `panel.html` | El contenido. Van en la raíz porque ahí los busca el servidor al entrar al dominio. |
| CSS | `css/` | La apariencia. |
| JavaScript | `js/` | El comportamiento. |
| Imágenes | `img/` | El logotipo y el símbolo en SVG (el símbolo en dos colores: tinta para el día, `-caqui` para la noche), el ícono de la pestaña y las imágenes PNG para compartir el enlace. |
| Nginx | `nginx/` | La configuración del servidor. No es parte de la página; se copia a `/etc/nginx/`. |
| Para buscadores | `robots.txt`, `sitemap.xml` | Le dicen a Google y a Bing que pueden leer el sitio y qué páginas tiene. |
| Python (panel) | `servidor/` | El programa del panel: recibe las solicitudes, guarda los datos y hace las cuentas. Es lo único que "corre" en el VPS. |
| Python (logo) | `logo/` | El script que dibuja los logos, y los logos en SVG y PNG. Solo se usa en tu PC. |

El HTML no trae estilos ni scripts escritos adentro: solo enlaza a los archivos de `css/` y `js/`.

### CSS

- `base.css`: colores, tipografía y medidas, definidos como variables en `:root`. Para cambiar el color de fondo o la letra de todo el sitio se toca solo aquí.
- `componentes.css`: las piezas que se repiten (botones, carrusel, mosaicos, carteles, filas, formulario).
- `secciones.css`: cómo se acomodan esas piezas en la página y los ajustes para celular.
- `documento.css`: el formato de las páginas de puro texto, como el aviso de privacidad.
- `panel.css`: lo propio del panel (las cifras, las gráficas de barras y columnas, y las listas).

### JavaScript

- `arranque.js`: marca la página como "con JavaScript" y, si la persona ya había elegido el modo nocturno, lo aplica antes de que se pinte.
- `ondas.js`: dibuja la onda de la portada y las señales de los mosaicos.
- `logo.js`: dibuja el logo de la portada con la onda en movimiento. Usa los puntos de `logo-puntos.js`, que no se edita a mano: lo escribe `logo/generar_logo.py`.
- `carrusel.js`: hace que los carruseles de servicios y proyectos no tengan fin, se deslicen solos poco a poco y respondan a las flechas.
- `detalle.js`: el selector de "Qué incluye".
- `contacto.js`: arma el mensaje del formulario, abre WhatsApp y manda una copia de la solicitud al panel.
- `panel.js`: todo el panel privado. Pide los datos y las cuentas al servidor y los dibuja.
- `tema.js`: el botón de modo nocturno. Pone o quita `data-tema="oscuro"` en `<html>` y recuerda la elección en el navegador de la persona.

Si JavaScript falla, la página sigue sirviendo: se ven todas las listas de "Qué incluye" una tras otra y el formulario manda el texto a WhatsApp de todos modos.

## Verlo en tu computadora

Doble clic en `index.html` (el panel no funciona así: ve "Probarlo en tu PC" más abajo). O, desde esta carpeta:

```bash
python -m http.server 4173
```

y abre `http://localhost:4173`.

## Antes de publicar, revisa esto

1. **Teléfono y correo.** Quedan a la vista de cualquiera. En `index.html` busca `524793255948` y `dietadhdez@gmail.com` y cámbialos si quieres usar otros.
2. **Proyectos.** Los cuatro carteles nombran a SuperConta, MII, Diego Rodríguez Autos y PBIT. Confirma que el texto de cada uno es correcto.
3. **Condiciones.** Debajo del formulario dice 15 días de vigencia, 30% de anticipo y 30 días de garantía. Salen de tu cotizador; si cambian allá, cámbialas aquí.
4. **Aviso de privacidad.** En `aviso-de-privacidad.html` el domicilio del responsable dice solo "León, Guanajuato", a propósito: es un domicilio particular y no se publica. La ley pide "identidad y domicilio"; si algún día tienes un domicilio de negocio (local, oficina o coworking), ponlo ahí. Es un texto base, no asesoría legal.
5. **Dominio.** Ya está puesto `delioph.tech` en `nginx/delio.conf` y en el `<head>` de las páginas, en `robots.txt` y en `sitemap.xml`. Si algún día cambia, busca `delioph.tech` en toda la carpeta.

## Subirlo al VPS

Estos pasos son para Debian. No se han probado en tu servidor; si algo no coincide, el mensaje de error casi siempre dice qué falta.

Si entras al VPS como `root`, escribe los comandos sin `sudo` (en un Debian recién instalado `sudo` puede no existir).

**1. Apunta el dominio.** En el panel donde compraste el dominio crea dos registros tipo A, `@` y `www`, con la IP del VPS. El dominio es `delioph.tech`.

**2. Sube el proyecto a GitHub** (en tu PC, dentro de esta carpeta). Primero crea en github.com un repositorio vacío llamado `delio`, sin README, y cambia `TU_USUARIO` por el tuyo:

```bash
git init -b main
```

```bash
git add . && git commit -m "Sitio de Delio"
```

```bash
git remote add origin https://github.com/TU_USUARIO/delio.git
```

```bash
git push -u origin main
```

**3. Instala Nginx y Git** (en el VPS):

```bash
sudo apt update && sudo apt install -y nginx git
```

**4. Baja el proyecto donde Nginx lo va a leer** (en el VPS):

```bash
sudo git clone https://github.com/TU_USUARIO/delio.git /var/www/delio
```

Si el repositorio es privado, GitHub pide usuario y un token de acceso (no la contraseña de la cuenta). La carpeta `.git` y la carpeta `logo/` quedan dentro de `/var/www/delio`, pero la configuración de Nginx no las entrega a nadie.

**5. Activa la configuración:**

```bash
sudo cp /var/www/delio/nginx/delio.conf /etc/nginx/sites-available/delio
```

```bash
sudo ln -s /etc/nginx/sites-available/delio /etc/nginx/sites-enabled/delio
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

`nginx -t` revisa que el archivo no tenga errores antes de aplicarlo. Si marca error, no se aplica nada y el sitio anterior sigue funcionando.

**6. Activa HTTPS** (certificado gratuito de Let's Encrypt):

```bash
sudo apt install -y certbot python3-certbot-nginx
```

```bash
sudo certbot --nginx -d delioph.tech -d www.delioph.tech
```

Certbot edita la configuración por ti para agregar el puerto 443 y renueva el certificado solo.

**7. Activa HTTP/2** (opcional, para que cargue más rápido). Con HTTP/2 el navegador pide todos los archivos por una sola conexión en vez de hacer fila. Abre la configuración que Certbot acaba de editar:

```bash
sudo nano /etc/nginx/sites-available/delio
```

En las líneas que dicen `listen 443 ssl` y `listen [::]:443 ssl` agrega la palabra `http2` antes del punto y coma (queda `listen 443 ssl http2;`). Guarda y aplica:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Si después de esto el dominio no abre, revisa que el firewall del VPS (o el del panel de tu proveedor) deje pasar los puertos 80 y 443. El 8765 del panel **no** se abre: solo lo usa Nginx por dentro.

## El panel

Está en `https://delioph.tech/panel.html`. Para entrar pide tu contraseña. De arriba a abajo:

- **Tu mes:** lo cobrado contra tu meta, la probabilidad de llegar a ella y los ingresos de los últimos 6 meses.
- **Del visitante al cliente:** el embudo de los últimos 30 días: visitas, quién abrió un servicio, quién pidió cotización, cotizaciones hechas y ganadas.
- **Lo que está por cerrarse:** cotizaciones pendientes y solicitudes nuevas, cada una con su probabilidad de ganarse y su valor esperado. Y la probabilidad de cierre por servicio.
- **Márgenes:** de cada $100 que cobras, cuánto te cuesta y cuánto te queda, por servicio y por cotización, contra tu objetivo.
- **Solicitudes, Ingresos sueltos, Objetivos y notas, Visitas.**
- **Datos del Cotizador:** donde subes el archivo con tus cotizaciones.
- **Acceso:** sesiones abiertas, bitácora y respaldo.

### De dónde salen los números

No hay inteligencia artificial. Todo se calcula en `servidor/analisis.py` con fórmulas fijas; el mismo dato da siempre el mismo resultado.

**Margen.** Para cada cotización se calcula lo que te cuesta con los factores de tu propio Cotizador (el costo de tu hora, indirectos, financiamiento):

```
margen = (lo que cobras − lo que te cuesta) ÷ lo que cobras
```

Un margen de 40% significa que de cada $100 te quedan $40. Si una partida no trae desglose de horas y materiales, su costo se estima como un porcentaje del precio (el ajuste "Costo estimado sin desglose" del Cotizador) y el panel lo marca como "costo estimado". Tu objetivo sale de tu "Utilidad objetivo": 12% sobre el costo equivale a que te queden $10.70 de cada $100.

**Probabilidad de ganar una cotización.** Sale de tu historia: de las que ya se decidieron, cuántas ganaste. Con pocos casos ese porcentaje engaña, así que se suaviza:

```
probabilidad = (ganadas + 1) ÷ (cerradas + 2)
```

Sin historia da 50%; con 4 de 4 da 83%, no 100%. Para un servicio con poca historia, su resultado se mezcla con el de todo el negocio. El panel dice cuánta confianza merece cada número (baja con menos de 5 casos).

**Valor esperado.** Monto × probabilidad. Una cotización de $10,000 con 60% "vale" $6,000 al planear.

**Probabilidad de llegar a la meta.** Se toma lo que falta y lo que tienes abierto, y se calcula qué tan probable es que lo que ganes alcance. Supone que lo abierto se decide este mes y que cada trato es independiente. Si no tienes nada abierto, marca 0%: no adivina trabajo que todavía no existe.

**Lo cobrado.** Sigue las reglas del Cotizador: una cotización cuenta cuando la marcas entregada (o cada pago, si tiene plan de pagos), y un cliente de mensualidad cuenta cada mes mientras siga vigente. A eso se suman los "ingresos sueltos" que anotes en el panel.

### Traer los datos del Cotizador

Las cotizaciones se siguen haciendo en tu Cotizador (el artefacto de claude.ai). El panel recibe una copia en un archivo `.json` que se sube en la sección "Datos del Cotizador". Importar reemplaza lo anterior; los teléfonos y correos de clientes no se guardan.

El Cotizador todavía no tiene un botón para sacar ese archivo. Por ahora el archivo lo genera Claude leyendo el artefacto, y queda en `servidor/datos/cotizador.json` (esa carpeta no se sube a GitHub, porque trae nombres de tus clientes). Para actualizarlo, pídeselo a Claude, o pide que se le agregue al Cotizador un botón "Exportar para el panel".

El archivo trae también tus tarifas. De ahí salen la meta mensual (`fin_meta`), la utilidad objetivo (`apu_utilidad`) y los factores de costo (`apu_…`): si los cambias en el Cotizador, vuelve a importar.

### Cómo funciona

```
navegador  ──►  Nginx  ──►  archivos (html, css, js…)        lo público
                  │
                  └─ /api/ ─►  servidor/app.py  ──►  delio.db      tus datos
```

Nada sale de tu servidor hacia otra empresa. Los archivos de `servidor/`:

- `app.py`: las rutas (qué pasa con cada petición a `/api/…`).
- `almacen.py`: la base de datos, un solo archivo de SQLite.
- `acceso.py`: el control de acceso: contraseña, sesiones, frenos contra intentos repetidos y bitácora.
- `analisis.py`: las cuentas: márgenes, probabilidades, embudo y meta del mes. **Si quieres cambiar una fórmula, es aquí.**
- `cotizador.py`: recibe y guarda el archivo del Cotizador.
- `sitio.py`: lee los servicios directo de `index.html`, para no tener la lista en dos lugares.
- `visitas.py`: cuenta las visitas leyendo los registros de Nginx.
- `delio-panel.service`, `requirements.txt`: servicio de Debian y bibliotecas.
- `local.env`: tus ajustes en tu PC, con la contraseña. **No está en GitHub** (lo excluye `.gitignore`); en el VPS su equivalente es `/etc/delio/panel.env`.

### Probarlo en tu PC

```bash
pip install flask
```

Abre `servidor/local.env` y escribe tu contraseña en `DELIO_CLAVE=` (mínimo 10 caracteres). Luego:

```bash
python servidor/app.py
```

y abre `http://localhost:8765/panel.html`. Sube `servidor/datos/cotizador.json` en "Datos del Cotizador" para ver tus números. En tu PC la sección de Visitas sale vacía, porque no hay registros de Nginx. `servidor/local.env` y `servidor/datos/` están en `.gitignore`: no se suben a GitHub.

### Instalarlo en el VPS

Después de `git pull` (o de clonar), una sola vez:

**1. Python y un usuario sin privilegios para el panel:**

```bash
sudo apt install -y python3-venv
```

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin delio
```

**2. Las bibliotecas, en su propia carpeta** (un "venv": no se mezclan con el Python del sistema):

```bash
sudo python3 -m venv /opt/delio/venv
```

```bash
sudo /opt/delio/venv/bin/pip install -r /var/www/delio/servidor/requirements.txt
```

**3. Los ajustes: tu contraseña.** El archivo de ajustes no viaja por GitHub: se crea a mano en el VPS.

```bash
sudo mkdir -p /etc/delio && sudo touch /etc/delio/panel.env && sudo chmod 600 /etc/delio/panel.env
```

```bash
sudo nano /etc/delio/panel.env
```

Escribe estos tres renglones, con tu contraseña en el primero (mínimo 10 caracteres; letras, números y guiones, sin espacios ni comillas):

```
DELIO_CLAVE=
DELIO_DATOS=/var/lib/delio
DELIO_LOG=/var/log/nginx/delio.access.log*
```

El `chmod 600` hace que solo `root` pueda leer ese archivo: ni otros usuarios del VPS ni Nginx. Y como está fuera de `/var/www/`, no se puede pedir desde internet.

**4. Arráncalo como servicio:**

```bash
sudo cp /var/www/delio/servidor/delio-panel.service /etc/systemd/system/
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now delio-panel
```

```bash
sudo systemctl status delio-panel
```

Debe decir `active (running)`. Para comprobar que responde: `curl http://127.0.0.1:8765/api/estado`.

**5. Actualiza Nginx.** `nginx/delio.conf` ahora manda `/api/` al panel. Hay que copiarlo otra vez (pasos 5, 6 y 7 de "Subirlo al VPS").

**6. Sube tus datos.** Entra a `https://delioph.tech/panel.html` y en "Datos del Cotizador" sube el archivo `servidor/datos/cotizador.json` desde tu PC.

**Si algo falla**, el programa dice por qué aquí:

```bash
sudo journalctl -u delio-panel -n 50
```

**Cuando cambies algo en `servidor/`**, después del `git pull`:

```bash
sudo systemctl restart delio-panel
```

### Control de acceso

- **La contraseña** está escrita en el archivo de ajustes: `servidor/local.env` en tu PC (fuera de GitHub) y `/etc/delio/panel.env` en el VPS (solo lo lee `root`). Usa una frase larga que no uses en otro sitio, porque quien pueda leer ese archivo la ve.
- **Intentos fallidos:** tras 5, esa dirección IP espera 15 minutos.
- **Sesiones:** se cierran solas tras 12 horas sin uso, o a los 7 días. En la sección Acceso ves desde qué dispositivos hay sesión y puedes cerrar las demás.
- **Bitácora:** cada entrada, salida, intento fallido, bloqueo y descarga de respaldo queda anotado con fecha, IP y dispositivo. Si ves entradas que no son tuyas, cambia la contraseña.
- **Cambiar la contraseña:** edita `DELIO_CLAVE` en `/etc/delio/panel.env` y reinicia con `sudo systemctl restart delio-panel`. Todas las sesiones abiertas dejan de valer en ese momento.
- **El navegador también ayuda:** `nginx/delio.conf` manda una regla (`Content-Security-Policy`) que solo deja cargar archivos de tu propio sitio. Funciona porque el HTML no trae estilos ni scripts escritos adentro; si un día agregas algo de otro sitio (un mapa, una tipografía, un video), hay que permitirlo ahí o el navegador lo bloqueará.

### Solo información del negocio

El panel guarda y analiza datos del negocio, no de las personas, y nada sale de tu servidor:

- **De cada solicitud del formulario** se guarda nombre, negocio, teléfono o correo (si lo dejó), servicio y mensaje. Es lo mínimo para poder contestarle.
- **Del Cotizador** se guardan cotizaciones, clientes de mensualidad y tarifas. Los teléfonos y correos se quitan al importar.
- **Visitas:** se guardan solo los totales por día. Las direcciones IP se leen del registro de Nginx para contar y no se copian a la base.
- **El aviso de privacidad** describe esto. Si cambias qué se guarda, actualiza `aviso-de-privacidad.html`.

### Otros cuidados

- **Respaldo.** En la sección Acceso, "Descargar respaldo" baja todos los datos en un archivo. Hazlo de vez en cuando y guárdalo fuera del VPS; ese archivo sí trae nombres y contactos, cuídalo. (La base completa está en `/var/lib/delio/delio.db`.)
- **Los números son tan buenos como lo que capturas.** Si no marcas una cotización como rechazada, la probabilidad de cierre sale más alta de lo real. Si no pones el desglose de costos, el margen es una estimación.

## Para que la página aparezca en internet

Lo que ya trae el sitio:

- **Título y descripción** de cada página: es lo que Google muestra en sus resultados.
- **Dirección oficial** (`canonical`), para que la página no se cuente dos veces.
- **Tarjeta para compartir** (etiquetas Open Graph e `img/compartir.png`): el título, el texto y la imagen que salen al pegar el enlace en WhatsApp o Facebook.
- **Datos del negocio** en formato schema.org, dentro del `<head>` de `index.html`: nombre, teléfono, ciudad y servicios, para que Google entienda que es un negocio local.
- **`robots.txt` y `sitemap.xml`**.
- **Aviso de privacidad**, enlazado desde el pie y desde el formulario.

Lo que solo puedes hacer tú, ya con el sitio publicado y con HTTPS:

1. **Google Search Console** (search.google.com/search-console): agrega `delioph.tech`, verifica que es tuyo con el registro DNS que te da, y en "Sitemaps" envía `https://delioph.tech/sitemap.xml`. Sin este paso Google puede tardar semanas en encontrar la página.
2. **Perfil de Negocio de Google** (google.com/business): es lo que hace que salgas en Google Maps y en el recuadro de la derecha al buscar tu negocio. Para un negocio local pesa más que cualquier etiqueta. Pon ahí el enlace a la página. Al crearlo, indica que **no** tienes un local que los clientes visiten: así Google muestra solo tu zona de servicio (León) y no tu dirección.
3. **Bing Webmaster Tools** (bing.com/webmasters): puede importar todo desde Search Console.
4. **Enlaces hacia tu página:** ponla en tu WhatsApp Business, en tus redes y en la firma de tu correo. Los buscadores descubren y valoran un sitio por quién lo enlaza.
5. **Prueba la tarjeta para compartir:** pega el enlace en un chat de WhatsApp contigo mismo. Si no sale la imagen, revísala en developers.facebook.com/tools/debug.

Aparecer no es inmediato: después de enviar el sitemap, Google suele tardar de unos días a un par de semanas.

## Para actualizar el sitio después

En tu PC, guarda y sube los cambios:

```bash
git add . && git commit -m "Describe el cambio" && git push
```

En el VPS, bájalos:

```bash
cd /var/www/delio && sudo git pull
```

No hace falta reiniciar Nginx. Si no ves el cambio, recarga con Ctrl + F5: el navegador guarda CSS y JS durante una hora.

Si lo que cambió fue `nginx/delio.conf`, `git pull` no basta: ese archivo se usa desde `/etc/nginx/`. Repite el paso 5 (sin el `ln`, que ya existe) y luego los pasos 6 y 7, porque al copiarlo se pierden las líneas de HTTPS que Certbot había agregado. Certbot no pide un certificado nuevo: ofrece reinstalar el que ya tienes.

## Qué tan rápida es

La portada completa pesa unos 90 KB, y comprimida viaja en unos 32 KB: menos que una sola foto. No usa tipografías descargadas, ni bibliotecas, ni rastreadores. Lo que la mantiene así:

- **Compresión** (`gzip`) y **memoria del navegador** (`expires`) en `nginx/delio.conf`.
- **Los scripts llevan `defer`**: se descargan mientras la página se pinta, sin detenerla.
- **Un solo logo en la portada:** de noche no se descarga otra imagen; `js/logo.js` lo dibuja del color que toca.
- **Las animaciones se detienen** cuando salen de pantalla o la pestaña queda en segundo plano.

Para medirla ya publicada: pagespeed.web.dev. Ojo: la velocidad ayuda un poco a la posición en Google, pero no hace que te encuentre antes; eso depende del sitemap y de Search Console (ver arriba).

## Cambios comunes

- **Agregar un servicio:** (el panel lo toma solo de `index.html`) en `index.html` son tres lugares: un `<li>` en el carrusel, una `<option>` y un `<article class="incluye">` en "Qué incluye", y una `<option>` en el formulario. La clave (por ejemplo `wifi`) tiene que ser la misma en el mosaico, la opción y el artículo.
- **Agregar un proyecto:** copia un `<li>` completo del carrusel de proyectos en `index.html` y cambia sus textos.
- **Cambiar la velocidad del logo animado:** el número `VUELTAS_POR_SEGUNDO` al inicio de `js/logo.js` (más bajo, más lento).
- **Cambiar la velocidad de las señales de los mosaicos:** los segundos de `animation: correr 7.5s` en `css/componentes.css` (más alto, más lento).
- **Cambiar la velocidad de los carruseles:** el número `VELOCIDAD` al inicio de `js/carrusel.js` (pixeles por segundo; más alto, más rápido). Para que un carrusel no avance solo, quítale el atributo `data-carrusel-auto` en `index.html`.
- **Cambiar la señal de un mosaico:** el atributo `data-onda`. Las disponibles están en `js/ondas.js`: `seno`, `am`, `amortiguada`, `cuadrada`, `triangular`, `sierra`, `escalera`, `pulsos`, `latido`.
- **Cambiar colores:** las variables de `css/base.css`. Hay dos juegos: el de `:root` (día) y el de `:root[data-tema="oscuro"]` (noche).
- **Cambiar el logo:** los SVG de `img/` salen de `generar_logo.py`, que está en la carpeta `logo/` junto con los PNG para usar fuera del sitio. Ahí se ajusta qué tan ondulado queda y, con `PASO`, cuántos puntos lleva cada letra (menos puntos, archivos más ligeros); después se copia `delio-logotipo-tinta.svg` a `img/logo-delio.svg`. El mismo script actualiza `js/logo-puntos.js`, que es lo que usa el logo animado de la portada.
