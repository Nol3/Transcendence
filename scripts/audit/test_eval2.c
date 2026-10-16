// Verificación del arreglo de comparación de manos.
//  A) Regresión: las frecuencias de categorías deben seguir siendo exactas.
//  B) Invariantes del desempate sobre las 2.598.960 manos (derivadas del
//     multiconjunto real de rangos, independientes del código de desempate).
//  C) Casos de regresión: los 5 enfrentamientos que antes daban mal ganador.
//  D) Enfrentamientos clásicos con ganador conocido.
//  E) Propiedades: antisimetría y transitividad de CompareHands.
#include "poker_hand.h"
#include "card.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static Card mk(int suit, int rank) {
    Card c; c.suit = suit; c.rank = rank; c.selected = false; c.hover = false; c.hoverScale = 1.0f;
    return c;
}
static int cmp_desc(const void* a, const void* b) { return *(const int*)b - *(const int*)a; }

static long long counts[HAND_COUNT];
static const long long EXPECTED[HAND_COUNT] = {
    1302540, 1098240, 123552, 54912, 10200, 5108, 3744, 624, 40
};
static const char* CAT_ES[HAND_COUNT] = {
    "Carta Alta", "Pareja", "Doble Pareja", "Trio", "Escalera",
    "Color", "Full House", "Poker", "Escalera de Color"
};

static long long invariant_failures = 0;
static long long tb_zero_failures = 0;
static char first_failure[256] = "";

#define FAIL(msg) do { \
    if (invariant_failures == 0) { \
        snprintf(first_failure, sizeof(first_failure), \
                 "%s | %s t=%d tb=[%d,%d,%d,%d,%d] ranks=[%d,%d,%d,%d,%d]", \
                 msg, CAT_ES[res->type], res->type, tb[0], tb[1], tb[2], tb[3], tb[4], \
                 ranks[0], ranks[1], ranks[2], ranks[3], ranks[4]); \
    } \
    invariant_failures++; return; \
} while (0)

// El desempate debe describir EXACTAMENTE las cartas reales de la mano.
static void check_invariants(Card* h, HandResult* res) {
    int ranks[5];
    for (int i = 0; i < 5; i++) ranks[i] = (h[i].rank == 1) ? 14 : h[i].rank;
    qsort(ranks, 5, sizeof(int), cmp_desc);
    int cnt[15]; memset(cnt, 0, sizeof(cnt));
    for (int i = 0; i < 5; i++) cnt[ranks[i]]++;

    int tb[5]; memcpy(tb, res->tiebreak, sizeof(tb));

    // El primer valor del desempate nunca puede ser 0 (carta inexistente).
    if (tb[0] <= 0) tb_zero_failures++;

    switch (res->type) {
        case HAND_HIGH_CARD:
            if (memcmp(tb, ranks, sizeof(ranks)) != 0) FAIL("carta alta: tb != rangos");
            break;

        case HAND_ONE_PAIR: {
            if (cnt[tb[0]] != 2) FAIL("pareja: tb[0] no aparece 2 veces");
            int rest[3], k = 0;
            for (int r = 14; r >= 2 && k < 3; r--) if (r != tb[0] && cnt[r]) rest[k++] = r;
            if (k != 3 || rest[0] != tb[1] || rest[1] != tb[2] || rest[2] != tb[3] || tb[4] != 0)
                FAIL("pareja: kickers mal");
            break;
        }
        case HAND_TWO_PAIR: {
            if (cnt[tb[0]] != 2 || cnt[tb[1]] != 2 || tb[0] <= tb[1]) FAIL("doble pareja: parejas mal");
            int kk = -1;
            for (int r = 14; r >= 2; r--) if (r != tb[0] && r != tb[1] && cnt[r]) { kk = r; break; }
            if (kk != tb[2] || tb[3] != 0 || tb[4] != 0) FAIL("doble pareja: kicker mal");
            break;
        }
        case HAND_THREE_OF_A_KIND: {
            if (cnt[tb[0]] != 3) FAIL("trio: tb[0] no aparece 3 veces");
            int rest[2], k = 0;
            for (int r = 14; r >= 2 && k < 2; r--) if (r != tb[0] && cnt[r]) rest[k++] = r;
            if (k != 2 || rest[0] != tb[1] || rest[1] != tb[2] || tb[3] != 0 || tb[4] != 0)
                FAIL("trio: kickers mal");
            break;
        }
        case HAND_STRAIGHT:
        case HAND_STRAIGHT_FLUSH: {
            int high = tb[0];
            int wheel = (high == 5 && cnt[14] && cnt[2] && cnt[3] && cnt[4] && cnt[5]);
            for (int i = 0; i < 5; i++) if (tb[i] != high - i) FAIL("escalera: tb no consecutivo");
            if (wheel) { if (tb[4] != 1) FAIL("rueda: el As debe valer 1"); break; }
            for (int i = 0; i < 5; i++) if (!cnt[high - i]) FAIL("escalera: falta una carta del run");
            break;
        }
        case HAND_FLUSH: {
            for (int i = 0; i < 5; i++) if (h[i].suit != h[0].suit) FAIL("color: palos distintos");
            if (memcmp(tb, ranks, sizeof(ranks)) != 0) FAIL("color: tb != rangos");
            break;
        }
        case HAND_FULL_HOUSE:
            if (cnt[tb[0]] != 3 || cnt[tb[1]] != 2) FAIL("full house: trio/pareja mal");
            break;

        case HAND_FOUR_OF_A_KIND: {
            if (cnt[tb[0]] != 4) FAIL("poker: tb[0] no aparece 4 veces");
            int kk = -1;
            for (int r = 14; r >= 2; r--) if (r != tb[0] && cnt[r]) { kk = r; break; }
            if (kk != tb[1] || tb[2] || tb[3] || tb[4]) FAIL("poker: kicker mal");
            break;
        }
        default: break;
    }
}

