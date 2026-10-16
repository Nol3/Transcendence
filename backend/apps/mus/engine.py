"""Reglas del Mus, en el servidor.

Port fiel del motor ya probado en el front (`front/src/app/core/games/mus/`). En cuanto la partida
es online las reglas **tienen** que vivir aquí.

Lo esencial:
  - **Cuatro jugadores en dos parejas**, cada uno frente a su compañero: 0 y 2 contra 1 y 3.
  - **Sin triunfo ni palos.** El orden es rey o tres, caballo, sota, siete, seis, cinco, cuatro,
    dos o as: se juega «con ocho reyes y ocho ases», o sea que el 3 vale lo mismo que el rey y el 2
    lo mismo que el as.
  - **El mus se corta una sola vez**: en cuanto alguien dice «no hay mus», se cierra el descarte
    para todos, aunque alguno no haya hablado.
  - Los **cuatro lances** en orden: grande, chica, pares y juego. El orden importa, porque una
    pareja puede llegar a las 40 piedras a mitad del recuento y ahí se acaba.
  - El **juego** se ordena 31, 32, 40, 37, 36, 35, 34, 33 (el 38 y el 39 no existen, no hay ochos
    ni nueves). Si nadie tiene juego, se va al **punto**: gana el que más se acerque al 30.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ..baraja import Card, build_deck, deal_some, shuffle

JUGADORES = 4
PIEDRAS_PARA_GANAR = 40
JUEGOS_POR_VACA = 3
ENVIDO_MINIMO = 2
LANCES: tuple[str, ...] = ("grande", "chica", "pares", "juego")
ORDEN_MUS: tuple[int, ...] = (12, 3, 11, 10, 7, 6, 5, 4, 1, 2)
# El 3 vale lo mismo que el rey y el 2 lo mismo que el as.
EQUIVALENCIAS = {3: 12, 2: 1}


class MusError(Exception):
    """Un movimiento imposible, con código corto para que el front lo traduzca."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def puntos_mus(carta: Card) -> int:
    """Lo que vale la carta al contar los puntos (para el punto)."""
    if carta.rank in (12, 3, 11, 10):
        return 10
    if carta.rank in (2, 1):
        return 1
    return carta.rank


def puntos_juego(carta: Card) -> int:
    """Lo que vale para el juego: aquí el tres vale 3 y el dos 1."""
    if carta.rank in (12, 11, 10):
        return 10
    return carta.rank


def fuerza_mus(carta: Card) -> int:
    """La fuerza de una carta: más alto gana. El tres empata con el rey y el dos con el as."""
    rank = EQUIVALENCIAS.get(carta.rank, carta.rank)
    return len(ORDEN_MUS) - ORDEN_MUS.index(rank)


@dataclass
class Jugada:
    grande: int = 0
    chica: int = 0
    pares_categoria: str | None = None
    pares_alto: int = 0
    juego: int | None = None
    punto: int = 0


def evaluar(mano: list[Card]) -> Jugada:
    if not mano:
        return Jugada()
    fuerzas = [fuerza_mus(c) for c in mano]
    repes: dict[int, int] = {}
    for c in mano:
        repes[c.rank] = repes.get(c.rank, 0) + 1
    ordenados = sorted(repes.items(), key=lambda kv: kv[1], reverse=True)
    cuantos = ordenados[0][1]
    dos_parejas = sum(1 for _, n in ordenados if n == 2) == 2
    categoria = (
        "duples" if cuantos == 4 or dos_parejas
        else "medias" if cuantos == 3
        else "par" if cuantos == 2
        else None
    )

    alto = 0
    if categoria == "duples":
        rangos = [ordenados[0][0]] if cuantos == 4 else [r for r, n in ordenados if n == 2]
        alto = max(fuerza_mus(Card(rank=r, suit="o")) for r in rangos)
    elif categoria:
        alto = fuerza_mus(Card(rank=ordenados[0][0], suit="o"))

    suma = sum(puntos_juego(c) for c in mano)
    return Jugada(
        grande=max(fuerzas),
        chica=min(fuerzas),
        pares_categoria=categoria,
        pares_alto=alto,
        juego=suma if suma >= 31 else None,
        punto=sum(puntos_mus(c) for c in mano),
    )


