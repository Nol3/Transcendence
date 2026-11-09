# Publicar el juego con tu dominio y Cloudflare

Todo lo de aquí se hace **en el servidor**, con el stack ya levantado (`scripts/deploy.sh`). Cloudflare
va delante: el navegador habla con Cloudflare, Cloudflare con tu servidor.

```
navegador ──HTTPS──▶ Cloudflare ──HTTPS──▶ tu servidor (nginx :443) ──▶ backend / frontend
```

Lo que el proyecto ya trae hecho para esto, y que no hay que tocar:

| Pieza | Dónde | Qué hace |
|---|---|---|
| IP real del visitante | `docker/waf.conf` | Acepta `CF-Connecting-IP` **solo** si viene de un rango de Cloudflare. Sin esto, todos los visitantes compartirían un mismo cubo del limitador (10 r/s, 1000/h por IP) y cuatro personas dejarían el sitio sin servicio. |
| Esquema real | `docker/waf.conf` | `CF-Visitor` reconstruye `https` aunque el origen reciba HTTP (túnel). Evita el bucle de `SECURE_SSL_REDIRECT`. |
| Certificado | `scripts/instalar-certificado.sh` | Instala el certificado de origen donde nginx lo lee (producción y desarrollo) y recarga el borde. |
| Hosts y CSRF | `.env` | `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL`. |
| WebSockets | `docker/waf.conf` | `Upgrade`/`Connection` y `proxy_read_timeout` de 1 h: las partidas no se cortan por inactividad. |

---

## 1. DNS

En Cloudflare → **DNS → Records**, dos registros `A` (o `AAAA` si tu servidor tiene IPv6):

| Tipo | Nombre | Contenido | Proxy |
|---|---|---|---|
| A | `@` (raíz) | IP pública del servidor | **Proxied** (nube naranja) |
| A | `www` | IP pública del servidor | **Proxied** |

La nube naranja es obligatoria: es lo que pone Cloudflare delante y emite el certificado del
lado del navegador. El registro tiene que estar en **Proxied**, no en «DNS only».

Comprueba desde fuera que el dominio ya resuelve a Cloudflare (`nslookup tudominio.com` debe dar
IPs de Cloudflare, no la tuya).

## 2. Certificado de origen y modo SSL

1. Cloudflare → **SSL/TLS → Overview** → modo **Full (strict)**.
   - *Flexible* deja el tramo Cloudflare→servidor en HTTP: el juego redirige a HTTPS y entra en
     bucle. *Full* acepta cualquier certificado; *Full (strict)* exige uno válido, que es lo que
     vamos a poner.
2. Cloudflare → **SSL/TLS → Origin Server → Create Certificate**: deja los nombres
   (`tudominio.com`, `*.tudominio.com`), 15 años, y copia el **certificado** y la **clave** a dos
   ficheros (`origen.pem` y `origen-key.pem`).
3. En el servidor:

```bash
./scripts/instalar-certificado.sh origen.pem origen-key.pem
./scripts/instalar-certificado.sh --ver      # comprueba qué hay puesto
```

El script valida que la clave corresponde al certificado **antes** de tocar nada, lo copia a
`./docker/ssl/` (lo que monta producción) y al volumen de desarrollo, y recarga nginx. Si el par
no cuadra, no instala y avisa: una clave que no encaja deja nginx sin arrancar y el sitio caído.

> `docker/ssl/` y `*.pem` están en `.gitignore`. La clave privada no se sube nunca al repositorio.

## 3. El `.env` del servidor

Un **solo** fichero, en la raíz del repositorio:

```bash
cp backend/.env.production.example .env
# rellena los CAMBIA_ESTO: dos claves distintas, la contraseña de Postgres y el correo
```

Lo leen las dos mitades: `docker compose` para sustituir `${...}` (incluida la contraseña de
Postgres) y el contenedor del backend para todo lo demás. No hace falta tocar `backend/.env`.

Estas cinco líneas son las que cambian (el resto, como en el ejemplo):

```ini
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com,localhost,127.0.0.1,backend
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com
CORS_ALLOWED_ORIGINS=https://tudominio.com,https://www.tudominio.com
FRONTEND_URL=https://tudominio.com
PUBLIC_BASE_URL=https://tudominio.com
```

- Sin `CSRF_TRUSTED_ORIGINS`, el login del admin y cualquier `POST` desde el dominio dan **403
  «CSRF verification failed»**. El esquema `https://` es obligatorio, no vale solo el host.
- `FRONTEND_URL` es el que va en el enlace del correo de «he olvidado mi contraseña»: si se queda
  en `localhost:4200`, el correo llega con un enlace que no funciona.
- `PUBLIC_BASE_URL` es el que aparece en el esquema OpenAPI de `/api/docs/`.

Después: `docker compose -f compose.yaml -f compose.prod.yaml up -d` (o `scripts/deploy.sh`).

## 4. Ajustes de Cloudflare que hay que dejar como se dice

En **Speed → Optimization**, todo esto **apagado**:

| Ajuste | Por qué |
|---|---|
| **Rocket Loader** | Reordena y difiere los `<script>`: rompe Angular, que arranca a mano. Pantalla en blanco. |
| **Auto Minify** (si aparece) | Ya minificamos en el build; volver a tocarlo puede romper el bundle. |
| **Email Obfuscation** | Reescribe correos del HTML con scripts; el juego no los usa y solo añade ruido. |
| **Bot Fight Mode** | Lanza retos JS a peticiones que no son un navegador normal: puede bloquear las llamadas a la API y el WebSocket. Si lo quieres, **crea una excepción para `/api/*` y `/ws/*`**. |

