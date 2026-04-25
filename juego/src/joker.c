#include "joker.h"
#include <string.h>
#include <stdlib.h>

const char* GetJokerName(JokerType type) {
    switch (type) {
        case JOKER_PLUS_PAIR:      return "Emparejador";
        case JOKER_DOUBLE_ACE:     return "As Dorado";
        case JOKER_RED_CARDS:      return "Corazon Rojo";
        case JOKER_FLUSH_BONUS:    return "Colorito";
        default:                   return "???";
    }
}

const char* GetJokerDescription(JokerType type) {
    switch (type) {
        case JOKER_PLUS_PAIR:      return "+10 pts por cada Pareja";
        case JOKER_DOUBLE_ACE:     return "x2 si la mano incluye un As";
        case JOKER_RED_CARDS:      return "+5 pts por cada carta roja";
        case JOKER_FLUSH_BONUS:    return "x1.5 si todas son del mismo palo";
        default:                   return "";
    }
}

int GetJokerPrice(JokerType type) {
    switch (type) {
        case JOKER_PLUS_PAIR:      return 5;
        case JOKER_DOUBLE_ACE:     return 8;
        case JOKER_RED_CARDS:      return 4;
        case JOKER_FLUSH_BONUS:    return 7;
        default:                   return 5;
    }
}

void JokerSystemInit(JokerSystem* system) {
    memset(system, 0, sizeof(JokerSystem));
    system->money = 10;
    system->shopActive = false;
}

void JokerSystemReset(JokerSystem* system) {
    memset(system, 0, sizeof(JokerSystem));
    system->money = 10;
    system->shopActive = false;
}

void GenerateShopJokers(JokerSystem* system, int rngSeed) {
    srand((unsigned int)rngSeed);
    JokerType pool[JOKER_COUNT];
    for (int i = 0; i < JOKER_COUNT; i++) pool[i] = i;
    for (int i = JOKER_COUNT - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        JokerType tmp = pool[i];
        pool[i] = pool[j];
        pool[j] = tmp;
    }
    for (int i = 0; i < SHOP_JOKER_COUNT; i++) {
        system->shopJokers[i].type = pool[i];
        system->shopJokers[i].price = GetJokerPrice(pool[i]);
        system->shopJokers[i].purchased = false;
        system->shopJokers[i].active = false;
        strncpy(system->shopJokers[i].name, GetJokerName(pool[i]), 47);
        system->shopJokers[i].name[47] = '\0';
        strncpy(system->shopJokers[i].description, GetJokerDescription(pool[i]), 95);
        system->shopJokers[i].description[95] = '\0';
    }
    system->shopActive = true;
}

void JokerSystemRerollShop(JokerSystem* system, int rngSeed) {
    if (system->money < 1) return;
    system->money -= 1;
    GenerateShopJokers(system, rngSeed);
}

void PurchaseJoker(JokerSystem* system, int shopIndex) {
    if (shopIndex < 0 || shopIndex >= SHOP_JOKER_COUNT) return;
    if (system->shopJokers[shopIndex].purchased) return;
    if (system->ownedCount >= MAX_JOKERS) return;
    if (system->money < system->shopJokers[shopIndex].price) return;

    system->money -= system->shopJokers[shopIndex].price;
    system->shopJokers[shopIndex].purchased = true;
    system->shopJokers[shopIndex].active = true;
    system->ownedJokers[system->ownedCount] = system->shopJokers[shopIndex];
    system->ownedCount++;
}

bool JokerSystemIsShopActive(JokerSystem* system) {
    return system->shopActive;
}

void DeactivateAllJokers(JokerSystem* system) {
    for (int i = 0; i < system->ownedCount; i++) {
        system->ownedJokers[i].active = false;
    }
}

int CalculateJokerBonus(JokerSystem* system, Card* cards, int count) {
    int bonus = 0;
    float multiplier = 1.0f;

    for (int i = 0; i < system->ownedCount; i++) {
        if (!system->ownedJokers[i].active) continue;
        switch (system->ownedJokers[i].type) {
            case JOKER_PLUS_PAIR: {
                int rankCounts[14] = {0};
                for (int j = 0; j < count; j++) rankCounts[cards[j].rank]++;
                for (int r = 1; r <= 13; r++) {
                    if (rankCounts[r] >= 2) bonus += 10;
                }
                break;
            }
            case JOKER_DOUBLE_ACE: {
                for (int j = 0; j < count; j++) {
                    if (cards[j].rank == 1) {
                        multiplier *= 2.0f;
                        break;
                    }
                }
                break;
            }
            case JOKER_RED_CARDS: {
                for (int j = 0; j < count; j++) {
                    if (cards[j].suit == SUIT_HEARTS || cards[j].suit == SUIT_DIAMONDS) {
                        bonus += 5;
                    }
                }
                break;
            }
            case JOKER_FLUSH_BONUS: {
                if (count >= 2) {
                    int suit = cards[0].suit;
                    bool sameSuit = true;
                    for (int j = 1; j < count; j++) {
                        if (cards[j].suit != suit) {
                            sameSuit = false;
                            break;
                        }
                    }
                    if (sameSuit) multiplier *= 1.5f;
                }
                break;
            }
            default:
                break;
        }
    }

    return (int)((bonus + 0) * multiplier);
}