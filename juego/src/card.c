#include "card.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

const char* GetSuitSymbol(int suit) {
    switch (suit) {
        case SUIT_HEARTS:   return "♥";
        case SUIT_DIAMONDS: return "♦";
        case SUIT_CLUBS:    return "♣";
        case SUIT_SPADES:   return "♠";
        default: return "?";
    }
}

const char* GetRankSymbol(int rank) {
    static const char* ranks[] = {"?", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"};
    if (rank >= 1 && rank <= 13) return ranks[rank];
    return "?";
}

Color GetSuitColor(int suit) {
    if (suit == SUIT_HEARTS || suit == SUIT_DIAMONDS) {
        return RED;
    }
    return BLACK;
}

void GetCardName(char* buffer, int bufferSize, Card* card) {
    const char* suitName = "";
    switch (card->suit) {
        case SUIT_HEARTS:   suitName = "Corazones"; break;
        case SUIT_DIAMONDS: suitName = "Diamantes"; break;
        case SUIT_CLUBS:    suitName = "Treboles"; break;
        case SUIT_SPADES:   suitName = "Picas"; break;
    }
    
    const char* rankName = GetRankSymbol(card->rank);
    snprintf(buffer, bufferSize, "%s de %s", rankName, suitName);
}

void DeckInit(Deck* deck) {
    int index = 0;
    for (int suit = 0; suit < 4; suit++) {
        for (int rank = 1; rank <= 13; rank++) {
            deck->cards[index].suit = suit;
            deck->cards[index].rank = rank;
            deck->cards[index].selected = false;
            deck->cards[index].hover = false;
            deck->cards[index].hoverScale = 1.0f;
            index++;
        }
    }
    deck->count = 52;
    deck->currentIndex = 0;
}

void DeckShuffle(Deck* deck) {
    // Fisher-Yates shuffle
    srand((unsigned int)time(NULL));
    for (int i = deck->count - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        Card temp = deck->cards[i];
        deck->cards[i] = deck->cards[j];
        deck->cards[j] = temp;
    }
    deck->currentIndex = 0;
}

Card DeckDraw(Deck* deck) {
    if (deck->currentIndex < deck->count) {
        return deck->cards[deck->currentIndex++];
    }
    // Retorna carta inválida si la baraja está vacía
    Card empty = {-1, -1, false};
    return empty;
}

bool DeckIsEmpty(Deck* deck) {
    return deck->currentIndex >= deck->count;
}