En **SSL/TLS → Edge Certificates**:

- **Always Use HTTPS: ON**.
- **HSTS**: actívalo **en un solo sitio**. Django ya manda `Strict-Transport-Security` (1 año). Si
  lo activas también en Cloudflare, la cabecera sale duplicada (feo, no roto). O lo dejas en
  Django, o pones en el `.env` `SECURE_HSTS_SECONDS=0` y lo gestiona Cloudflare.

## 5. Caché

Por defecto Cloudflare solo cachea estáticos por extensión, así que la API (JSON) no se cachea.
Aun así, si creas una regla «Cache Everything», **excluye**:

- `/api/*` (respuestas por usuario: perfil, historial, salas)
- `/ws/*` (WebSocket)
- `/admin/*`
- `/index.html`, `/ngsw.json`, `/ngsw-worker.js` (el service worker y su manifiesto **nunca** se
  cachean en el borde: si no, un despliegue nuevo no llega a los navegadores)

Los JS/CSS con hash sí pueden cachearse: su nombre cambia con cada build.

## 6. WebSockets

Cloudflare los soporta sin configuración extra (plan gratuito incluido). Hay dos cosas que sí
importan y ya están puestas en `waf.conf`:

- `proxy_set_header Upgrade $http_upgrade` y `Connection "upgrade"`.
- `proxy_read_timeout 3600s`: una partida con gente pensando no se corta por inactividad.

Para comprobarlo de verdad: entra, abre una sala y juega dos minutos. Si el WebSocket se cae, en
la consola del navegador se ve el cierre; en `docker compose logs -f nginx` se ve si Cloudflare
corta con 520/524.

## 7. Verificación después de publicar

```bash
# 1. El sitio responde por el dominio (y el certificado es de Cloudflare, no el autofirmado)
curl -sI https://tudominio.com/ | head -5

# 2. La API también
curl -s -o /dev/null -w '%{http_code}\n' https://tudominio.com/api/leaderboard/

# 3. Una sola cabecera HSTS (si sale dos veces, tienes HSTS en Cloudflare y en Django)
curl -sI https://tudominio.com/ | grep -ci strict-transport-security

# 4. El chat y el juego en tiempo real: en el navegador → F12 → Network → WS → estado 101
```

Y la prueba que de verdad importa: **registro → partida con otra persona → terminar**. Ahí se
ejercitan el login, el JWT, el WebSocket y la base de datos a la vez.

## 8. Si el servidor no tiene IP pública (CGNAT) o no quieres abrir puertos

Cloudflare Tunnel: la conexión la inicia tu servidor hacia Cloudflare, sin tocar el router.

1. Zero Trust → **Networks → Tunnels → Create a tunnel** (tipo Cloudflared) y copia el token.
2. En el `.env`: `TUNNEL_TOKEN=...`
3. En el túnel, **Public hostname**: `tudominio.com` → servicio `https://nginx:8443`, y activa
   **No TLS Verify** (dentro de la red de Docker el certificado es el autofirmado; el tramo
   público lo cifra Cloudflare).
4. Arranca con el perfil:

```bash
docker compose -f compose.yaml -f compose.prod.yaml --profile tunnel up -d
```

Con túnel, el modo SSL de Cloudflare puede quedarse en **Full** (sin *strict*): el tráfico llega
a nginx por HTTP y `CF-Visitor` ya reconstruye el `https` para que Django no redirija en bucle.

## 9. Cuando algo falla

| Síntoma | Causa habitual | Arreglo |
|---|---|---|
| **526** en Cloudflare | Certificado de origen inválido o ausente | `./scripts/instalar-certificado.sh --ver` y reinstalar el par |
| **522 / 524** | Cloudflare no llega al servidor / tarda más de 100 s | Puertos 80 y 443 abiertos en el router y en el firewall del servidor |
| **502** justo después de desplegar | nginx tiene cacheada la IP vieja del backend | `scripts/deploy.sh` ya recarga el borde; si no, `docker compose restart nginx` |
| Bucle de redirecciones | Modo SSL en *Flexible*, o `SECURE_PROXY_SSL_HEADER` sin llegar | Poner *Full (strict)*; comprobar `X-Forwarded-Proto` en `waf.conf` |
| **403 CSRF** al entrar | Falta `CSRF_TRUSTED_ORIGINS` con `https://` | Completar el `.env` y reiniciar backend |
| «Demasiadas peticiones» con poco tráfico | El limitador ve la IP de Cloudflare para todos | Comprobar que `waf.conf` tiene los `set_real_ip_from` y que nginx se **recreó** (`up -d --force-recreate nginx`: es una plantilla, `reload` no basta) |
| Pantalla en blanco | Rocket Loader activo | Apagarlo |
| WebSocket se cierra a los pocos minutos | Algún proxy recortando el tiempo de lectura | Revisar `proxy_read_timeout` y que no haya otro proxy delante |

## 10. Mantenimiento

- **Rangos de Cloudflare**: están escritos en `docker/waf.conf`. Cambian muy de vez en cuando; si
  Cloudflare publica una lista nueva en <https://www.cloudflare.com/ips/>, se actualiza ahí y se
  recrea nginx.
- **Renovación**: el certificado de origen de Cloudflare dura 15 años. Si algún día se usa
  Let's Encrypt en el origen, hay que renovarlo cada 90 días (el de origen, no).
- **Backups**: `scripts/backup.sh` y `scripts/restaurar.sh` funcionan igual con Cloudflare delante;
  no tocan la red.
