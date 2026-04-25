#ifndef POKER_HAND_H
#define POKER_HAND_H

#include "card.h"

// Tipos de manos de póker (de menor a mayor valor)
typedef enum {
    HAND_HIGH_CARD = 0,
    HAND_ONE_PAIR,
    HAND_TWO_PAIR,
    HAND_THREE_OF_A_KIND,
    HAND_STRAIGHT,
    HAND_FLUSH,
    HAND_FULL_HOUSE,
    HAND_FOUR_OF_A_KIND,
    HAND_STRAIGHT_FLUSH,
    HAND_COUNT
} HandType;

// Información de una mano evaluada
typedef struct {
    HandType type;
    int score;
    char name[32];
    Card cards[5];  // Las 5 cartas que forman la mano
} HandResult;

// Funciones de evaluación
HandResult EvaluateHand(Card* cards, int count);
const char* GetHandTypeName(HandType type);
int GetHandBaseScore(HandType type);

// Funciones auxiliares para detectar combinaciones
bool HasPair(Card* cards, int count, int* pairRank);
bool HasTwoPair(Card* cards, int count, int* highPair, int* lowPair);
bool HasThreeOfAKind(Card* cards, int count, int* trioRank);
bool HasStraight(Card* cards, int count, int* highCard);
bool HasFlush(Card* cards, int count, int* suit);
bool HasFullHouse(Card* cards, int count, int* trioRank, int* pairRank);
bool HasFourOfAKind(Card* cards, int count, int* fourRank);
bool HasStraightFlush(Card* cards, int count, int* highCard);

// Utilidades
void SortCardsByRank(Card* cards, int count);
int CompareCards(const void* a, const void* b);

#endif // POKER_HAND_H
