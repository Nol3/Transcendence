"""El bot del Mus, en el servidor.

Mismo criterio que el del front: evalúa los cuatro lances y aprieta solo cuando la mano lo merece.
En el mus pide descartar si la mano no tiene nada, pero **solo una vez**: si ya ha cambiado cartas
y sigue sin tener nada, corta. Sin ese tope, cuatro bots pidiendo mus se quedarían dando vueltas
para siempre.
"""
from __future__ import annotations

from ..baraja import Card
from .engine import Jugada, MusState, comparar, evaluar, pareja_de, turno_actual


def valor_jugada(j: Jugada) -> int:
    valor = 0
    if j.pares_categoria == "duples":
        valor += 3
    elif j.pares_categoria == "medias":
        valor += 2
    elif j.pares_categoria == "par":
        valor += 1
    if j.juego is not None:
        valor += 3
    if j.grande >= 9:
        valor += 1
    if j.chica <= 2:
        valor += 1
    return valor


def _cartas_que_sobran(mano: list[Card]) -> list[str]:
    por_rango: dict[int, list[Card]] = {}
    for c in mano:
        por_rango.setdefault(c.rank, []).append(c)

    utiles = set()
    for cartas in por_rango.values():
        if len(cartas) >= 2:
            utiles.update(c.id for c in cartas)
    ordenadas = sorted(mano, key=lambda c: evaluar([c]).grande)
    if ordenadas:
        utiles.add(ordenadas[0].id)
        utiles.add(ordenadas[-1].id)

    sobran = [c.id for c in mano if c.id not in utiles]
    return sobran[:3] if len(sobran) == 4 else sobran


def _mejor_contraria(state: MusState, seat: int, lance: str) -> Jugada | None:
    contrarios = state.teams[1 - pareja_de(seat)].players
    mejor: Jugada | None = None
    for i in contrarios:
        j = state.players[i].jugada
        if mejor is None or comparar(j, mejor, lance) > 0:
            mejor = j
    return mejor


def bot_decision(state: MusState, seat: int) -> tuple[str, object] | None:
    """Qué hace el bot: `("mus",)`, `("cortar",)`, `("descartar", ids)`, `("pasar",)`…"""
    if state.phase in ("game-end", "vaca-end"):
        return None
    if turno_actual(state) != seat:
        return None

    yo = state.players[seat]

    if state.phase == "mus":
        if valor_jugada(yo.jugada) >= 2 or yo.descartes >= 1:
            return ("cortar", None)
        return ("mus", None)

    if state.phase == "descartar":
        return ("descartar", _cartas_que_sobran(yo.hand))

    lance = state.lance
    if not lance:
        return None

    # Si hay un envite esperando respuesta, contesta.
    if state.envite and state.responde == seat:
        mia = yo.jugada
        suya = _mejor_contraria(state, seat, lance)
        gano = comparar(mia, suya, lance) > 0 if suya else True
        valor = valor_jugada(mia)
        if state.envite["ordago"]:
            return ("quiero", None) if gano and valor >= 4 else ("no_quiero", None)
        if gano and valor >= 3:
            return ("quiero", None)
        if valor >= 2 and state.envite["cuantas"] <= 2:
            return ("quiero", None)
        return ("no_quiero", None)

    todas = [p.jugada for p in state.players]
    gano_la_mesa = sum(1 for o in todas if comparar(yo.jugada, o, lance) > 0) == len(todas) - 1
    valor = valor_jugada(yo.jugada)

    if gano_la_mesa and valor >= 3:
        return ("ordago", None) if valor >= 6 else ("envidar", 2)
    if valor >= 4:
        return ("envidar", 2)
    return ("pasar", None)
