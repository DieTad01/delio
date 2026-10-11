# Sitio de Delio

Página principal de una sola pantalla larga (portada, servicios, proyectos, qué incluye cada servicio y contacto por WhatsApp) más el aviso de privacidad. No usa base de datos ni programas en el servidor: son archivos que Nginx entrega tal cual.

## Una carpeta por tecnología

| Tecnología | Dónde está | Para qué sirve |
|---|---|---|
| HTML | `index.html`, `aviso-de-privacidad.html` | El contenido. Van en la raíz porque ahí los busca el servidor al entrar al dominio. |
| CSS | `css/` | La apariencia. |
| JavaScript | `js/` | El comportamiento. |
| Imágenes | `img/` | El logotipo y el símbolo en SVG (el símbolo en dos colores: tinta para el día, `-caqui` para la noche), el ícono de la pestaña y las imágenes PNG para compartir el enlace. |
| Nginx | `nginx/` | La configuración del servidor. No es parte de la página; se copia a `/etc/nginx/`. |
| Para buscadores | `robots.txt`, `sitemap.xml` | Le dicen a Google y a Bing que pueden leer el sitio y qué páginas tiene. |
| Python | `logo/` | El script que dibuja los logos, y los logos en SVG y PNG. Solo se usa en tu PC; el servidor no necesita Python. |

El HTML no trae estilos ni scripts escritos adentro: solo enlaza a los archivos de `css/` y `js/`.

### CSS

- `base.css`: colores, tipografía y medidas, definidos como variables en `:root`. Para cambiar el color de fondo o la letra de todo el sitio se toca solo aquí.
- `componentes.css`: las piezas que se repiten (botones, carrusel, mosaicos, carteles, filas, formulario).
- `secciones.css`: cómo se acomodan esas piezas en la página y los ajustes para celular.
- `documento.css`: el formato de las páginas de puro texto, como el aviso de privacidad.

### JavaScript

- `arranque.js`: marca la página como "con JavaScript" y, si la persona ya había elegido el modo nocturno, lo aplica antes de que se pinte.
- `ondas.js`: dibuja la onda de la portada y las señales de los mosaicos.
- `logo.js`: dibuja el logo de la portada con la onda en movimiento. Usa los puntos de `logo-puntos.js`, que no se edita a mano: lo escribe `logo/generar_logo.py`.
- `carrusel.js`: hace que los carruseles de servicios y proyectos no tengan fin, se deslicen solos poco a poco y respondan a las flechas.
- `detalle.js`: el selector de "Qué incluye".
- `contacto.js`: arma el mensaje del formulario y abre WhatsApp.
- `tema.js`: el botón de modo nocturno. Pone o quita `data-tema="oscuro"` en `<html>` y recuerda la elección en el navegador de la persona.

Si JavaScript falla, la página sigue sirviendo: se ven todas las listas de "Qué incluye" una tras otra y el formulario manda el texto a WhatsApp de todos modos.

## Verlo en tu computadora

Doble clic en `index.html`. O, desde esta carpeta:

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

Si después de esto el dominio no abre, revisa que el firewall del VPS (o el del panel de tu proveedor) deje pasar los puertos 80 y 443.

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

- **Agregar un servicio:** en `index.html` son tres lugares: un `<li>` en el carrusel, una `<option>` y un `<article class="incluye">` en "Qué incluye", y una `<option>` en el formulario. La clave (por ejemplo `wifi`) tiene que ser la misma en el mosaico, la opción y el artículo.
- **Agregar un proyecto:** copia un `<li>` completo del carrusel de proyectos en `index.html` y cambia sus textos.
- **Cambiar la velocidad del logo animado:** el número `VUELTAS_POR_SEGUNDO` al inicio de `js/logo.js` (más bajo, más lento).
- **Cambiar la velocidad de las señales de los mosaicos:** los segundos de `animation: correr 7.5s` en `css/componentes.css` (más alto, más lento).
- **Cambiar la velocidad de los carruseles:** el número `VELOCIDAD` al inicio de `js/carrusel.js` (pixeles por segundo; más alto, más rápido). Para que un carrusel no avance solo, quítale el atributo `data-carrusel-auto` en `index.html`.
- **Cambiar la señal de un mosaico:** el atributo `data-onda`. Las disponibles están en `js/ondas.js`: `seno`, `am`, `amortiguada`, `cuadrada`, `triangular`, `sierra`, `escalera`, `pulsos`, `latido`.
- **Cambiar colores:** las variables de `css/base.css`. Hay dos juegos: el de `:root` (día) y el de `:root[data-tema="oscuro"]` (noche).
- **Cambiar el logo:** los SVG de `img/` salen de `generar_logo.py`, que está en la carpeta `logo/` junto con los PNG para usar fuera del sitio. Ahí se ajusta qué tan ondulado queda y, con `PASO`, cuántos puntos lleva cada letra (menos puntos, archivos más ligeros); después se copia `delio-logotipo-tinta.svg` a `img/logo-delio.svg`. El mismo script actualiza `js/logo-puntos.js`, que es lo que usa el logo animado de la portada.
