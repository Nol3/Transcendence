#ifndef CARD_TEXTURES_H
#define CARD_TEXTURES_H

#include "raylib.h"

// Sets de cartas disponibles
typedef enum {
    CARD_SET_DEFAULT = 0,      // Cartas normales
    CARD_SET_HIGH_CONTRAST,    // Alto contraste (sufijo _hc)
    CARD_SET_COUNT
} CardSet;

// Texturas de cartas
typedef struct {
    Texture2D cards[4][13];  // [suit][rank-1]
    Texture2D cardBack;
    bool loaded;
    CardSet currentSet;
} CardTextures;

// Funciones
bool LoadCardTextures(CardTextures* textures);
bool LoadCardTexturesSet(CardTextures* textures, CardSet set);
void UnloadCardTextures(CardTextures* textures);
Texture2D GetCardTexture(CardTextures* textures, int suit, int rank);
const char* GetCardSetSuffix(CardSet set);

#endif // CARD_TEXTURES_H