def orden_juego(suma: int) -> int:
    """El orden del juego, de mejor a peor: 31, 32, 40, 37, 36, 35, 34, 33."""
    orden = (31, 32, 40, 37, 36, 35, 34, 33)
    return orden.index(suma) if suma in orden else -1


def _peso_pares(categoria: str | None) -> int:
    return {"duples": 3, "medias": 2, "par": 1}.get(categoria or "", 0)


def _punto_cerca(punto: int) -> int:
    return 30 - punto if punto <= 30 else 100 + (punto - 30)


def comparar(a: Jugada, b: Jugada, lance: str) -> int:
    """Compara dos jugadas del mismo lance. Positivo si gana la primera."""
    if lance == "grande":
        return a.grande - b.grande
    if lance == "chica":
        return b.chica - a.chica
    if lance == "pares":
        d = _peso_pares(a.pares_categoria) - _peso_pares(b.pares_categoria)
        return d if d != 0 else a.pares_alto - b.pares_alto
    if a.juego is not None or b.juego is not None:
        if a.juego is None:
            return -1
        if b.juego is None:
            return 1
        return orden_juego(b.juego) - orden_juego(a.juego)
    # Menos distancia al 30 es mejor: el signo va al revés que en los demás lances.
    return _punto_cerca(b.punto) - _punto_cerca(a.punto)


@dataclass
class MusPlayer:
    id: int
    name: str
    is_bot: bool = False
    hand: list[Card] = field(default_factory=list)
    jugada: Jugada = field(default_factory=Jugada)
    hablado: bool = False
    # Cuántas veces ha cambiado cartas: el bot solo pide mus una vez por mano.
    descartes: int = 0
    connected: bool = True


@dataclass
class MusTeam:
    id: int
    players: list[int]
    piedras: int = 0
    juegos: int = 0


@dataclass
class MusState:
    players: list[MusPlayer] = field(default_factory=list)
    teams: list[MusTeam] = field(default_factory=list)
    mano: int = 0
    phase: str = "mus"  # mus | descartar | lances | game-end | vaca-end
    lance: str | None = None
    envite: dict[str, Any] | None = None
    responde: int | None = None
    pasados: list[int] = field(default_factory=list)
    piedras_del_lance: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    winner: int | None = None


def pareja_de(seat: int) -> int:
    """La pareja de cada asiento: el 0 con el 2, el 1 con el 3."""
    return seat % 2


def new_game(
    names: list[str],
    bots: list[bool] | None = None,
    piedras: list[int] | None = None,
    juegos: list[int] | None = None,
    mano: int = 0,
    rng: random.Random | None = None,
) -> MusState:
    if len(names) != JUGADORES:
        raise MusError("players", "el mus se juega de cuatro, en dos parejas")
    mazo = shuffle(build_deck(1), rng)
    manos, _ = deal_some(mazo, JUGADORES, 4)
    return MusState(
        players=[
            MusPlayer(id=i, name=n, is_bot=(bots[i] if bots else False),
                      hand=list(manos[i]), jugada=evaluar(manos[i]))
            for i, n in enumerate(names)
        ],
        teams=[
            MusTeam(0, [0, 2], piedras[0] if piedras else 0, juegos[0] if juegos else 0),
            MusTeam(1, [1, 3], piedras[1] if piedras else 0, juegos[1] if juegos else 0),
        ],
        mano=mano,
        events=[{"kind": "deal"}],
    )


def turno_de(state: MusState, i: int) -> int:
    return (state.mano + i) % JUGADORES


def turno_actual(state: MusState) -> int | None:
    """A quién le toca hablar ahora (en el mus o en los lances)."""
    if state.responde is not None:
        return state.responde
    # Las tres fases en las que se habla van por el mismo orden: empezando por el mano.
    if state.phase in ("mus", "lances", "descartar"):
        for i in range(JUGADORES):
            seat = turno_de(state, i)
            if not state.players[seat].hablado:
                return seat
    return None