static long long prop_failures = 0;

static void enumerate(void) {
    Card deck[52]; int n = 0;
    for (int s = 0; s < 4; s++) for (int r = 1; r <= 13; r++) deck[n++] = mk(s, r);
    Card samples[64][5]; int ns = 0;
    long long idx = 0;
    for (int a = 0; a < 48; a++)
      for (int b = a + 1; b < 49; b++)
        for (int c = b + 1; c < 50; c++)
          for (int d = c + 1; d < 51; d++)
            for (int e = d + 1; e < 52; e++) {
                Card h[5] = { deck[a], deck[b], deck[c], deck[d], deck[e] };
                HandResult r = EvaluateHand(h, 5);
                counts[r.type]++;
                check_invariants(h, &r);
                // Propiedades: antisimetría y transitividad sobre una muestra.
                if ((idx % 40961) == 0 && ns < 64) {
                    memcpy(samples[ns], h, sizeof(h));
                    ns++;
                }
                idx++;
            }
    // Propiedades sobre la muestra (pares y tríos).
    for (int i = 0; i < ns; i++)
      for (int j = 0; j < ns; j++) {
        HandResult A = EvaluateHand(samples[i], 5), B = EvaluateHand(samples[j], 5);
        int ab = CompareHands(&A, &B), ba = CompareHands(&B, &A);
        if ((ab > 0 && ba >= 0) || (ab < 0 && ba <= 0) || (ab == 0 && ba != 0)) prop_failures++;
        for (int k = 0; k < ns; k++) {
            HandResult C = EvaluateHand(samples[k], 5);
            int ac = CompareHands(&A, &C), bc = CompareHands(&B, &C);
            if (ab > 0 && bc >= 0 && ac <= 0) prop_failures++;   // A>B, B>=C pero A<=C
            if (ab == 0 && ac != bc) prop_failures++;            // iguales => mismo orden frente a C
        }
      }
}

// ── Enfrentamientos: se espera que gane el PRIMERO ─────────────────────────
static int case_failures = 0;
static void duel(const char* label, Card* A, Card* B, const char* expect) {
    HandResult ra = EvaluateHand(A, 5), rb = EvaluateHand(B, 5);
    int c = CompareHands(&ra, &rb);
    const char* win = c > 0 ? "A" : (c < 0 ? "B" : "EMPATE");
    int ok = (strcmp(win, expect) == 0);
    if (!ok) case_failures++;
    printf("  [%s] %-42s %s(%d) vs %s(%d) -> gana %s (esperado %s)\n",
           ok ? "OK" : "MAL", label, ra.name, ra.score, rb.name, rb.score, win, expect);
}

