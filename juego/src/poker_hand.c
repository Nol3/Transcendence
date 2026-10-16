#include "poker_hand.h"
#include "lang.h"
#include <string.h>
#include <stdlib.h>

// El As (rank 1 en la baraja) se evalúa como la carta más alta (valor 14),
// salvo en la escalera baja A-2-3-4-5. Toda comparación y puntuación usa este
// valor, de modo que A-J-Q-K-A se detecta como escalera y el As gana al Rey.
static int RankValue(int rank) {
    return (rank == 1) ? 14 : rank;
}

const char* GetHandTypeName(HandType type) {
    switch (type) {
        case HAND_HIGH_CARD:       return T(STR_HAND_HIGH_CARD);
        case HAND_ONE_PAIR:        return T(STR_HAND_ONE_PAIR);
        case HAND_TWO_PAIR:        return T(STR_HAND_TWO_PAIR);
        case HAND_THREE_OF_A_KIND: return T(STR_HAND_THREE_KIND);
        case HAND_STRAIGHT:        return T(STR_HAND_STRAIGHT);
        case HAND_FLUSH:           return T(STR_HAND_FLUSH);
        case HAND_FULL_HOUSE:      return T(STR_HAND_FULL_HOUSE);
        case HAND_FOUR_OF_A_KIND:  return T(STR_HAND_FOUR_KIND);
        case HAND_STRAIGHT_FLUSH:  return T(STR_HAND_STRAIGHT_FLUSH);
        default:                   return T(STR_HAND_UNKNOWN);
    }
}

int GetHandBaseScore(HandType type) {
    switch (type) {
        case HAND_HIGH_CARD:       return 0;
        case HAND_ONE_PAIR:        return 100;
        case HAND_TWO_PAIR:        return 200;
        case HAND_THREE_OF_A_KIND: return 300;
        case HAND_STRAIGHT:        return 400;
        case HAND_FLUSH:           return 500;
        case HAND_FULL_HOUSE:      return 600;
        case HAND_FOUR_OF_A_KIND:  return 800;
        case HAND_STRAIGHT_FLUSH:  return 900;
        default:                   return 0;
    }
}

// Orden descendente por valor de carta (el As queda primero).
int CompareCards(const void* a, const void* b) {
    const Card* cardA = (const Card*)a;
    const Card* cardB = (const Card*)b;
    return RankValue(cardB->rank) - RankValue(cardA->rank);
}

void SortCardsByRank(Card* cards, int count) {
    qsort(cards, count, sizeof(Card), CompareCards);
}

// ========== CONTEO ==========

// Cuenta ocurrencias por valor de carta. counts debe tener 15 enteros; los
// índices útiles son 2..14 (el As ocupa el 14).
static void CountRanks(Card* cards, int count, int* counts) {
    memset(counts, 0, sizeof(int) * 15);
    for (int i = 0; i < count; i++) {
        counts[RankValue(cards[i].rank)]++;
    }
}

// Cuenta ocurrencias por palo. counts debe tener 4 enteros.
static void CountSuits(Card* cards, int count, int* counts) {
    memset(counts, 0, sizeof(int) * 4);
    for (int i = 0; i < count; i++) {
        counts[cards[i].suit]++;
    }
}

// ========== DETECCIÓN DE COMBINACIONES ==========

bool HasPair(Card* cards, int count, int* pairRank) {
    int counts[15];
    CountRanks(cards, count, counts);
    for (int r = 14; r >= 2; r--) {
        if (counts[r] >= 2) {
            *pairRank = r;
            return true;
        }
    }
    return false;
}

bool HasTwoPair(Card* cards, int count, int* highPair, int* lowPair) {
    int counts[15];
    CountRanks(cards, count, counts);

    *highPair = 0;
    *lowPair = 0;
    for (int r = 14; r >= 2; r--) {
        if (counts[r] >= 2) {
            if (*highPair == 0) {
                *highPair = r;
            } else {
                *lowPair = r;
                return true;
            }
        }
    }
    return false;
}

bool HasThreeOfAKind(Card* cards, int count, int* trioRank) {
    int counts[15];
    CountRanks(cards, count, counts);
    for (int r = 14; r >= 2; r--) {
        if (counts[r] >= 3) {
            *trioRank = r;
            return true;
        }
    }
    return false;
}