def _jugador(state: MusState, player_id: int) -> MusPlayer:
    if not 0 <= player_id < len(state.players):
        raise MusError("unknown_player", "ese jugador no está en la mesa")
    return state.players[player_id]


def _siguiente_contrario(state: MusState, player_id: int) -> int:
    for i in range(1, JUGADORES + 1):
        seat = (player_id + i) % JUGADORES
        if pareja_de(seat) != pareja_de(player_id):
            return seat
    return (player_id + 1) % JUGADORES


def _comprobar_turno(state: MusState, player_id: int) -> None:
    """Se habla por orden, empezando por el mano.

    Si no se comprobara, el servidor aceptaría un mus fuera de turno.
    """
    if turno_actual(state) != player_id:
        raise MusError("not_your_turn", "ahora no te toca")


def decir_mus(state: MusState, player_id: int) -> None:
    if state.phase != "mus":
        raise MusError("not_mus", "ya no se puede pedir mus")
    _comprobar_turno(state, player_id)
    yo = _jugador(state, player_id)
    if yo.hablado:
        raise MusError("already_spoke", "ya has hablado en esta mano")
    yo.hablado = True
    state.events.append({"kind": "mus", "player": player_id})
    if all(p.hablado for p in state.players):
        # Al descarte se entra con las marcas limpias: el descarte también va por turnos.
        for p in state.players:
            p.hablado = False
        state.phase = "descartar"


def cortar_mus(state: MusState, player_id: int) -> None:
    if state.phase != "mus":
        raise MusError("not_mus", "ya no se puede cortar el mus")
    _comprobar_turno(state, player_id)
    yo = _jugador(state, player_id)
    if yo.hablado:
        raise MusError("already_spoke", "ya has hablado en esta mano")
    yo.hablado = True
    state.events.append({"kind": "cortar", "player": player_id})
    # En cuanto uno corta, se cierra el descarte para todos.
    state.phase = "lances"
    state.lance = LANCES[0]
    state.pasados = []
    for p in state.players:
        p.hablado = False


def descartar(state: MusState, player_id: int, card_ids: list[str],
              rng: random.Random | None = None) -> None:
    if state.phase != "descartar":
        raise MusError("not_discard", "ahora no se descarta")
    _comprobar_turno(state, player_id)
    yo = _jugador(state, player_id)  # el descarte lo puede hacer cada uno cuando le toque
    if not card_ids or len(card_ids) > 4:
        raise MusError("bad_discard", "se descartan entre una y cuatro cartas")
    for cid in card_ids:
        if not any(c.id == cid for c in yo.hand):
            raise MusError("not_your_card", "esa carta no es tuya")

    mazo = shuffle(build_deck(1), rng)
    usadas = {c.id for p in state.players for c in p.hand}
    nuevas: list[Card] = []
    for carta in mazo:
        if len(nuevas) >= len(card_ids):
            break
        if carta.id in usadas or any(n.id == carta.id for n in nuevas):
            continue
        nuevas.append(carta)

    yo.hand = [c for c in yo.hand if c.id not in card_ids] + nuevas
    yo.jugada = evaluar(yo.hand)
    yo.descartes += 1
    # `hablado` marca que ya ha descartado en esta vuelta; cuando todos han descartado, se vuelve
    # al mus con la marca limpia para poder volver a hablar.
    yo.hablado = True
    state.events.append({"kind": "descartar", "player": player_id, "cuantas": len(card_ids)})
    if all(p.hablado for p in state.players):
        for p in state.players:
            p.hablado = False
        state.phase = "mus"


def _comprobar_lance(state: MusState, player_id: int) -> None:
    if state.phase != "lances":
        raise MusError("not_lances", "ahora no se envidan lances")
    _comprobar_turno(state, player_id)
    if state.envite:
        raise MusError("betting", "hay un envite sin resolver")
    if _jugador(state, player_id).hablado:
        raise MusError("already_spoke", "ya has hablado en este lance")


