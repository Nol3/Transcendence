#!/usr/bin/env bash
#
# Copia de seguridad: la base de datos y los ficheros subidos por los usuarios.
#
#   ./scripts/backup.sh                 # a ./backups/
#   ./scripts/backup.sh /mnt/disco/ts   # a un disco externo
#
# Se puede poner en el cron del servidor, por ejemplo cada noche a las 4:
#
#   0 4 * * * cd /ruta/al/proyecto && ./scripts/backup.sh /mnt/disco/transcendence >> /var/log/transcendence-backup.log 2>&1
#
# Qué guarda:
#   - base-<fecha>.sql.gz    : volcado de PostgreSQL comprimido.
#   - media-<fecha>.tar.gz   : avatares y demás ficheros subidos.
#
# Para restaurar, ver docs/DESPLIEGUE.md.
set -euo pipefail
cd "$(dirname "$0")/.."

DESTINO="${1:-./backups}"
FECHA="$(date +%Y%m%d-%H%M%S)"
COMPOSE=(docker compose -f compose.yaml -f compose.prod.yaml)
DB_USER="${DB_USER:-transcendence}"
DB_NAME="${DB_NAME:-transcendence}"

mkdir -p "$DESTINO"

echo "Volcando la base de datos…"
"${COMPOSE[@]}" exec -T postgres pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$DESTINO/base-$FECHA.sql.gz"

echo "Guardando los ficheros subidos…"
"${COMPOSE[@]}" run --rm -T --entrypoint sh backend -c \
  "tar czf - -C /app/media . 2>/dev/null || true" > "$DESTINO/media-$FECHA.tar.gz"

echo
echo "Copia hecha en $DESTINO:"
ls -lh "$DESTINO" | tail -3
echo
echo "Recuerda que una copia que vive en el mismo disco que el original no es una copia."
echo "Llévala a otro sitio (disco externo, otro equipo o la nube)."
