#include "card_textures.h"
#include <stdio.h>
#include <string.h>

#if defined(PLATFORM_WEB)
#define ASSETS_PREFIX "/assets"
#else
#define ASSETS_PREFIX "assets"
#endif

// Nombres de palos para archivos
const char* SUIT_NAMES[4] = {"hearts", "diamonds", "clubs", "spades"};

// Nombres de valores para archivos
const char* RANK_NAMES[13] = {"ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king"};

const char* GetCardSetSuffix(CardSet set) {
    switch (set) {
        case CARD_SET_DEFAULT: return "";
        case CARD_SET_HIGH_CONTRAST: return "_hc";
        default: return "";
    }
}

bool LoadCardTexturesSet(CardTextures* textures, CardSet set) {
    // Primero descargar texturas existentes si hay
    if (textures->loaded) {
        UnloadCardTextures(textures);
    }
    
    memset(textures, 0, sizeof(CardTextures));
    textures->currentSet = set;
    
    printf("Loading card textures (set: BASIC 8-bit)...\n");
    
    int loaded = 0;
    int failed = 0;
    
    // Cargar las 52 cartas desde BASIC/8BitDeckN.png
    // Mapeo: suit 0-3 (hearts, diamonds, clubs, spades)
    // En las imgenes 8BitDeck, el orden de cada palo es 2, 3, 4... K, A.
    // Es decir, la imagen 1 es el 2, la imagen 12 es la K, y la imagen 13 es el As.
    // En nuestro cdigo, rank = 0 es As, y rank = 1..12 son 2..K.
    for (int suit = 0; suit < 4; suit++) {
        for (int rank = 0; rank < 13; rank++) {
            int imageRank;
            if (rank == 0) {
                // As es la carta nmero 13 en las imgenes
                imageRank = 13;
            } else {
                // El 2 (rank 1) es la imagen 1, el 3 (rank 2) es la imagen 2, etc.
                imageRank = rank;
            }
            
            int deckNumber = suit * 13 + imageRank;
            char filename[256];
            snprintf(filename, sizeof(filename), ASSETS_PREFIX "/cards/BASIC/8BitDeck%d.png", deckNumber);
            
            textures->cards[suit][rank] = LoadTexture(filename);
            
            if (textures->cards[suit][rank].id != 0) {
                loaded++;
            } else {
                failed++;
                printf("Failed to load: %s\n", filename);
            }
        }
    }
    
    // Cargar reverso desde BASIC/card_back.png
    textures->cardBack = LoadTexture(ASSETS_PREFIX "/cards/BASIC/card_back.png");
    
    if (textures->cardBack.id == 0) {
        printf("Warning: Failed to load card back from BASIC/card_back.png\n");
    } else {
        loaded++;
        printf("Card back loaded from BASIC/card_back.png\n");
    }
    
    textures->loaded = (loaded > 0);
    printf("Card textures loaded: %d success, %d failed\n", loaded, failed);
    return textures->loaded;
}

bool LoadCardTextures(CardTextures* textures) {
    return LoadCardTexturesSet(textures, CARD_SET_DEFAULT);
}

void UnloadCardTextures(CardTextures* textures) {
    if (!textures->loaded) return;
    
    for (int suit = 0; suit < 4; suit++) {
        for (int rank = 0; rank < 13; rank++) {
            if (textures->cards[suit][rank].id != 0) {
                UnloadTexture(textures->cards[suit][rank]);
            }
        }
    }
    
    if (textures->cardBack.id != 0) {
        UnloadTexture(textures->cardBack);
    }
    
    textures->loaded = false;
}

Texture2D GetCardTexture(CardTextures* textures, int suit, int rank) {
    if (!textures->loaded) return (Texture2D){0};
    if (suit < 0 || suit >= 4) return (Texture2D){0};
    if (rank < 1 || rank > 13) return (Texture2D){0};
    
    return textures->cards[suit][rank - 1];
}