int main(void) {
    enumerate();
    printf("=== A) Frecuencias (regresion) ===\n");
    int bad = 0;
    for (int i = 0; i < HAND_COUNT; i++) if (counts[i] != EXPECTED[i]) { bad++; printf("  MAL %s\n", CAT_ES[i]); }
    printf("  %s\n\n", bad ? "DESVIACION" : "9/9 categorias exactas (2598960 manos)");

    printf("=== B) Invariantes del desempate sobre todas las manos ===\n");
    printf("  violaciones: %lld   (tb[0]<=0: %lld)\n", invariant_failures, tb_zero_failures);
    if (first_failure[0]) printf("  primer fallo: %s\n", first_failure);
    printf("  %s\n\n", invariant_failures == 0 ? "desempate coherente con las cartas" : "DESEMPATE INCOHERENTE");

    printf("=== C) Casos que ANTES daban ganador equivocado ===\n");
    Card f1[5] = { mk(0,1), mk(0,13), mk(0,9), mk(0,5), mk(0,2) };
    Card f2[5] = { mk(1,1), mk(1,13), mk(1,8), mk(1,6), mk(1,4) };
    duel("Color A-K-9-5-2 vs Color A-K-8-6-4", f1, f2, "A");
    Card t1[5] = { mk(0,1), mk(1,1), mk(0,2), mk(1,2), mk(0,13) };
    Card t2[5] = { mk(2,13), mk(3,13), mk(2,12), mk(3,12), mk(0,1) };
    duel("Doble par A-A-2-2 vs Doble par K-K-Q-Q", t1, t2, "A");
    Card r1[5] = { mk(0,9), mk(1,9), mk(2,9), mk(0,1), mk(1,13) };
    Card r2[5] = { mk(3,9), mk(1,9), mk(2,9), mk(0,13), mk(1,12) };
    duel("Trio 9-9-9-A-K vs Trio 9-9-9-K-Q", r1, r2, "A");
    Card p1[5] = { mk(0,2), mk(1,2), mk(0,1), mk(1,13), mk(2,12) };
    Card p2[5] = { mk(2,2), mk(3,2), mk(0,13), mk(1,12), mk(2,11) };
    duel("Pareja 2-2-A-K-Q vs Pareja 2-2-K-Q-J", p1, p2, "A");
    Card h1[5] = { mk(0,1), mk(1,5), mk(2,4), mk(3,3), mk(0,2) };
    Card h2[5] = { mk(1,1), mk(2,5), mk(3,4), mk(0,3), mk(1,6) };
    duel("Carta alta A-5-4-3-2 vs A-6-5-4-3", h1, h2, "A");

    printf("\n=== D) Enfrentamientos clasicos ===\n");
    Card royal[5]  = { mk(3,1), mk(3,13), mk(3,12), mk(3,11), mk(3,10) };
    Card quad[5]   = { mk(0,9), mk(1,9), mk(2,9), mk(3,9), mk(0,2) };
    Card fh[5]     = { mk(0,13), mk(1,13), mk(2,13), mk(0,2), mk(1,2) };
    Card wheel[5]  = { mk(2,1), mk(0,2), mk(1,3), mk(2,4), mk(3,5) };
    Card six_high[5] = { mk(0,6), mk(1,5), mk(2,4), mk(3,3), mk(0,2) };
    Card quads_2[5] = { mk(0,2), mk(1,2), mk(2,2), mk(3,2), mk(0,1) };
    Card fh_low[5] = { mk(0,3), mk(1,3), mk(2,3), mk(0,1), mk(1,1) };
    duel("Escalera de color real vs Poker de 9", royal, quad, "A");
    duel("Poker de 9 vs Full de K", quad, fh, "A");
    duel("Full de K vs Escalera al 6", fh, six_high, "A");
    duel("Escalera al 6 vs Rueda A-2-3-4-5", six_high, wheel, "A");
    duel("Rueda vs Full bajo 3-3-3-A-A", wheel, fh_low, "B");
    duel("Poker de 2 con As vs Full de K", quads_2, fh, "A");
    Card tp_big[5] = { mk(0,1), mk(1,1), mk(2,13), mk(3,13), mk(0,12) };
    Card pair_a[5] = { mk(2,1), mk(3,1), mk(0,12), mk(1,11), mk(2,10) };
    duel("Doble pareja A-A-K-K vs Pareja de ases", tp_big, pair_a, "A");

    printf("\n=== E) Propiedades (antisimetria/transitividad) ===\n");
    printf("  violaciones: %lld  %s\n\n", prop_failures, prop_failures == 0 ? "OK" : "*** MAL ***");

    int total_fails = bad + (invariant_failures ? 1 : 0) + (tb_zero_failures ? 1 : 0)
                    + case_failures + (prop_failures ? 1 : 0);
    printf("================ RESULTADO: %s (%d fallos) ================\n",
           total_fails == 0 ? "TODO CORRECTO" : "HAY FALLOS", total_fails);
    return total_fails == 0 ? 0 : 1;
}
