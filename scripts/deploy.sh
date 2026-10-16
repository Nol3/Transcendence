#!/usr/bin/env bash
#
# Despliegue en el servidor. Pensado para pegarse tal cual en la máquina:
#
#   DOMINIO=tudominio.com EMAIL=tucorreo@example.com ./scripts/deploy.sh --certificado
#   ./scripts/deploy.sh                 # actualiza y levanta
#
# Lo que hace, en orden:
#   1. Copia el certificado de Let's Encrypt al sitio donde nginx lo busca.
#   2. Baja los cambios del repositorio (si es un repo git).
#   3. Reconstruye y levanta con el overlay de producción.
#   4. Espera a que todo esté sano y lo dice.
#
# Con `--certificado` además saca (o renueva) el certificado. Para eso nginx tiene
# que estar parado un momento, porque certbot necesita el puerto 80 para
# comprobar que el dominio es tuyo. Es lo normal la primera vez.
set -euo pipefail
cd "$(dirname "$0")/.."

DOMINIO="${DOMINIO:-}"
EMAIL="${EMAIL:-}"
SSL_DIR="${SSL_DIR:-./docker/ssl}"
COMPOSE=(docker compose -f compose.yaml -f compose.prod.yaml)

pedir_dominio() {
  if [ -z "$DOMINIO" ]; then
    echo "Falta el dominio. Uso: DOMINIO=tudominio.com EMAIL=tucorreo@example.com $0 $*"
    exit 1
  fi
}

copiar_certificado() {
  local origen="/etc/letsencrypt/live/$DOMINIO"
  if [ ! -f "$origen/fullchain.pem" ]; then
    echo "Todavía no hay certificado para $DOMINIO."
    echo "Sácalo con: DOMINIO=$DOMINIO EMAIL=$EMAIL $0 --certificado"
    exit 1
  fi
  mkdir -p "$SSL_DIR"
  # nginx los busca con estos dos nombres, igual que en desarrollo.
  cp "$origen/fullchain.pem" "$SSL_DIR/cert.pem"
  cp "$origen/privkey.pem" "$SSL_DIR/key.pem"
  chmod 644 "$SSL_DIR"/*.pem
  echo "[1/4] Certificado de $DOMINIO copiado a $SSL_DIR"
}

sacar_certificado() {
  pedir_dominio
  if ! command -v certbot >/dev/null 2>&1; then
    echo "Falta certbot. En Debian/Ubuntu:"
    echo "  sudo apt update && sudo apt install -y certbot"
    exit 1
  fi
  echo "Parando nginx un momento para que certbot pueda usar el puerto 80…"
  "${COMPOSE[@]}" stop nginx || true
  sudo certbot certonly --standalone --non-interactive --agree-tos \
    -m "$EMAIL" -d "$DOMINIO" --keep-until-expiring
  echo "Certificado listo. nginx volverá a levantarse en el despliegue."
}

actualizar_codigo() {
  if [ -d .git ]; then
    echo "[2/4] Trayendo cambios…"
    git pull --ff-only || echo "Aviso: no se pudo hacer git pull (¿cambios locales?). Sigo con lo que hay."
  else
    echo "[2/4] No es un repositorio git: se despliega lo que hay en la carpeta."
  fi
}

levantar() {
  echo "[3/4] Reconstruyendo y levantando…"
  "${COMPOSE[@]}" up -d --build
  echo "[4/4] Esperando a que el stack esté sano…"
  for _ in $(seq 1 60); do
    local sanos
    sanos=$("${COMPOSE[@]}" ps --format '{{.Status}}' | grep -c healthy || true)
    if [ "$sanos" -ge 4 ]; then
      echo "Listo: $sanos servicios sanos."
      "${COMPOSE[@]}" ps --format '{{.Service}}\t{{.Status}}'
      return 0
    fi
    sleep 5
  done
  echo "Algo no ha llegado a estar sano. Mira los logs:"
  echo "  ${COMPOSE[*]} logs --tail 50"
  return 1
}

case "${1:-}" in
  --certificado|--cert)
    sacar_certificado
    copiar_certificado
    actualizar_codigo
    levantar
    ;;
  *)
    copiar_certificado
    actualizar_codigo
    levantar
    ;;
esac
