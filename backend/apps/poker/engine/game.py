"""Texas Hold'em sin límite, autoritativo y determinista.

Este módulo es **el árbitro**: baraja, reparte, valida cada acción y decide quién
gana. No importa Django ni hace E/S, así que se puede probar entero sin servidor.

Reglas implementadas:
- 2..6 asientos, botón rotatorio, ciegas pequeña/grande (heads-up: el botón pone la
  ciega pequeña y habla primero preflop).
- Cuatro calles: preflop, flop, turn, river.
- Acciones: fold, check, call, bet/raise (con apuesta mínima = última subida completa)
  y all-in.
- Un all-in **corto** (menor que la subida mínima) no reabre la acción para quien ya
  actuó: solo puede igualar o retirarse.
- Botes laterales: se devuelve la apuesta no igualada y se reparten los botes por
  niveles de aportación.
- Showdown con comparación lexicográfica de manos; reparto de botes divididos y
  asignación de la ficha impar al primer asiento a la izquierda del botón.
- Si todos se retiran menos uno, no hay showdown ni se muestran las cartas.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from .cards import Card, Deck
from .hand_eval import HandRank, evaluate

PREFLOP = 0
FLOP = 1
TURN = 2
RIVER = 3
COMPLETE = 4

STREET_NAMES = {PREFLOP: "preflop", FLOP: "flop", TURN: "turn", RIVER: "river",
                COMPLETE: "complete"}

FOLD = "fold"
CHECK = "check"
CALL = "call"
BET = "bet"
RAISE = "raise"
ALL_IN = "all_in"
AGGRESSIVE = (BET, RAISE, ALL_IN)

MIN_SEATS = 2
MAX_SEATS = 6


class IllegalAction(Exception):
    """La acción pedida no es legal en este momento."""


@dataclass
class Seat:
    index: int
    name: str
    stack: int
    hole: list[Card] = field(default_factory=list)
    folded: bool = False
    all_in: bool = False
    committed: int = 0        # aportado en la calle actual
    total: int = 0            # aportado en toda la mano
    is_bot: bool = False
    has_acted: bool = False   # ya actuó en la calle actual

    @property
    def in_hand(self) -> bool:
        return not self.folded

    @property
    def can_act(self) -> bool:
        return not self.folded and not self.all_in and self.stack > 0


class Hand:
    """Una mano completa de Texas Hold'em sin límite."""

    def __init__(
        self,
        stacks: Sequence[int],
        button: int = 0,
        small_blind: int = 1,
        big_blind: int = 2,
        names: Sequence[str] | None = None,
        deck_cards: Sequence[Card] | None = None,
        rng=None,
        bots: Iterable[int] = (),
    ):
        if not (MIN_SEATS <= len(stacks) <= MAX_SEATS):
            raise ValueError(f"se necesitan entre {MIN_SEATS} y {MAX_SEATS} asientos")
        if any(s <= 0 for s in stacks):
            raise ValueError("todos los asientos deben empezar con fichas")

        self.small_blind = small_blind
        self.big_blind = big_blind
        self.button = button % len(stacks)
        self.n_seats = len(stacks)
        self.seats = [
            Seat(index=i, name=(names[i] if names else f"Asiento {i + 1}"),
                 stack=stacks[i], is_bot=(i in set(bots)))
            for i in range(len(stacks))
        ]

        self.deck = Deck(cards=deck_cards, rng=rng)
        if deck_cards is None:
            self.deck.shuffle()

        self.street = PREFLOP
        self.board: list[Card] = []
        self.current_bet = 0
        self.last_full_raise = big_blind
        self.history: list[dict] = []
        self.result: dict | None = None
        self._pending: list[int] = []
        self._can_raise: set[int] = set()
        self._returned: dict[int, int] = {}   # apuestas no igualadas devueltas

    # ── Consultas ────────────────────────────────────────────────────────────
    @property
    def complete(self) -> bool:
        return self.street in (COMPLETE,)

    @property
    def pot_total(self) -> int:
        """Bote actual: la suma de lo aportado por todos.

        `_settle()` devuelve la apuesta no igualada restando de `total` (y sumando
        al stack de su dueño), así que aquí **no** hay que volver a restarla: hacerlo
        hacía desaparecer fichas del bote.
        """
        return sum(s.total for s in self.seats)

    @property
    def actor(self) -> int | None:
        return self._pending[0] if self._pending else None

    @property
    def active_seats(self) -> list[int]:
        return [s.index for s in self.seats if s.in_hand]

    @property
    def action_order(self) -> list[int]:
        return list(self._pending)

    def seat(self, index: int) -> Seat:
        return self.seats[index]

    # ── Arranque ─────────────────────────────────────────────────────────────
    def start(self) -> Hand:
        sb, bb = self._blind_seats()
        self._post_blind(sb, self.small_blind, "small_blind")
        self._post_blind(bb, self.big_blind, "big_blind")

        # Reparto: 2 cartas a cada asiento en orden (el reparto real va carta a
        # carta alrededor de la mesa; para la lógica es equivalente).
        for s in self.seats:
            s.hole = self.deck.draw(2)

        self.current_bet = max(s.committed for s in self.seats)
        self.last_full_raise = self.big_blind
        # Preflop habla primero el asiento a la izquierda de la ciega grande.
        bb_seat = self._blind_seats()[1]
        self._pending = [i for i in self._order_from(bb_seat) if self.seats[i].can_act]
        if self.seats[bb_seat].can_act:
            self._pending.append(bb_seat)   # el BB tiene la última opción preflop
        self._can_raise = set(self._pending)
        self._log({"event": "hand_start", "button": self.button, "sb": sb, "bb": bb,
                   "stacks": [s.stack for s in self.seats]})
        if not self._pending:
            # Ciegas que dejan a todos all-in: se reparten las calles de golpe.
            self._close_street()
        return self

    def _blind_seats(self) -> tuple[int, int]:
        if self.n_seats == 2:
            # Heads-up: el botón pone la ciega pequeña.
            return self.button, (self.button + 1) % self.n_seats
        return (self.button + 1) % self.n_seats, (self.button + 2) % self.n_seats

    def _post_blind(self, index: int, amount: int, label: str) -> None:
        s = self.seats[index]
        pay = min(amount, s.stack)
        s.stack -= pay
        s.committed += pay
        s.total += pay
        if s.stack == 0:
            s.all_in = True
        self._log({"event": "blind", "seat": index, "kind": label, "amount": pay})

    # ── Orden de acción ──────────────────────────────────────────────────────
    def _full_order_from(self, start: int) -> list[int]:
        """Los n asientos en orden circular empezando por el siguiente a `start`."""
        return [(start + k) % self.n_seats for k in range(1, self.n_seats + 1)]

    def _order_from(self, start: int, only_can_act: bool = True) -> list[int]:
        """Asientos a partir de `start`, **excluyéndolo**, en orden circular.

        Excluir el asiento de partida es clave: quien acaba de subir no vuelve a
        actuar hasta que otro lo haga (si no, podría resubir a sí mismo).
        """
        out = []
        for k in range(1, self.n_seats):
            i = (start + k) % self.n_seats
            s = self.seats[i]
            if s.folded:
                continue
            if only_can_act and not s.can_act:
                continue
            out.append(i)
        return out

    # ── Acciones legales ─────────────────────────────────────────────────────
    def legal_actions(self, seat_index: int | None = None) -> list[dict]:
        idx = self.actor if seat_index is None else seat_index
        if idx is None or self.complete:
            return []
        s = self.seats[idx]
        if not s.can_act:
            return []
        if seat_index is not None and idx != self.actor:
            # Fuera de turno: solo informativo, sin acciones.
            return []

        to_call = min(self.current_bet - s.committed, s.stack)
        options: list[dict] = [{"action": FOLD}]
        if to_call <= 0:
            options.append({"action": CHECK})
        else:
            # Si no le llega para igualar, el "call" consume todo su stack: es un
            # all-in por menos.
            options.append({"action": CALL, "amount": to_call})

        max_total = s.committed + s.stack
        min_total = self.current_bet + self.last_full_raise
        # Ir all-in ES subir: si la acción no está reabierta, no se puede shove.
        if idx in self._can_raise and max_total > to_call:
            if max_total < min_total:
                options.append({"action": ALL_IN, "amount": max_total})
            else:
                options.append({
                    "action": BET if self.current_bet == 0 else RAISE,
                    "min": min_total,
                    "max": max_total,
                })
                # Atajo explícito para la UI: shove por todo el stack.
                options.append({"action": ALL_IN, "amount": max_total})
        return options

    # ── Ejecución de una acción ──────────────────────────────────────────────
    def act(self, seat_index: int, action: str, amount: int | None = None) -> dict:
        if self.complete:
            raise IllegalAction("la mano ya ha terminado")
        if self.actor != seat_index:
            raise IllegalAction(f"no es el turno del asiento {seat_index}")

        s = self.seats[seat_index]
        action = action.lower()
        if action == "bet" and self.current_bet > 0:
            action = RAISE
        if action == "raise" and self.current_bet == 0:
            action = BET

        legal = {o["action"] for o in self.legal_actions()}
        if action not in legal:
            raise IllegalAction(f"acción {action!r} no permitida ahora: {sorted(legal)}")

        paid = 0
        aggressive = False

        if action == FOLD:
            s.folded = True
        elif action == CHECK:
            pass
        elif action == CALL:
            paid = min(self.current_bet - s.committed, s.stack)
            s.stack -= paid
            s.committed += paid
            s.total += paid
        elif action in (BET, RAISE):
            if amount is None:
                raise IllegalAction("bet/raise requiere 'amount' (total en la calle)")
            if amount > s.committed + s.stack:
                raise IllegalAction("no tienes tantas fichas")
            min_total = self.current_bet + self.last_full_raise
            if amount < min_total and amount != s.committed + s.stack:
                raise IllegalAction(f"la subida mínima es {min_total} (pediste {amount})")
            increment = amount - self.current_bet
            paid = amount - s.committed
            s.stack -= paid
            s.committed = amount
            s.total += paid
            if increment >= self.last_full_raise:
                self.last_full_raise = increment
                # Reabre la acción para los DEMÁS (quien sube no puede volver a
                # subir hasta que otro lo haga).
                self._can_raise = {i for i in self._order_from(seat_index)
                                   if self.seats[i].can_act}
            # Si es corta (all-in por menos de la subida mínima) NO se reabre:
            # quien ya actuó solo puede igualar o retirarse.
            self.current_bet = max(self.current_bet, s.committed)
            aggressive = True
        elif action == ALL_IN:
            paid = s.stack
            s.stack = 0
            s.committed += paid
            s.total += paid
            if s.committed > self.current_bet:
                increment = s.committed - self.current_bet
                if increment >= self.last_full_raise:
                    self.last_full_raise = increment
                    self._can_raise = {i for i in self._order_from(seat_index)
                                       if self.seats[i].can_act}
                self.current_bet = s.committed
                aggressive = True
        else:
            raise IllegalAction(f"acción desconocida: {action}")

        if s.stack == 0 and not s.folded:
            s.all_in = True
        s.has_acted = True
        self._log({"event": "action", "seat": seat_index, "action": action,
                   "amount": paid, "committed": s.committed, "street": STREET_NAMES[self.street]})

        self._advance(seat_index, aggressive)
        return self.history[-1]

    # ── Avance de la mano ────────────────────────────────────────────────────
    def _advance(self, actor_index: int, aggressive: bool) -> None:
        if len(self.active_seats) == 1:
            self._end_by_fold(self.active_seats[0])
            return

        if aggressive:
            # Una apuesta/subida reabre la acción para todos los que puedan actuar.
            self._pending = [i for i in self._order_from(actor_index) if self.seats[i].can_act]
        else:
            self._pending = [i for i in self._pending
                             if i != actor_index and self.seats[i].can_act]

        if not self._pending:
            self._close_street()

    def _close_street(self) -> None:
        """Cierra la calle. Si ya nadie puede actuar, reparte las que falten de golpe."""
        while self.street != RIVER:
            for s in self.seats:
                s.committed = 0
                s.has_acted = False
            self.current_bet = 0
            self.last_full_raise = self.big_blind
            self.street += 1

            self.deck.burn()
            if self.street == FLOP:
                self.board.extend(self.deck.draw(3))
            else:
                self.board.extend(self.deck.draw(1))
            self._log({"event": "street", "street": STREET_NAMES[self.street],
                       "board": [str(c) for c in self.board]})

            # Postflop habla primero el asiento a la izquierda del botón y el
            # botón cierra la ronda.
            self._pending = [i for i in self._order_from(self.button) if self.seats[i].can_act]
            if self.seats[self.button].can_act:
                self._pending.append(self.button)
            self._can_raise = set(self._pending)
            if self._pending:
                return  # hay acción en esta calle
            # Si no hay nadie que pueda actuar (todos all-in), seguir repartiendo.

        if len(self.active_seats) > 1:
            self._showdown()

    # ── Final de la mano ─────────────────────────────────────────────────────
    def _end_by_fold(self, winner_index: int) -> None:
        self._settle()
        w = self.seats[winner_index]
        won = self.pot_total
        w.stack += won
        self.street = COMPLETE
        self._pending = []
        self.result = {
            "showdown": False,
            "board": [str(c) for c in self.board],
            "pots": [{"amount": won, "winners": [
                {"seat": w.index, "name": w.name, "amount": won, "hand": None}]}],
            "total": won,
            "revealed": {},
            "stacks": [s.stack for s in self.seats],
        }
        self._log({"event": "hand_end", "winner": w.index, "amount": won, "showdown": False})

    def _settle(self) -> None:
        """Devuelve la apuesta no igualada antes de repartir botes."""
        totals = [s.total for s in self.seats]
        if not totals:
            return
        ordered = sorted(totals, reverse=True)
        if len(ordered) > 1 and ordered[0] > ordered[1]:
            for s in self.seats:
                if s.total == ordered[0]:
                    refund = s.total - ordered[1]
                    s.total -= refund
                    s.stack += refund
                    self._returned[s.index] = refund
                    self._log({"event": "uncalled_return", "seat": s.index, "amount": refund})
                    break

    def _showdown(self) -> None:
        self._settle()
        contenders = [i for i in self.active_seats]
        ranks: dict[int, HandRank] = {}
        for i in contenders:
            ranks[i] = evaluate(self.seats[i].hole + self.board)

        # Botes por niveles de aportación.
        contribs = [s.total for s in self.seats]
        levels = sorted({c for c in contribs if c > 0})
        pots = []
        prev = 0
        for level in levels:
            amount = 0
            eligible = []
            for s in self.seats:
                amount += min(s.total, level) - min(s.total, prev)
                if s.total >= level and s.in_hand:
                    eligible.append(s.index)
            if amount > 0:
                pots.append({"amount": amount, "eligible": eligible})
            prev = level

        payouts: dict[int, int] = {}
        pot_report = []
        for pot in pots:
            elig = pot["eligible"]
            if not elig:
                continue
            best = max(ranks[i] for i in elig)
            winners = [i for i in elig if ranks[i] == best]
            share, remainder = divmod(pot["amount"], len(winners))
            # La ficha impar va al primero a la izquierda del botón.
            order = self._full_order_from(self.button)
            winners_sorted = [i for i in order if i in winners]
            winners_report = []
            for n, i in enumerate(winners_sorted):
                got = share + (1 if n < remainder else 0)
                payouts[i] = payouts.get(i, 0) + got
                winners_report.append({
                    "seat": i, "name": self.seats[i].name,
                    "amount": got, "hand": ranks[i].name,
                })
            pot_report.append({"amount": pot["amount"], "winners": winners_report})

        for i, amount in payouts.items():
            self.seats[i].stack += amount

        self.street = COMPLETE
        self._pending = []
        self.result = {
            "showdown": True,
            "board": [str(c) for c in self.board],
            "pots": pot_report,
            "total": sum(p["amount"] for p in pot_report),
            # Claves **de texto**, no enteras: este resultado viaja por el channel
            # layer y con Redis se serializa con msgpack, que rechaza claves int
            # ("int is not allowed for map key"). El front ya las lee con
            # `String(seat)`, así que en JSON son lo mismo.
            "revealed": {str(i): [str(c) for c in self.seats[i].hole] for i in contenders},
            "hands": {str(i): {"name": ranks[i].name, "tiebreak": list(ranks[i].tiebreak)}
                      for i in contenders},
            "stacks": [s.stack for s in self.seats],
        }
        # `payouts` va con claves de texto: este evento entra en el estado que se
        # manda por el channel layer y msgpack no admite claves enteras.
        self._log({"event": "hand_end", "showdown": True, "pots": pot_report,
                   "payouts": {str(i): v for i, v in payouts.items()}})

    # ── Vista por jugador (clave para no filtrar cartas) ─────────────────────
    def state_for(self, seat_index: int | None) -> dict:
        """Estado que puede ver un asiento. Las cartas ajenas solo se revelan en showdown."""
        reveal = bool(self.result and self.result.get("showdown"))
        seats = []
        for s in self.seats:
            visible_hole = None
            if seat_index is not None and s.index == seat_index:
                visible_hole = [str(c) for c in s.hole]
            # Las claves de `revealed` son de texto (viajan por el channel layer).
            elif reveal and str(s.index) in (self.result or {}).get("revealed", {}):
                visible_hole = self.result["revealed"][str(s.index)]
            seats.append({
                "index": s.index,
                "name": s.name,
                "stack": s.stack,
                "committed": s.committed,
                "folded": s.folded,
                "all_in": s.all_in,
                "is_bot": s.is_bot,
                "hole": visible_hole,
                "hole_count": len(s.hole),
            })
        return {
            "street": STREET_NAMES[self.street],
            "board": [str(c) for c in self.board],
            "pot": self.pot_total,
            "button": self.button,
            "current_bet": self.current_bet,
            "min_raise_to": self.current_bet + self.last_full_raise,
            "actor": self.actor,
            "seats": seats,
            "legal_actions": self.legal_actions(seat_index) if seat_index == self.actor else [],
            "complete": self.complete,
            "result": self.result,
            "history": self.history,
        }

    # ── Utilidades ───────────────────────────────────────────────────────────
    def _log(self, event: dict) -> None:
        self.history.append(event)

    def __repr__(self) -> str:
        return (f"<Hand street={STREET_NAMES[self.street]} pot={self.pot_total} "
                f"board={' '.join(str(c) for c in self.board) or '-'} actor={self.actor}>")
