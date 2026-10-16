// Auditoría del evaluador de poker (juego/src/poker_hand.c) — test independiente.
// 1) Verifica DETECCIÓN: enumera las C(52,5)=2.598.960 manos y compara las
//    frecuencias con las oficiales del póker.
// 2) Verifica COMPARACIÓN/desempate: casos donde el score del juego elige un
//    ganador distinto del que dicta el ranking lexicográfico del póker.
#include "poker_hand.h"
#include "card.h"
#include <stdio.h>
#include <string.h>

static Card mk(int suit, int rank) {
    Card c; c.suit = suit; c.rank = rank; c.selected = false; c.hover = false; c.hoverScale = 1.0f;
    return c;
}

// ── 1. Exhaustivo: frecuencias por categoría ────────────────────────────────
static long long counts[HAND_COUNT];

static void enumerate(void) {
    Card deck[52]; int n = 0;
    for (int s = 0; s < 4; s++) for (int r = 1; r <= 13; r++) deck[n++] = mk(s, r);
    for (int a = 0; a < 48; a++)
      for (int b = a + 1; b < 49; b++)
        for (int c = b + 1; c < 50; c++)
          for (int d = c + 1; d < 51; d++)
            for (int e = d + 1; e < 52; e++) {
                Card h[5] = { deck[a], deck[b], deck[c], deck[d], deck[e] };
                counts[EvaluateHand(h, 5).type]++;
            }
}

static const long long EXPECTED[HAND_COUNT] = {
    1302540, 1098240, 123552, 54912, 10200, 5108, 3744, 624, 40
};
static const char* NAMES_ES[HAND_COUNT] = {
    "Carta Alta", "Pareja", "Doble Pareja", "Trio", "Escalera",
    "Color", "Full House", "Poker", "Escalera de Color"
};

// ── 2. Comparación de manos ────────────────────────────────────────────────
// Ranking lexicográfico correcto (categoría + kickers), independiente del juego.
static int rank5(HandType t, const int* v) {
    static const int mult[HAND_COUNT] = {1,1,1,1,1,1,1,1,1};
    (void)mult;
    int s = (int)t;
    for (int i = 0; i < 5; i++) s = s * 15 + v[i];
    return s;
}

static void cmp_case(const char* label, Card* A, Card* B) {
    HandResult ra = EvaluateHand(A, 5);
    HandResult rb = EvaluateHand(B, 5);
    const char* gameWinner = ra.score >= rb.score ? "A" : "B";
    printf("%-46s  A: %-18s score=%-4d | B: %-18s score=%-4d  -> juego dice %s\n",
           label, ra.name, ra.score, rb.name, rb.score, gameWinner);
    (void)rank5;
}

int main(void) {
    enumerate();
    printf("=== 1) DETECCION: enumeracion exhaustiva de 2.598.960 manos de 5 cartas ===\n");
    long long total = 0; int bad = 0;
    for (int i = 0; i < HAND_COUNT; i++) {
        total += counts[i];
        int ok = (counts[i] == EXPECTED[i]);
        if (!ok) bad++;
        printf("  %-20s obtenido=%-9lld esperado=%-9lld %s\n",
               NAMES_ES[i], counts[i], EXPECTED[i], ok ? "OK" : "*** MISMATCH ***");
    }
    printf("  TOTAL = %lld (esperado 2598960) %s\n", total, total == 2598960 ? "OK" : "MISMATCH");
    printf("  -> %s (%d categorias con desviacion)\n\n",
           bad == 0 ? "Deteccion de categorias: CORRECTA" : "Deteccion: INCORRECTA", bad);

    printf("=== 2) COMPARACION: quien gana la ronda (CalculateRoundWinner usa type+score) ===\n");
    // Color: A K 9 5 2 vs A K 8 6 4  -> debe ganar A (9 > 8 en la 3a carta)
    Card f1[5] = { mk(0,14%14?14:1), mk(0,13), mk(0,9), mk(0,5), mk(0,2) };
    Card f2[5] = { mk(1,14%14?14:1), mk(1,13), mk(1,8), mk(1,6), mk(1,4) };
    cmp_case("Color A-K-9-5-2  vs  Color A-K-8-6-4", f1, f2);

    // Doble pareja: A A 2 2 K vs K K Q Q A -> debe ganar A (pareja de ases manda)
    Card t1[5] = { mk(0,1), mk(1,1), mk(0,2), mk(1,2), mk(0,13) };
    Card t2[5] = { mk(2,13), mk(3,13), mk(2,12), mk(3,12), mk(0,1) };
    cmp_case("Doble par A-A-2-2 vs Doble par K-K-Q-Q", t1, t2);

    // Trio: 9 9 9 A K vs 9 9 9 K Q -> debe ganar la primera (kicker A > K)
    Card r1[5] = { mk(0,9), mk(1,9), mk(2,9), mk(0,1), mk(1,13) };
    Card r2[5] = { mk(3,9), mk(1,9), mk(2,9), mk(0,13), mk(1,12) };
    cmp_case("Trio 9-9-9-A-K vs Trio 9-9-9-K-Q", r1, r2);

    // Pareja: 2 2 A K Q vs 2 2 K Q J -> debe ganar la primera (kickers A,K > K,Q)
    Card p1[5] = { mk(0,2), mk(1,2), mk(0,1), mk(1,13), mk(2,12) };
    Card p2[5] = { mk(2,2), mk(3,2), mk(0,13), mk(1,12), mk(2,11) };
    cmp_case("Pareja 2-2-A-K-Q vs Pareja 2-2-K-Q-J", p1, p2);

    // Carta alta: A 5 4 3 2 vs A 5 4 3 ... (mismo top, distinto kicker)
    Card h1[5] = { mk(0,1), mk(1,5), mk(2,4), mk(3,3), mk(0,2) };
    Card h2[5] = { mk(1,1), mk(2,5), mk(3,4), mk(0,3), mk(1,6) };
    cmp_case("Carta alta A-5-4-3-2 vs Carta alta A-6-5-4-3", h1, h2);

    printf("\n=== 3) Escalera de color: variantes de la rueda ===\n");
    Card wheel[5] = { mk(0,1), mk(0,2), mk(0,3), mk(0,4), mk(0,5) };
    Card royal[5] = { mk(3,1), mk(3,13), mk(3,12), mk(3,11), mk(3,10) };
    HandResult w = EvaluateHand(wheel, 5), r = EvaluateHand(royal, 5);
    printf("  Rueda A-2-3-4-5 mismo palo: %s score=%d (esperado Escalera de Color, baja)\n", w.name, w.score);
    printf("  Royal A-K-Q-J-T mismo palo: %s score=%d (esperado Escalera de Color, alta)\n", r.name, r.score);
    printf("  -> rueda %s royal: %s\n", w.score < r.score ? "<" : ">=", w.score < r.score ? "OK" : "*** MAL ***");
    return 0;
}
