"""Integración del póker online con el resto del proyecto.

Cuando termina una partida, **el servidor** (no el navegador) escribe el resultado:
queda en el historial de partidas y, si los dos jugadores son humanos, se actualiza
el ELO y el balance de victorias/derrotas.

Las partidas contra un bot se guardan en el historial pero **no puntúan**: inflar el
ranking ganando a bots sería hacer trampa con el propio ranking.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Nombres de los bots (deben coincidir con los de `consumers.BOT_NAMES`).
BOT_PREFIX = "Bot "


def _report_sync(table) -> dict | None:
    """Escribe el resultado de una partida de póker. Devuelve un resumen o None."""
    from django.contrib.auth.models import User

    from apps.games.models import Game
    from apps.games.services import finish_game, get_ai_opponent

    human_seats = [s for s in table.seats if not s.is_bot and s.user_id]
    if not human_seats:
        return None

    # Para el modelo Game hacen falta dos usuarios: si el rival es un bot (o no hay
    # rival humano), se usa la cuenta interna del bot.
    me = human_seats[0]
    rival = next((s for s in table.seats if s is not me), None)
    player1 = User.objects.filter(pk=me.user_id).first()
    if player1 is None:
        return None
    if rival is not None and rival.user_id:
        player2 = User.objects.filter(pk=rival.user_id).first() or get_ai_opponent()
    else:
        player2 = get_ai_opponent()

    # El ELO del proyecto es 1v1: en una mesa de 3–6 humanos el resultado se guarda
    # en el historial pero no puntúa (el modelo no representa un ganador de N).
    rated = bool(rival is not None and rival.user_id and not rival.is_bot
                 and len(human_seats) == 2)

    winner = None
    if table.winner is not None:                      # None = empate
        winner = player1 if table.winner.user_id == me.user_id else player2

    # rated=True solo cuando los dos son humanos: este resultado lo decide el
    # servidor (la mesa), no el navegador.
    game = Game.objects.create(player1=player1, player2=player2, status="in_progress",
                               rated=rated)
    finish_game(
        game,
        winner=winner,
        player1_score=me.stack,
        player2_score=rival.stack if rival is not None else 0,
        rated=rated,
    )
    manos = _save_hands(game, table)
    resumen = {
        "game_id": game.id,
        "rated": rated,
        "winner": winner.username if winner else None,
        "hands": manos,
    }
    torneo = _close_tournament_match(table)
    if torneo:
        resumen.update(torneo)
    return resumen


def _save_hands(game, table) -> int:
    """Guarda el historial de manos de la partida. Devuelve cuántas se guardaron."""
    from .models import PokerHandPlayer, PokerHandRecord

    resumenes = getattr(table, "hands", None) or []
    for resumen in resumenes:
        mano = PokerHandRecord.objects.create(
            game=game,
            table_id=table.id,
            hand_number=resumen["hand_number"],
            board=resumen["board"],
            pot=resumen["pot"],
            showdown=resumen["showdown"],
            winner_names=resumen["winner_names"],
            actions=resumen.get("actions") or [],
        )
        PokerHandPlayer.objects.bulk_create([
            PokerHandPlayer(
                hand=mano,
                user_id=j["user_id"],
                seat=j["seat"],
                name=j["name"],
                is_bot=j["is_bot"],
                hole=j["hole"],
                hand_name=j["hand_name"],
                stack_after=j["stack_after"],
                won=j["won"],
                folded=j["folded"],
            )
            for j in resumen["players"]
        ])
    return len(resumenes)


def _close_tournament_match(table) -> dict | None:
    """Si la mesa es de un match de torneo, lo cierra el **servidor**.

    Esta es la vía fuerte: el ganador no lo declara ningún jugador, sale del estado
    real de la mesa, así que el bracket avanza sin pedir confirmación a nadie.
    """
    match_id = (getattr(table, "context", None) or {}).get("match_id")
    if not match_id or table.winner is None:
        return None

    from apps.tournament.models import TournamentMatch
    from apps.tournament.services import report_match_result

    match = (
        TournamentMatch.objects.filter(pk=match_id)
        .select_related("player1", "player2", "round", "tournament")
        .first()
    )
    if match is None or match.player2_id is None:
        return None
    if match.status == "completed":
        return {"tournament_match": match.id, "already_completed": True}

    ganador_id = table.winner.user_id
    if ganador_id not in (match.player1_id, match.player2_id):
        logger.warning("Póker: el ganador de la mesa no juega el match %s", match_id)
        return None

    slot = 1 if ganador_id == match.player1_id else 2
    # Los marcadores se mapean por usuario, no por asiento: el orden de la mesa y
    # el del bracket no tienen por qué coincidir.
    fichas = {s.user_id: s.stack for s in table.seats if s.user_id}
    report_match_result(
        match,
        winner_slot=slot,
        player1_score=fichas.get(match.player1_id, 0),
        player2_score=fichas.get(match.player2_id, 0),
    )
    logger.info("Torneo: match %s cerrado por el servidor (gana el asiento %s)", match.id, slot)
    return {"tournament_match": match.id, "winner_slot": slot, "closed_by": "server"}


async def report_match_end(table) -> None:
    """Hook `on_match_end` de la mesa: se ejecuta al acabar la partida."""
    from asgiref.sync import sync_to_async

    try:
        summary = await sync_to_async(_report_sync, thread_sensitive=True)(table)
        if summary:
            logger.info("Póker: resultado registrado %s", summary)
    except Exception:                                  # nunca tumbar la partida por esto
        logger.exception("Póker: no se pudo registrar el resultado de la partida")
