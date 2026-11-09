#!/usr/bin/env bash
#
# Restaurar una copia de seguridad **y comprobarla**. Es el otro lado de `backup.sh`: una copia
# que nunca se ha restaurado no es una copia, es una carpeta con bytes.
#
#   ./scripts/restaurar.sh                       # verifica la copia más reciente de ./backups
#   ./scripts/restaurar.sh backups/base-X.sql.gz # verifica una copia concreta
#   ./scripts/restaurar.sh --real <volcado>      # restaura de verdad sobre el Postgres del stack
#
# Por defecto **no toca nada**: levanta un Postgres desechable, restaura ahí el volcado y compara
# el número de filas de las tablas importantes con la base de datos viva. Si los recuentos cuadran,
# la copia sirve; si no, avisa. Con `--real` sí restaura sobre la base del stack (pide confirmación
# por la boca y hay que escribir «restaurar»).
#
# Variables: DB_USER y DB_NAME (por defecto `transcendence`, igual que `backup.sh`).
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f compose.yaml -f compose.prod.yaml)
DB_USER="${DB_USER:-transcendence}"
DB_NAME="${DB_NAME:-transcendence}"
# Nombres por defecto de Django (`<app>_<modelo>`): el usuario es el `auth_user` de siempre.
TABLAS=(auth_user users_userprofile games_game tournament_tournament tournament_tournamentmatch
        poker_pokerhandrecord chat_message)
CONTENEDOR="ts_restaurar_$$"
IMAGEN="postgres:16-alpine"

modo="verificar"
case "${1:-}" in
    --real) modo="real"; shift ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac

VOLCADO="${1:-$(ls -t backups/base-*.sql.gz 2>/dev/null | head -1 || true)}"
if [ -z "${VOLCADO}" ] || [ ! -f "${VOLCADO}" ]; then
    echo "No encuentro el volcado. Uso: $0 [--real] <fichero.sql.gz>" >&2
    exit 1
fi

echo "Volcado: $VOLCADO ($(du -h "$VOLCADO" | cut -f1))"

# Recuento de filas de una base: se le pasa la conexión ya montada y devuelve «tabla=filas».
recuentos() {
    local psql_cmd=("$@")
    local tabla
    for tabla in "${TABLAS[@]}"; do
        local n
        n=$(echo "SELECT count(*) FROM ${tabla}" | "${psql_cmd[@]}" -tA 2>/dev/null || echo "-")
        echo "${tabla}=${n}"
    done
}

limpiar() { docker rm -f "$CONTENEDOR" >/dev/null 2>&1 || true; }
trap limpiar EXIT

if [ "$modo" = "real" ]; then
    echo
    echo "Vas a RESTAURAR sobre la base de datos del stack. Se pierde lo que haya ahora."
    read -r -p "Escribe «restaurar» para continuar: " respuesta
    [ "$respuesta" = "restaurar" ] || { echo "Cancelado."; exit 1; }
    echo "Restaurando…"
    gunzip -c "$VOLCADO" | "${COMPOSE[@]}" exec -T postgres psql -q -U "$DB_USER" -d "$DB_NAME"
    echo "Restaurado. Recuentos:"
    recuentos "${COMPOSE[@]}" exec -T postgres psql -U "$DB_USER" -d "$DB_NAME"
    exit 0
fi

echo
echo "1/3 · Levantando un Postgres desechable (${IMAGEN})…"
docker run -d --rm --name "$CONTENEDOR" -e POSTGRES_PASSWORD=restaurar -e POSTGRES_DB="$DB_NAME" \
    "$IMAGEN" >/dev/null
for _ in $(seq 1 60); do
    if docker exec "$CONTENEDOR" pg_isready -U postgres -q 2>/dev/null; then break; fi
    sleep 1
done
docker exec "$CONTENEDOR" pg_isready -U postgres -q || { echo "El Postgres desechable no arranca." >&2; exit 1; }

# El volcado lleva `OWNER TO <usuario>` y GRANTs: sin el rol, psql escupe errores en cada tabla
# (aunque el esquema se restaure igual). Se crea con el mismo nombre para que la prueba sea limpia.
docker exec "$CONTENEDOR" psql -q -U postgres -d postgres \
    -c "CREATE ROLE \"${DB_USER}\" LOGIN SUPERUSER PASSWORD 'restaurar'" >/dev/null 2>&1 || true

echo "2/3 · Restaurando el volcado…"
gunzip -c "$VOLCADO" | docker exec -i "$CONTENEDOR" psql -q -U postgres -d "$DB_NAME" >/dev/null

tablas_restauradas=$(echo "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" \
    | docker exec -i "$CONTENEDOR" psql -tA -U postgres -d "$DB_NAME")
if [ "${tablas_restauradas:-0}" -lt 10 ]; then
    echo "El volcado solo trae ${tablas_restauradas:-0} tabla(s): no parece una copia buena." >&2
    exit 1
fi
echo "   ${tablas_restauradas} tablas restauradas."

echo "3/3 · Comparando recuentos con la base viva…"
restaurada=$(recuentos docker exec -i "$CONTENEDOR" psql -U postgres -d "$DB_NAME")
viva=$(recuentos "${COMPOSE[@]}" exec -T postgres psql -U "$DB_USER" -d "$DB_NAME")

fallos=0
echo
printf '%-24s %10s %10s\n' "tabla" "copia" "viva"
for fila in $restaurada; do
    tabla="${fila%%=*}"; n_copia="${fila##*=}"
    n_viva=$(echo "$viva" | tr ' ' '\n' | grep "^${tabla}=" | cut -d= -f2)
    marca=""
    # La copia es de un momento anterior: puede tener menos filas, nunca más, y siempre > 0 si la
    # tabla tenía datos. Un 0 en una tabla que en vivo tiene filas es un volcado roto.
    if [ "$n_copia" = "-" ] || { [ "$n_viva" != "-" ] && [ "$n_copia" -gt "$n_viva" ]; }; then
        marca="  <-- MAL"; fallos=$((fallos + 1))
    fi
    printf '%-24s %10s %10s%s\n' "$tabla" "$n_copia" "$n_viva" "$marca"
done

echo
if [ "$fallos" -eq 0 ]; then
    echo "La copia se restaura y cuadra con la base viva."
else
    echo "Hay $fallos tabla(s) que no cuadran: revisa el volcado antes de fiarte de él." >&2
    exit 1
fi