bool HasStraight(Card* cards, int count, int* highCard) {
    if (count < 5) return false;

    bool present[15] = {0};
    for (int i = 0; i < count; i++) {
        present[RankValue(cards[i].rank)] = true;
    }

    // Escaleras normales: cinco valores consecutivos, de la más alta a la más
    // baja (high = 6 cubre 2-3-4-5-6).
    for (int high = 14; high >= 6; high--) {
        bool run = true;
        for (int k = 0; k < 5; k++) {
            if (!present[high - k]) { run = false; break; }
        }
        if (run) {
            *highCard = high;
            return true;
        }
    }

    // Escalera baja (rueda): A-2-3-4-5, donde el As cuenta como 1.
    if (present[14] && present[2] && present[3] && present[4] && present[5]) {
        *highCard = 5;
        return true;
    }

    return false;
}

bool HasFlush(Card* cards, int count, int* suit) {
    int counts[4];
    CountSuits(cards, count, counts);
    for (int s = 0; s < 4; s++) {
        if (counts[s] >= 5) {
            *suit = s;
            return true;
        }
    }
    return false;
}

bool HasFullHouse(Card* cards, int count, int* trioRank, int* pairRank) {
    int counts[15];
    CountRanks(cards, count, counts);

    *trioRank = 0;
    *pairRank = 0;

    for (int r = 14; r >= 2; r--) {
        if (counts[r] >= 3) { *trioRank = r; break; }
    }
    if (*trioRank == 0) return false;

    for (int r = 14; r >= 2; r--) {
        if (r != *trioRank && counts[r] >= 2) {
            *pairRank = r;
            return true;
        }
    }
    return false;
}

bool HasFourOfAKind(Card* cards, int count, int* fourRank) {
    int counts[15];
    CountRanks(cards, count, counts);
    for (int r = 14; r >= 2; r--) {
        if (counts[r] >= 4) {
            *fourRank = r;
            return true;
        }
    }
    return false;
}

bool HasStraightFlush(Card* cards, int count, int* highCard) {
    for (int suit = 0; suit < 4; suit++) {
        Card suited[7];
        int suitedCount = 0;
        for (int i = 0; i < count && suitedCount < 7; i++) {
            if (cards[i].suit == suit) {
                suited[suitedCount++] = cards[i];
            }
        }
        if (suitedCount >= 5 && HasStraight(suited, suitedCount, highCard)) {
            return true;
        }
    }
    return false;
}

// ========== EVALUACIÓN ==========

// Rellena el desempate lexicográfico de póker de una mano ya clasificada.
// `r1`/`r2` son los valores que devolvieron los detectores para esa categoría
// (en el color, `r1` es el PALO, no un valor).
static void FillTiebreak(HandResult* res, const Card* sorted, int n, int r1, int r2) {
    int counts[15];
    memset(counts, 0, sizeof(counts));

    if (res->type == HAND_FLUSH) {
        // Para el color solo cuentan las cartas del palo del color; si no, al
        // evaluar más de 5 cartas se colarían valores de otros palos.
        for (int i = 0; i < n; i++) {
            if (sorted[i].suit == r1) counts[RankValue(sorted[i].rank)]++;
        }
    } else {
        for (int i = 0; i < n; i++) counts[RankValue(sorted[i].rank)]++;
    }

    int tb[5] = {0, 0, 0, 0, 0};
    int k = 0;

    switch (res->type) {
        case HAND_STRAIGHT_FLUSH:
        case HAND_STRAIGHT:
            // Cinco valores consecutivos desde el más alto. En la rueda
            // r1 == 5, así que el As queda como 1 sin caso especial.
            for (int i = 0; i < 5; i++) tb[i] = r1 - i;
            break;

        case HAND_FOUR_OF_A_KIND:
            tb[k++] = r1;                                   // póker
            for (int r = 14; r >= 2 && k < 5; r--)          // kicker
                if (r != r1 && counts[r]) tb[k++] = r;
            break;

        case HAND_FULL_HOUSE:
            tb[0] = r1;                                     // trío
            tb[1] = r2;                                     // pareja
            break;

        case HAND_FLUSH:
            for (int r = 14; r >= 2 && k < 5; r--)          // 5 cartas del palo
                if (counts[r]) tb[k++] = r;
            break;

        case HAND_THREE_OF_A_KIND:
            tb[k++] = r1;                                   // trío
            for (int r = 14; r >= 2 && k < 5; r--)          // 2 kickers
                if (r != r1 && counts[r]) tb[k++] = r;
            break;

        case HAND_TWO_PAIR:
            tb[0] = r1;                                     // pareja alta
            tb[1] = r2;                                     // pareja baja
            k = 2;
            for (int r = 14; r >= 2 && k < 5; r--)          // kicker
                if (r != r1 && r != r2 && counts[r]) tb[k++] = r;
            break;

        case HAND_ONE_PAIR:
            tb[k++] = r1;                                   // pareja
            for (int r = 14; r >= 2 && k < 5; r--)          // 3 kickers
                if (r != r1 && counts[r]) tb[k++] = r;
            break;

        default: // HAND_HIGH_CARD
            for (int r = 14; r >= 2 && k < 5; r--)          // 5 más altas
                if (counts[r]) tb[k++] = r;
            break;
    }

    memcpy(res->tiebreak, tb, sizeof(tb));
}

