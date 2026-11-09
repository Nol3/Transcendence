#!/usr/bin/env bash
#
# Instala un certificado de **origen** de Cloudflare (o cualquiera) donde nginx lo lee, para
# poder poner Cloudflare en modo «Full (strict)».
#
#   ./scripts/instalar-certificado.sh origen.pem origen-key.pem
#   ./scripts/instalar-certificado.sh --ver          # enseña el que hay puesto
#
# El certificado de origen se saca gratis en Cloudflare → SSL/TLS → Origin Server → Create
# Certificate, y vale 15 años. Sin él, nginx sirve el self-signed de `ssl-init` y Cloudflare en
# «Full (strict)» devuelve **526** (no puede validar el origen).
#
# Se escribe en **los dos sitios** que puede usar nginx, porque depende del modo:
#   · producción → `${SSL_DIR:-./docker/ssl}` (bind mount del overlay `compose.prod.yaml`)
#   · desarrollo → volumen `ssl_certs`, que rellena `ssl-init` si está vacío
# Los dos están en `.gitignore`: una clave privada no se versiona nunca.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f compose.yaml -f compose.prod.yaml)
CARPETA="${SSL_DIR:-./docker/ssl}"
VOLUMEN="${SSL_VOLUME:-$(docker volume ls -q --filter name=ssl_certs | head -1)}"

# La imagen con openssl, la misma (y con el mismo digest) que usa `ssl-init` en el compose: así
# no se fija aquí una versión distinta que se quede atrás.
IMAGEN_SSL="$(grep -o 'alpine/openssl@sha256:[a-f0-9]*' compose.yaml | head -1)"

if [ "${1:-}" = "--ver" ]; then
    echo "Carpeta de producción: $CARPETA"
    echo "Volumen de desarrollo: ${VOLUMEN:-(no existe)}"
    if [ -f "$CARPETA/cert.pem" ]; then
        echo "— el de $CARPETA —"
        openssl x509 -in "$CARPETA/cert.pem" -noout -subject -issuer -dates
    elif [ -n "$VOLUMEN" ]; then
        echo "— el del volumen —"
        docker run --rm -v "$VOLUMEN:/ssl:ro" --entrypoint openssl "$IMAGEN_SSL" \
            x509 -in /ssl/cert.pem -noout -subject -issuer -dates 2>/dev/null \
            || echo "El volumen no tiene certificado todavía."
    else
        echo "No hay ningún certificado instalado."
    fi
    exit 0
fi

CERT="${1:-}"
CLAVE="${2:-}"
if [ -z "$CERT" ] || [ -z "$CLAVE" ]; then
    echo "Uso: $0 <certificado.pem> <clave.pem>" >&2
    echo "     $0 --ver" >&2
    exit 1
fi
[ -f "$CERT" ] || { echo "No existe: $CERT" >&2; exit 1; }
[ -f "$CLAVE" ] || { echo "No existe: $CLAVE" >&2; exit 1; }

# Se valida el par antes de tocar nada: si la clave no es la del certificado, nginx no arranca y
# el sitio se queda caído hasta que alguien lo mire.
if [ "$(openssl x509 -in "$CERT" -noout -modulus 2>/dev/null | openssl sha256)" != \
     "$(openssl rsa -in "$CLAVE" -noout -modulus 2>/dev/null | openssl sha256)" ]; then
    echo "La clave no corresponde a ese certificado." >&2
    exit 1
fi

echo "Certificado que se va a instalar:"
openssl x509 -in "$CERT" -noout -subject -issuer -dates | sed 's/^/  /'

mkdir -p "$CARPETA"
cp "$CERT" "$CARPETA/cert.pem"
cp "$CLAVE" "$CARPETA/key.pem"
chmod 644 "$CARPETA/cert.pem" "$CARPETA/key.pem"
echo "Copiado en $CARPETA (lo que monta producción)."

if [ -n "$VOLUMEN" ]; then
    docker run --rm -v "$VOLUMEN:/ssl" -v "$(cd "$CARPETA" && pwd):/origen:ro" alpine \
        sh -c 'cp /origen/cert.pem /ssl/cert.pem && cp /origen/key.pem /ssl/key.pem &&
               chmod 644 /ssl/cert.pem /ssl/key.pem'
    echo "Copiado también en el volumen $VOLUMEN (lo que usa desarrollo)."
fi

if "${COMPOSE[@]}" ps --format '{{.Service}}' 2>/dev/null | grep -qx nginx; then
    echo "Recargando nginx…"
    "${COMPOSE[@]}" restart nginx >/dev/null
    for _ in $(seq 1 30); do
        if "${COMPOSE[@]}" ps --format '{{.Status}}' nginx | grep -q healthy; then
            echo "Nginx arriba con el certificado nuevo."
            exit 0
        fi
        sleep 2
    done
    echo "Nginx no llegó a estar sano: mira 'docker compose logs nginx'." >&2
    exit 1
fi
echo "Nginx no está levantado; el certificado queda listo para el próximo arranque."