def pasar(state: MusState, player_id: int) -> None:
    _comprobar_lance(state, player_id)
    state.players[player_id].hablado = True
    state.pasados.append(player_id)
    state.events.append({"kind": "envite", "player": player_id, "apuesta": "paso", "cuantas": 0})
    if all(p.hablado for p in state.players):
        _resolver_lance(state)


def envidar(state: MusState, player_id: int, cuantas: int = ENVIDO_MINIMO) -> None:
    _comprobar_lance(state, player_id)
    if cuantas < ENVIDO_MINIMO:
        raise MusError("too_small", "el envite mínimo son dos piedras")
    if state.envite and cuantas <= state.envite["cuantas"]:
        raise MusError("too_small", "hay que subir el envite")
    state.players[player_id].hablado = True
    state.envite = {"quien": player_id, "cuantas": cuantas, "ordago": False}
    # Responde **la pareja contraria**.
    state.responde = _siguiente_contrario(state, player_id)
    state.events.append(
        {"kind": "envite", "player": player_id, "apuesta": "envido", "cuantas": cuantas}
    )


def ordago(state: MusState, player_id: int) -> None:
    _comprobar_lance(state, player_id)
    state.players[player_id].hablado = True
    state.envite = {"quien": player_id, "cuantas": 0, "ordago": True}
    state.responde = _siguiente_contrario(state, player_id)
    state.events.append({"kind": "envite", "player": player_id, "apuesta": "ordago", "cuantas": 0})


def quiero(state: MusState, player_id: int) -> None:
    if not state.envite or state.responde != player_id:
        raise MusError("nothing_to_accept", "no hay nada que querer")
    envite = state.envite
    state.piedras_del_lance += envite["cuantas"]
    state.envite = None
    state.responde = None
    state.players[player_id].hablado = True
    state.events.append(
        {"kind": "envite", "player": player_id, "apuesta": "quiero", "cuantas": envite["cuantas"]}
    )
    _resolver_lance(state)


def no_quiero(state: MusState, player_id: int) -> None:
    if not state.envite or state.responde != player_id:
        raise MusError("nothing_to_reject", "no hay nada que rechazar")
    envite = state.envite
    state.teams[pareja_de(envite["quien"])].piedras += 1
    state.envite = None
    state.responde = None
    state.events.append(
        {"kind": "envite", "player": player_id, "apuesta": "no_quiero", "cuantas": 0}
    )
    state.events.append(
        {"kind": "lance", "lance": state.lance, "team": pareja_de(envite["quien"]), "piedras": 1}
    )
    # Ojo: esta piedra también puede llegar a las 40 y terminar el juego. Si solo se comprobara al
    # resolver el lance, una pareja podría pasarse de 40 por un envite rechazado y seguir jugando.
    if not _comprobar_fin(state, pareja_de(envite["quien"])):
        _siguiente_lance(state)


def _mejor_de(state: MusState, team: int, lance: str) -> tuple[int, Jugada]:
    asientos = state.teams[team].players
    mejor = (asientos[0], state.players[asientos[0]].jugada)
    for seat in asientos[1:]:
        if comparar(state.players[seat].jugada, mejor[1], lance) > 0:
            mejor = (seat, state.players[seat].jugada)
    return mejor


def _resolver_lance(state: MusState) -> None:
    """Resuelve el lance comparando las mejores jugadas de cada pareja."""
    lance = state.lance or LANCES[0]
    a = _mejor_de(state, 0, lance)
    b = _mejor_de(state, 1, lance)
    cmp = comparar(a[1], b[1], lance)
    if cmp == 0:
        state.events.append({"kind": "nadie", "lance": lance})
        _siguiente_lance(state)
        return

    ganador = 0 if cmp > 0 else 1
    gana = a[1] if ganador == 0 else b[1]

    if lance == "pares":
        valen = {"duples": 3, "medias": 2, "par": 1}.get(gana.pares_categoria or "", 1)
    elif lance == "juego":
        # 3 si es la «una», 2 si es otro juego y 1 si se ha ido al punto.
        valen = (3 if gana.juego == 31 else 2) if gana.juego is not None else 1
    else:
        valen = 2

    piedras = valen + state.piedras_del_lance
    state.teams[ganador].piedras += piedras
    state.events.append({"kind": "lance", "lance": lance, "team": ganador, "piedras": piedras})

    # Una pareja puede llegar a las 40 a mitad del recuento: ahí se acaba.
    if not _comprobar_fin(state, ganador):
        _siguiente_lance(state)


