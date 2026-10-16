"""Logros del póker (roadmap 7.1).

Se calculan sobre el historial que ya se guarda (`PokerHandPlayer` / `PokerHandRecord`),
sin modelo nuevo: cualquier mano que se juegue entra sola en el cálculo.

Los tres del roadmap, con nombres honestos sobre qué se mide:

- **primera_mano**: ganar una mano (lo primero que desbloquea casi todo el mundo).
- **escalera_de_color**: completar una escalera de color en una mano.
- **tres_seguidas**: ganar tres manos seguidas.
"""
from __future__ import annotations

from .engine.hand_eval import CATEGORY_NAMES, STRAIGHT_FLUSH
from .models import PokerHandPlayer

# El historial guarda el nombre **de pantalla** de la mano («Escalera de color»), no su
# código interno, así que se compara con el nombre del motor para no tener dos listas.
ESCALERA_DE_COLOR = CATEGORY_NAMES[STRAIGHT_FLUSH]

LOGROS = (
    ("primera_mano", 1),
    ("escalera_de_color", 1),
    ("tres_seguidas", 3),
)


def _manos_de(user):
    """Manos del jugador en orden cronológico (por partida y número de mano)."""
    return list(
        PokerHandPlayer.objects.filter(user=user)
        .select_related("hand")
        .order_by("hand__created_at", "hand__id", "seat")
    )


def mejor_racha(manos) -> int:
    """Manos ganadas seguidas (la mejor racha del historial)."""
    mejor = actual = 0
    for mano in manos:
        if mano.won > 0:
            actual += 1
            mejor = max(mejor, actual)
        else:
            actual = 0
    return mejor


def logros_de(user) -> list[dict]:
    """Estado de cada logro para ese jugador."""
    manos = _manos_de(user)
    ganadas = sum(1 for m in manos if m.won > 0)
    escalera = any(m.hand_name == ESCALERA_DE_COLOR for m in manos)
    racha = mejor_racha(manos)

    valores = {
        "primera_mano": ganadas,
        "escalera_de_color": 1 if escalera else 0,
        "tres_seguidas": racha,
    }

    salida = []
    for logro_id, objetivo in LOGROS:
        valor = valores[logro_id]
        salida.append({
            "id": logro_id,
            "unlocked": valor >= objetivo,
            "progress": min(valor, objetivo),
            "target": objetivo,
        })
    return salida
