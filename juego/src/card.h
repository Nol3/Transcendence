#ifndef CARD_H
#define CARD_H

#include <stdbool.h>
#include "raylib.h"

// Representación de una carta
typedef struct {
    int suit;    // 0=Hearts, 1=Diamonds, 2=Clubs, 3=Spades
    int rank;    // 1=Ace, 2-10, 11=Jack, 12=Queen, 13=King
    bool selected;
    bool hover;  // Ratón encima de la carta
    float hoverScale; // Escala actual por hover (para animación suave)
} Card;

// Palos
typedef enum {
    SUIT_HEARTS = 0,
    SUIT_DIAMONDS,
    SUIT_CLUBS,
    SUIT_SPADES,
    SUIT_COUNT
} Suit;

// Funciones de utilidad
const char* GetSuitSymbol(int suit);
const char* GetRankSymbol(int rank);
Color GetSuitColor(int suit);
void GetCardName(char* buffer, int bufferSize, Card* card);

// Baraja
typedef struct {
    Card cards[52];
    int count;
    int currentIndex;
} Deck;

void DeckInit(Deck* deck);
void DeckShuffle(Deck* deck);
Card DeckDraw(Deck* deck);
bool DeckIsEmpty(Deck* deck);

#endif // CARD_H
