#ifndef RENDERER_H
#define RENDERER_H

#include "card.h"
#include "game.h"
#include "poker_hand.h"
#include "card_textures.h"
#include "joker.h"

// Dimensiones de cartas (basadas en los sprites extraídos: 71x95)
#define CARD_WIDTH 71
#define CARD_HEIGHT 95
#define CARD_SPACING 15
#define CARD_CORNER_RADIUS 6

// Variables globales
extern CardTextures g_cardTextures;
extern bool g_useTextures;  // true = usar imagenes, false = procedural

// Fuentes personalizadas
extern Font g_fontTitle;     // Caldstone - para títulos
extern Font g_fontText;      // Kolbano - para texto general
extern bool g_fontsLoaded;   // Indica si las fuentes están cargadas

// Gestión de fuentes
void LoadGameFonts(void);
void UnloadGameFonts(void);
void LoadTableTexture(void);
void DrawTableBackground(void);

// Funciones de renderizado
void DrawCard(Card* card, float x, float y, bool faceUp, float scale);
void DrawCardBack(float x, float y, float scale);
void DrawCardFaceTexture(Card* card, float x, float y, float scale);
void DrawCardBackTexture(float x, float y, float scale);
void DrawCardFace(Card* card, float x, float y, float scale);

// Renderizado de estados del juego
void DrawStateMenu(Game* game);
void DrawStateInstructions(Game* game);
void DrawStateConfig(Game* game);
void DrawStateSetupPlayers(Game* game);
void DrawStateDealCards(Game* game);
void DrawStatePlayerTurn(Game* game);
void DrawStateHideScreen(Game* game);
void DrawStateShowResults(Game* game);
void DrawStateRoundEnd(Game* game);
void DrawStateShop(Game* game);
void DrawStateGameOver(Game* game);

// Utilidades de UI
void DrawButton(const char* text, float x, float y, float width, float height, Color bgColor, Color textColor);
bool IsButtonClicked(const char* text, float x, float y, float width, float height);
void DrawCenteredText(const char* text, float y, int fontSize, Color color);
void DrawScoreboard(Game* game, float x, float y);
void DrawHandResult(HandResult* result, float x, float y);

// Cálculo de posiciones
float GetHandStartX(int cardCount, float screenWidth);
float GetCardY(bool selected);

// High Scores
void DrawHighScoresScreen(HighScoreEntry* entries, int count);

#endif // RENDERER_H
