#include "poker_hand.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

const char* GetHandTypeName(HandType type) {
    switch (type) {
        case HAND_HIGH_CARD:       return "Carta Alta";
        case HAND_ONE_PAIR:        return "Pareja";
        case HAND_TWO_PAIR:        return "Doble Pareja";
        case HAND_THREE_OF_A_KIND: return "Trio";
        case HAND_STRAIGHT:        return "Escalera";
        case HAND_FLUSH:           return "Color";
        case HAND_FULL_HOUSE:      return "Full House";
        case HAND_FOUR_OF_A_KIND:  return "Poker";
        case HAND_STRAIGHT_FLUSH:  return "Escalera de Color";
        default: return "Desconocido";
    }
}

int GetHandBaseScore(HandType type) {
    switch (type) {
        case HAND_HIGH_CARD:       return 5;
        case HAND_ONE_PAIR:        return 10;
        case HAND_TWO_PAIR:        return 20;
        case HAND_THREE_OF_A_KIND: return 30;
        case HAND_STRAIGHT:        return 40;
        case HAND_FLUSH:           return 50;
        case HAND_FULL_HOUSE:      return 60;
        case HAND_FOUR_OF_A_KIND:  return 80;
        case HAND_STRAIGHT_FLUSH:  return 100;
        default: return 0;
    }
}

int CompareCards(const void* a, const void* b) {
    Card* cardA = (Card*)a;
    Card* cardB = (Card*)b;
    return cardB->rank - cardA->rank; // Orden descendente
}

void SortCardsByRank(Card* cards, int count) {
    qsort(cards, count, sizeof(Card), CompareCards);
}

// Contar ocurrencias de cada rango
void CountRanks(Card* cards, int count, int* rankCounts) {
    memset(rankCounts, 0, sizeof(int) * 14); // 1-13
    for (int i = 0; i < count; i++) {
        rankCounts[cards[i].rank]++;
    }
}

// Contar ocurrencias de cada palo
void CountSuits(Card* cards, int count, int* suitCounts) {
    memset(suitCounts, 0, sizeof(int) * 4);
    for (int i = 0; i < count; i++) {
        suitCounts[cards[i].suit]++;
    }
}

bool HasPair(Card* cards, int count, int* pairRank) {
    int rankCounts[14] = {0};
    CountRanks(cards, count, rankCounts);
    
    for (int r = 13; r >= 1; r--) {
        if (rankCounts[r] >= 2) {
            *pairRank = r;
            return true;
        }
    }
    return false;
}

bool HasTwoPair(Card* cards, int count, int* highPair, int* lowPair) {
    int rankCounts[14] = {0};
    CountRanks(cards, count, rankCounts);
    
    *highPair = 0;
    *lowPair = 0;
    
    for (int r = 13; r >= 1; r--) {
        if (rankCounts[r] >= 2) {
            if (*highPair == 0) {
                *highPair = r;
            } else if (*lowPair == 0) {
                *lowPair = r;
                return true;
            }
        }
    }
    return false;
}

bool HasThreeOfAKind(Card* cards, int count, int* trioRank) {
    int rankCounts[14] = {0};
    CountRanks(cards, count, rankCounts);
    
    for (int r = 13; r >= 1; r--) {
        if (rankCounts[r] >= 3) {
            *trioRank = r;
            return true;
        }
    }
    return false;
}

bool HasStraight(Card* cards, int count, int* highCard) {
    if (count < 5) return false;
    
    // Crear array de rangos únicos ordenados
    int uniqueRanks[14] = {0};
    int uniqueCount = 0;
    
    for (int i = 0; i < count && uniqueCount < 14; i++) {
        bool alreadyAdded = false;
        for (int j = 0; j < uniqueCount; j++) {
            if (uniqueRanks[j] == cards[i].rank) {
                alreadyAdded = true;
                break;
            }
        }
        if (!alreadyAdded) {
            uniqueRanks[uniqueCount++] = cards[i].rank;
        }
    }
    
    // Ordenar únicos
    for (int i = 0; i < uniqueCount - 1; i++) {
        for (int j = i + 1; j < uniqueCount; j++) {
            if (uniqueRanks[j] > uniqueRanks[i]) {
                int temp = uniqueRanks[i];
                uniqueRanks[i] = uniqueRanks[j];
                uniqueRanks[j] = temp;
            }
        }
    }
    
    // Buscar escalera (5 consecutivos)
    for (int i = 0; i <= uniqueCount - 5; i++) {
        bool isStraight = true;
        for (int j = 0; j < 4; j++) {
            if (uniqueRanks[i + j] - 1 != uniqueRanks[i + j + 1]) {
                isStraight = false;
                break;
            }
        }
        if (isStraight) {
            *highCard = uniqueRanks[i];
            return true;
        }
    }
    
    // Escalera baja (A-2-3-4-5)
    if (uniqueCount >= 5) {
        bool hasAce = false, has2 = false, has3 = false, has4 = false, has5 = false;
        for (int i = 0; i < uniqueCount; i++) {
            if (uniqueRanks[i] == 1) hasAce = true;
            if (uniqueRanks[i] == 2) has2 = true;
            if (uniqueRanks[i] == 3) has3 = true;
            if (uniqueRanks[i] == 4) has4 = true;
            if (uniqueRanks[i] == 5) has5 = true;
        }
        if (hasAce && has2 && has3 && has4 && has5) {
            *highCard = 5; // La escalera baja termina en 5
            return true;
        }
    }
    
    return false;
}

