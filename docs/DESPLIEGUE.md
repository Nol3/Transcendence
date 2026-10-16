# Desplegar en un servidor propio

Guía para dejar el proyecto funcionando en un servidor con un dominio de verdad y HTTPS.
Está escrita para seguirse de arriba abajo, en la máquina que va a hacer de servidor.

---

## 0. Lo que hace falta antes de empezar

| Cosa | Dónde se consigue |
|---|---|
| Un dominio | Cualquier registrador. Da igual cuál: solo hay que poder tocar el DNS |
| Un servidor con Docker | Tu PC, o un VPS. Con Docker Engine y el plugin `docker compose` |
| El puerto 80 y el 443 abiertos | En el router (si es tu casa) o en el firewall del VPS |
| Una IP que no cambie | Si tu operador te da IP dinámica, hace falta un DDNS o un VPS |

**Si el servidor está en tu casa**: la IP pública cambia sola cada cierto tiempo. Con un
dominio dinámico (DuckDNS, No-IP…) el dominio apunta siempre a donde estés. Si no quieres
líos, un VPS pequeño cuesta poco y te quita ese problema y el de abrir puertos en el router.

---

## 1. El dominio

1. Compra el dominio.
2. En el DNS, crea un registro **A** que apunte a la IP del servidor:
   - Nombre: `@` (el dominio a secas) → la IP.
   - Nombre: `www` → la misma IP.
3. Espera a que propague (de minutos a unas horas). Se comprueba con:
   ```bash
   dig +short tudominio.com
   ```
   Si devuelve tu IP, ya está.

---

## 2. El código en el servidor

```bash
git clone https://github.com/Nol3/Transcendence.git
cd Transcendence
```

Si el servidor es Windows, instala Docker Desktop y trabaja desde WSL (Ubuntu). El
proyecto se desarrolló así.

---

## 3. Los secretos

```bash
cp backend/.env.production.example backend/.env
```

Y rellena el fichero. Lo mínimo:

- `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` y
  `PUBLIC_BASE_URL` con **tu** dominio.
- `DJANGO_SECRET_KEY` y `JWT_SECRET_KEY`: dos claves **distintas**, generadas en el
  servidor y que no se reutilizan de desarrollo:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- `DB_PASSWORD` con algo que no sea `transcendence`.
- `USE_VAULT=false` (en producción los secretos van en este fichero).
- `SECURE_HSTS_SECONDS=300` al principio: es el tiempo que el navegador de tus visitantes
  recuerda «solo HTTPS». Con un dominio nuevo conviene ir corto hasta comprobar que todo
  funciona; luego se sube a `31536000`.

El fichero `.env` no se sube a git (ya está ignorado), y no debería salir del servidor.

---

## 4. El certificado

```bash
sudo apt update && sudo apt install -y certbot
DOMINIO=tudominio.com EMAIL=tucorreo@example.com ./scripts/deploy.sh --certificado
```

Eso para nginx un momento, le pide a Let's Encrypt el certificado del dominio (certbot
comprueba que el dominio es tuyo usando el puerto 80), lo copia al sitio donde nginx lo
busca y levanta todo. Los certificados de Let's Encrypt duran 90 días; para renovarlos:

```bash
sudo certbot renew --quiet && ./scripts/deploy.sh
```

Y se puede dejar en el cron del servidor.

---

## 5. Arrancar (y actualizar)

```bash
./scripts/deploy.sh
```

Hace cuatro cosas: copia el certificado, trae los cambios del repositorio, reconstruye y
levanta con el overlay de producción, y espera a que todo esté sano.

Comandos útiles:

```bash
# Ver cómo va todo
docker compose -f compose.yaml -f compose.prod.yaml ps

# Los logs de un servicio
docker compose -f compose.yaml -f compose.prod.yaml logs -f backend

# Parar sin perder datos
docker compose -f compose.yaml -f compose.prod.yaml down

# Entrar al panel de administración
#   https://tudominio.com/admin/   (hace falta un superusuario, ver abajo)
docker compose -f compose.yaml -f compose.prod.yaml exec backend \
  python manage.py createsuperuser
```