def _comprobar_fin(state: MusState, team: int) -> bool:
    """Si la pareja ha llegado a las 40 piedras, se anota el juego (y la vaca si es el tercero)."""
    if state.teams[team].piedras < PIEDRAS_PARA_GANAR:
        return False
    state.teams[team].juegos += 1
    state.events.append({"kind": "game-end", "team": team})
    if state.teams[team].juegos >= JUEGOS_POR_VACA:
        state.phase = "vaca-end"
        state.winner = team
        state.events.append({"kind": "vaca", "team": team})
    else:
        state.phase = "game-end"
    return True


def _siguiente_lance(state: MusState) -> None:
    actual = LANCES.index(state.lance or LANCES[0])
    proximo = LANCES[actual + 1] if actual + 1 < len(LANCES) else None
    state.lance = proximo
    state.pasados = []
    state.envite = None
    state.responde = None
    state.piedras_del_lance = 0
    for p in state.players:
        p.hablado = False
    if proximo is None:
        # Los cuatro lances sin que nadie llegue a 40: se reparte otra mano.
        state.phase = "mus"
        state.mano = (state.mano + 1) % JUGADORES


def next_hand(state: MusState, rng: random.Random | None = None) -> None:
    """Reparte la mano siguiente, conservando las piedras y los juegos."""
    nueva = new_game(
        names=[p.name for p in state.players],
        bots=[p.is_bot for p in state.players],
        piedras=[state.teams[0].piedras, state.teams[1].piedras],
        juegos=[state.teams[0].juegos, state.teams[1].juegos],
        mano=(state.mano + 1) % JUGADORES,
        rng=rng,
    )
    state.players = nueva.players
    state.teams = nueva.teams
    state.mano = nueva.mano
    state.phase = "mus"
    state.lance = None
    state.envite = None
    state.responde = None
    state.pasados = []
    state.piedras_del_lance = 0
    state.events = nueva.events
    state.winner = None


def state_for(state: MusState, seat: int) -> dict:
    """Lo que ve un jugador: su mano, su jugada y la de su compañero; de los rivales, nada."""
    yo = state.players[seat] if 0 <= seat < len(state.players) else None
    companero_seat = next(
        (p for p in state.teams[pareja_de(seat)].players if p != seat), None
    ) if yo else None
    companero = state.players[companero_seat] if companero_seat is not None else None

    def jugada_dict(j: Jugada) -> dict:
        return {
            "grande": j.grande,
            "chica": j.chica,
            "pares": {"categoria": j.pares_categoria, "alto": j.pares_alto},
            "juego": j.juego,
            "punto": j.punto,
        }

    return {
        "players": [
            {"id": p.id, "name": p.name, "isBot": p.is_bot,
             "handCount": len(p.hand), "connected": p.connected}
            for p in state.players
        ],
        "teams": [
            {"id": t.id, "players": list(t.players), "piedras": t.piedras, "juegos": t.juegos}
            for t in state.teams
        ],
        "myHand": [c.to_dict() for c in (yo.hand if yo else [])],
        "myJugada": jugada_dict(yo.jugada if yo else Jugada()),
        "mano": state.mano,
        "phase": state.phase,
        "lance": state.lance,
        "turn": turno_actual(state),
        "envite": state.envite,
        "responde": state.responde,
        "pasados": list(state.pasados),
        "puedoHablar": bool(yo) and not yo.hablado and state.phase in ("mus", "lances"),
        "companero": (
            {"id": companero.id, "name": companero.name, "jugada": jugada_dict(companero.jugada)}
            if companero
            else None
        ),
        "events": state.events,
        "winner": state.winner,
    }
