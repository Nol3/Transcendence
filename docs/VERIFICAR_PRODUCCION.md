# Qué comprobar en producción

Lista para repasar **en el servidor real**, de lo que rompe la experiencia a lo que solo molesta. No
sustituye a los tests: cubre lo que los tests no pueden ver (red, TLS, DNS, un móvil de verdad).

## 1. Lo que deja la web inservible si falla

- [ ] **TLS y redirección**: `https://tudominio/` carga sin aviso de certificado y `http://` redirige a
      `https://`. Comprobar la cadena completa (Cloudflare → origen) con `curl -I`.
- [ ] **WebSocket a través de Cloudflare**: entrar en una sala con dos dispositivos y jugar un turno.
      Si el WS no conecta, casi siempre es el proxy (hace falta el upgrade y, en el origen, el puerto
      correcto). Mirar la pestaña Red: debe verse `wss://` en 101.
- [ ] **`ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`** con el dominio real, y `SECURE_PROXY_SSL_HEADER`
      puesto, o Django verá `http` detrás de Cloudflare y redirigirá en bucle.
- [ ] **Healthcheck** `GET /api/health/` responde 200 desde fuera de la red local (no solo desde el
      propio servidor).
- [ ] **Estáticos y tarjetas**: abrir una mesa y comprobar en Red que **ninguna imagen de carta da
      404**. Son 92 cartas + 2 dorsos; un fallo aquí deja huecos en blanco que nadie reporta.

## 2. Lo nuevo de esta tanda

- [ ] **QR de sala**: escanearlo con un Android y un iPhone. Debe abrir `/culo?codigo=XXXX` y entrar
      solo. Si el enlace abre pero no entra, es que `entrarSala()` se lanzó antes de que el WebSocket
      estuviera abierto.
- [ ] **Selector de baraja**: cambiar a francesa en la cabecera, recargar y comprobar que se mantiene
      (va en `localStorage`). Ojo: **solo cambia la mano**; las cartas de la mesa siguen en española
      hasta que se cableen (ver roadmap).
- [ ] **Abanico y mano fija en un móvil real**: con 10 cartas, ninguna debe salirse de la pantalla ni
      quedar tapada por la barra del navegador. Probar con la barra de direcciones visible y oculta.
- [ ] **Gestos**: doble toque juega, mantener pulsado enseña la carta, y el toque de cierre de la vista
      previa no dispara nada debajo.
- [ ] **Vibración**: en iOS no existe (`navigator.vibrate` no está); es normal que no vibre.

## 3. Cuentas y sesión

- [ ] Registro con Google (si está activo) y con correo, y **recuperación de contraseña**: que el
      correo salga de verdad (SMTP real, no consola) y que el enlace funcione.
- [ ] Cerrar sesión y comprobar que el token deja de valer (que no basta con borrar el `localStorage`).
- [ ] Sesión caducada a mitad de partida: qué ve el jugador.

## 4. Operación

- [ ] **Copias de la base de datos**: `scripts/backup.sh` programado en cron y una restauración
      probada al menos una vez (una copia que nunca se restaura no es una copia).
- [ ] **Logs**: que se escriban en un sitio que sobreviva a un reinicio y que no crezcan sin límite.
- [ ] **Arranque limpio**: `docker compose down && docker compose up -d` y todo vuelve solo, incluida
      la base de datos y las migraciones.
- [ ] **Vigilancia externa** de `/api/health/` (UptimeRobot o similar) con aviso al móvil.
- [ ] `manage.py check --deploy` con el dominio y `DEBUG=false`: revisar los avisos que queden.

## 5. Cosas que se ven solo con gente

- [ ] Seis personas en una sala: el lobby no se rompe, los nombres largos no descuadran y el código se
      lee a un metro.
- [ ] Alguien se cae a mitad de baza: qué pasa con su asiento (hoy no hay reconexión silenciosa).
- [ ] Dos pestañas del mismo usuario a la vez.
- [ ] Un móvil en horizontal.

## 6. Legal, antes de abrirlo al público

- [ ] **Licencia del arte de las cartas**: los PNG 8-bit vienen de Balatro (juego comercial). O hay
      permiso, o se cambia a la baraja de itch (pedir licencia al autor) o a la de Wikimedia (dominio
      público). El código ya está preparado: es cambiar la carpeta en `decks.ts`.
- [ ] Aviso de privacidad y qué se guarda (correo, nombre de usuario, partidas).