// Comparación de manos según las reglas del póker: categoría y, a igualdad de
// categoría, desempate carta a carta (kickers). El `score` aditivo de abajo
// sirve para la carrera de puntos del juego, NO para decidir quién gana la
// ronda: dos manos de la misma categoría pueden tener scores iguales o incluso
// invertidos (un color A-K-9-5-2 suma menos que A-K-8-6-4).
int CompareHands(const HandResult* a, const HandResult* b) {
    if (a->type != b->type) {
        return (a->type > b->type) ? 1 : -1;
    }
    for (int i = 0; i < 5; i++) {
        if (a->tiebreak[i] != b->tiebreak[i]) {
            return (a->tiebreak[i] > b->tiebreak[i]) ? 1 : -1;
        }
    }
    return 0;  // misma mano exacta
}

HandResult EvaluateHand(Card* cards, int count) {
    HandResult result = {0};
    result.type = HAND_HIGH_CARD;
    strcpy(result.name, GetHandTypeName(HAND_HIGH_CARD));

    if (count == 0) return result;

    // Copiar y ordenar (descendente por valor) sin tocar la mano original.
    Card sorted[7];
    int n = (count > 7) ? 7 : count;
    memcpy(sorted, cards, sizeof(Card) * n);
    SortCardsByRank(sorted, n);
    memcpy(result.cards, sorted, sizeof(Card) * (n > 5 ? 5 : n));

    // r1/r2 los rellenan los detectores según la categoría; se inicializan para
    // que FillTiebreak nunca reciba basura en las categorías que no usan r2.
    int rank1 = 0, rank2 = 0;

    // Se comprueba de la mejor mano a la peor; la primera que encaja gana.
    if (HasStraightFlush(sorted, n, &rank1)) {
        result.type = HAND_STRAIGHT_FLUSH;
        result.score = GetHandBaseScore(result.type) + rank1;
    } else if (HasFourOfAKind(sorted, n, &rank1)) {
        result.type = HAND_FOUR_OF_A_KIND;
        result.score = GetHandBaseScore(result.type) + rank1;
    } else if (HasFullHouse(sorted, n, &rank1, &rank2)) {
        result.type = HAND_FULL_HOUSE;
        result.score = GetHandBaseScore(result.type) + rank1 * 10 + rank2;
    } else if (HasFlush(sorted, n, &rank1)) {
        result.type = HAND_FLUSH;
        result.score = GetHandBaseScore(result.type);
        // Sumar el valor de hasta 5 cartas del palo del color.
        int added = 0;
        for (int i = 0; i < n && added < 5; i++) {
            if (sorted[i].suit == rank1) {
                result.score += RankValue(sorted[i].rank);
                added++;
            }
        }
    } else if (HasStraight(sorted, n, &rank1)) {
        result.type = HAND_STRAIGHT;
        result.score = GetHandBaseScore(result.type) + rank1;
    } else if (HasThreeOfAKind(sorted, n, &rank1)) {
        result.type = HAND_THREE_OF_A_KIND;
        result.score = GetHandBaseScore(result.type) + rank1;
    } else if (HasTwoPair(sorted, n, &rank1, &rank2)) {
        result.type = HAND_TWO_PAIR;
        result.score = GetHandBaseScore(result.type) + rank1 + rank2;
    } else if (HasPair(sorted, n, &rank1)) {
        result.type = HAND_ONE_PAIR;
        result.score = GetHandBaseScore(result.type) + rank1;
    } else {
        result.type = HAND_HIGH_CARD;
        result.score = GetHandBaseScore(HAND_HIGH_CARD) + RankValue(sorted[0].rank);
    }

    strcpy(result.name, GetHandTypeName(result.type));

    // Desempate de póker: sin esto, dos manos de la misma categoría se
    // comparaban por el score aditivo y ganaba el jugador equivocado.
    FillTiebreak(&result, sorted, n, rank1, rank2);

    return result;
}