En producción **solo nginx publica puertos** (el 80 y el 443). El backend, el frontend,
Postgres y Redis hablan entre ellos por la red interna de Docker: no son accesibles desde
fuera, y así debe quedarse.

---

## 6. Copias de seguridad

```bash
./scripts/backup.sh /mnt/disco-externo/transcendence
```

Guarda dos ficheros con la fecha: el volcado de la base de datos (comprimido) y los
ficheros subidos por los usuarios (avatares). En el cron, cada noche:

```cron
0 4 * * * cd /ruta/al/proyecto && ./scripts/backup.sh /mnt/disco-externo/transcendence >> /var/log/transcendence-backup.log 2>&1
```

### Restaurar

```bash
# La base de datos
gunzip -c backups/base-FECHA.sql.gz | docker compose -f compose.yaml -f compose.prod.yaml \
  exec -T postgres psql -U transcendence transcendence

# Los ficheros subidos
docker compose -f compose.yaml -f compose.prod.yaml exec -T backend \
  sh -c "cd /app/media && tar xzf -" < backups/media-FECHA.tar.gz
```

Una copia que vive en el mismo disco que el original no es una copia: llévala a otro sitio.

---

## 7. Lo que hay que saber del día a día

- **Las cuentas de prueba**: los tests automáticos crean cuentas (`e2e_...`, `juegos_...`).
  En un servidor de verdad no deberían existir, y en desarrollo llenan el ranking:
  ```bash
  python manage.py limpiar_prueba            # enseña lo que borraría
  python manage.py limpiar_prueba --borrar   # lo borra
  ```
- **La base de datos**: en producción se usa PostgreSQL (el overlay lo fuerza). SQLite vale
  para desarrollar, pero no aguanta varias escrituras a la vez.
- **Los avatares** viven en un volumen (`media_data`). Si algún día se borra ese volumen,
  se pierden: por eso están en la copia de seguridad.
- **El registro está abierto**: cualquiera puede crearse una cuenta. Si no lo quieres,
  hay que cerrarlo (todavía no hay interruptor para eso, es un cambio pequeño).

---

## 8. Cuando algo no va

| Síntoma | Por dónde empezar |
|---|---|
| El navegador avisa del certificado | El certificado no se copió: `./scripts/deploy.sh --certificado` |
| «Bad Gateway» (502) | Alguno de los servicios no está sano: `docker compose ... ps` y mira los logs del que falle |
| El registro da 429 | El limitador de anónimos: 60 peticiones por hora **por IP** (con `THROTTLE_ANON` se sube). El login tiene además su propio límite, 10 por minuto |
| La página sale sin estilos o el juego no arranca | La CSP: si has añadido un servicio externo al front (un CDN, una tipografía), hay que permitirlo en **los dos** sitios donde vive la política (`docker/nginx-app.conf` y `CONTENT_SECURITY_POLICY` en los settings). Hay un test que comprueba que las dos coinciden |
| El WebSocket no conecta | Tiene que ir por `wss://` (HTTPS). Comprueba que entras con `https://` |
| El admin da 403 al guardar | Falta el dominio en `CSRF_TRUSTED_ORIGINS` del `.env` |
| No llegan los correos de «olvidé mi contraseña» | Rellena `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en el `.env` |

---

## 9. Lo que queda pendiente en el proyecto

Para que no sorprenda. La lista viva y priorizada está en `docs/ROADMAP.md` (sección de la
auditoría del 16-10-2026); esto es lo que puede afectar al despliegue:

- **El WAF**: el borde usa la configuración de la imagen `owasp/modsecurity-crs:nginx`, sin
  afinar. Está pendiente decidir la buena (nivel de paranoia y umbral) y comprobarla de verdad
  con tráfico real. Los ajustes que se leen en `docker/nginx.conf` **no se aplican**: ese
  fichero no se monta.
- **Endurecer el contenedor**: el backend corre como root y las imágenes usan etiquetas
  flotantes (`:latest`, `nginx:alpine`), que un día traerán un cambio sin avisar.
- Las **señas del Mus** y los modos de **4 por parejas** de brisca y tute.
- El registro de mesas entre réplicas: solo importa si algún día se levanta más de un
  servidor de aplicaciones a la vez.
- Cerrar el registro si quieres invitaciones en vez de registro libre.