bool HasFlush(Card* cards, int count, int* suit) {
    int suitCounts[4] = {0};
    CountSuits(cards, count, suitCounts);
    
    for (int s = 0; s < 4; s++) {
        if (suitCounts[s] >= 5) {
            *suit = s;
            return true;
        }
    }
    return false;
}

bool HasFullHouse(Card* cards, int count, int* trioRank, int* pairRank) {
    int rankCounts[14] = {0};
    CountRanks(cards, count, rankCounts);
    
    *trioRank = 0;
    *pairRank = 0;
    
    // Buscar trío
    for (int r = 13; r >= 1; r--) {
        if (rankCounts[r] >= 3) {
            *trioRank = r;
            break;
        }
    }
    
    if (*trioRank == 0) return false;
    
    // Buscar pareja (diferente del trío)
    for (int r = 13; r >= 1; r--) {
        if (r != *trioRank && rankCounts[r] >= 2) {
            *pairRank = r;
            return true;
        }
    }
    
    return false;
}

bool HasFourOfAKind(Card* cards, int count, int* fourRank) {
    int rankCounts[14] = {0};
    CountRanks(cards, count, rankCounts);
    
    for (int r = 13; r >= 1; r--) {
        if (rankCounts[r] >= 4) {
            *fourRank = r;
            return true;
        }
    }
    return false;
}

bool HasStraightFlush(Card* cards, int count, int* highCard) {
    // Verificar cada palo
    for (int suit = 0; suit < 4; suit++) {
        // Extraer cartas de este palo
        Card suitedCards[7];
        int suitedCount = 0;
        
        for (int i = 0; i < count && suitedCount < 7; i++) {
            if (cards[i].suit == suit) {
                suitedCards[suitedCount++] = cards[i];
            }
        }
        
        if (suitedCount >= 5) {
            if (HasStraight(suitedCards, suitedCount, highCard)) {
                return true;
            }
        }
    }
    return false;
}

HandResult EvaluateHand(Card* cards, int count) {
    HandResult result = {0};
    result.type = HAND_HIGH_CARD;
    result.score = 0;
    strcpy(result.name, "Carta Alta");
    
    if (count == 0) return result;
    
    // Copiar y ordenar cartas
    Card sorted[7];
    memcpy(sorted, cards, sizeof(Card) * count);
    SortCardsByRank(sorted, count);
    memcpy(result.cards, sorted, sizeof(Card) * (count > 5 ? 5 : count));
    
    int tempRank1, tempRank2;
    
    // Verificar de mejor a peor
    if (HasStraightFlush(sorted, count, &tempRank1)) {
        result.type = HAND_STRAIGHT_FLUSH;
        result.score = GetHandBaseScore(result.type) + tempRank1;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasFourOfAKind(sorted, count, &tempRank1)) {
        result.type = HAND_FOUR_OF_A_KIND;
        result.score = GetHandBaseScore(result.type) + tempRank1;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasFullHouse(sorted, count, &tempRank1, &tempRank2)) {
        result.type = HAND_FULL_HOUSE;
        result.score = GetHandBaseScore(result.type) + tempRank1 * 10 + tempRank2;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasFlush(sorted, count, &tempRank1)) {
        result.type = HAND_FLUSH;
        result.score = GetHandBaseScore(result.type);
        // Sumar valor de cartas altas
        for (int i = 0; i < count && i < 5; i++) {
            if (sorted[i].suit == tempRank1) {
                result.score += sorted[i].rank;
            }
        }
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasStraight(sorted, count, &tempRank1)) {
        result.type = HAND_STRAIGHT;
        result.score = GetHandBaseScore(result.type) + tempRank1;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasThreeOfAKind(sorted, count, &tempRank1)) {
        result.type = HAND_THREE_OF_A_KIND;
        result.score = GetHandBaseScore(result.type) + tempRank1;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasTwoPair(sorted, count, &tempRank1, &tempRank2)) {
        result.type = HAND_TWO_PAIR;
        result.score = GetHandBaseScore(result.type) + tempRank1 + tempRank2;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    if (HasPair(sorted, count, &tempRank1)) {
        result.type = HAND_ONE_PAIR;
        result.score = GetHandBaseScore(result.type) + tempRank1;
        strcpy(result.name, GetHandTypeName(result.type));
        return result;
    }
    
    // Carta alta - sumar valor de la carta más alta
    result.score = GetHandBaseScore(HAND_HIGH_CARD) + sorted[0].rank;
    
    return result;
}
