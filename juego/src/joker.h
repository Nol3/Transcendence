#ifndef JOKER_H
#define JOKER_H

#include "card.h"

#define MAX_JOKERS 5
#define SHOP_JOKER_COUNT 3
#define JOKER_BASE_PRICE 5

typedef enum {
    JOKER_PLUS_PAIR,       // +10 a parejas
    JOKER_DOUBLE_ACE,       // x2 si incluye As
    JOKER_RED_CARDS,        // +5 por carta roja
    JOKER_FLUSH_BONUS,      // x1.5 si todas son del mismo palo
    JOKER_COUNT
} JokerType;

typedef struct {
    JokerType type;
    int price;
    bool purchased;
    bool active;
    char name[48];
    char description[96];
} Joker;

typedef struct {
    Joker shopJokers[SHOP_JOKER_COUNT];
    Joker ownedJokers[MAX_JOKERS];
    int ownedCount;
    int money;
    int rerollCount;
    bool shopActive;
} JokerSystem;

void JokerSystemInit(JokerSystem* system);
void JokerSystemReset(JokerSystem* system);
void GenerateShopJokers(JokerSystem* system, int rngSeed);
void JokerSystemRerollShop(JokerSystem* system, int rngSeed);
void PurchaseJoker(JokerSystem* system, int shopIndex);
bool JokerSystemIsShopActive(JokerSystem* system);
void DeactivateAllJokers(JokerSystem* system);

int CalculateJokerBonus(JokerSystem* system, Card* cards, int count);

const char* GetJokerName(JokerType type);
const char* GetJokerDescription(JokerType type);
int GetJokerPrice(JokerType type);

#endif