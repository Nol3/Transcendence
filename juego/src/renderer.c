#include "renderer.h"
#include "audio.h"
#include "poker_hand.h"
#include <string.h>
#include <stdio.h>

#if defined(PLATFORM_WEB)
#define ASSETS_PREFIX "/assets"
#define FONTS_PREFIX "/fonts"
#else
#define ASSETS_PREFIX "assets"
#define FONTS_PREFIX "fonts"
#endif

// Variables globales
CardTextures g_cardTextures = {0};
bool g_useTextures = true;  // Por defecto usar texturas si están disponibles

// Textura de tapete (fondo)
Texture2D g_tableTexture = {0};

// Fuentes personalizadas
Font g_fontTitle = {0};
Font g_fontText = {0};
bool g_fontsLoaded = false;

// Forward declarations
void DrawCardShadow(float x, float y, float scale);
bool IsMouseOverCard(float x, float y, float scale);

// ========== CARGAR TAPETE ==========

void LoadTableTexture(void) {
    g_tableTexture = LoadTexture(ASSETS_PREFIX "/tapete/tapete.png");
    if (g_tableTexture.id == 0) {
        TraceLog(LOG_WARNING, "No se pudo cargar tapete.png");
    } else {
        TraceLog(LOG_INFO, "Tapete cargado: %dx%d", g_tableTexture.width, g_tableTexture.height);
    }
}

void UnloadTableTexture(void) {
    if (g_tableTexture.id != 0) {
        UnloadTexture(g_tableTexture);
        g_tableTexture.id = 0;
    }
}

// ========== GESTIÓN DE FUENTES ==========

void LoadGameFonts(void) {
    // Cargar fuentes con tamaño base grande para mejor calidad
    // El tamaño base determina la resolución del atlas de texturas
    g_fontTitle = LoadFontEx(FONTS_PREFIX "/caldstone/Caldstone-SemiBold.otf", 128, NULL, 256);
    g_fontText = LoadFontEx(FONTS_PREFIX "/kolbano/Kolbano-regular.otf", 64, NULL, 256);
    
    // Verificar carga exitosa
    g_fontsLoaded = (g_fontTitle.texture.id > 0 && g_fontTitle.baseSize > 0 && 
                     g_fontText.texture.id > 0 && g_fontText.baseSize > 0);
    
    // Si falla la carga, usamos la fuente por defecto
    if (!g_fontsLoaded) {
        TraceLog(LOG_WARNING, "No se pudieron cargar las fuentes personalizadas, usando fuente por defecto");
    } else {
        TraceLog(LOG_INFO, "Fuentes cargadas - Title: %dpx, Text: %dpx", 
                 g_fontTitle.baseSize, g_fontText.baseSize);
    }
}

void UnloadGameFonts(void) {
    if (g_fontsLoaded) {
        UnloadFont(g_fontTitle);
        UnloadFont(g_fontText);
        g_fontsLoaded = false;
    }
    UnloadTableTexture();
}

void DrawTableBackground(void) {
    if (g_tableTexture.id != 0) {
        DrawTextureEx(g_tableTexture, (Vector2){0, 0}, 0.0f, 1.0f, WHITE);
    } else {
        DrawRectangle(0, 0, GetScreenWidth(), GetScreenHeight(), (Color){0, 74, 28, 255});
    }
}


// ========== DIBUJADO DE CARTAS ==========

void DrawCardBackTexture(float x, float y, float scale) {
    if (!g_cardTextures.loaded || g_cardTextures.cardBack.id == 0) {
        DrawCardBack(x, y, scale);
        return;
    }
    
    Texture2D tex = g_cardTextures.cardBack;
    float w = CARD_WIDTH * scale;
    float h = CARD_HEIGHT * scale;
    
    // Sombra
    DrawCardShadow(x, y, scale);
    
    // Dibujar textura escalada
    DrawTexturePro(tex, 
                   (Rectangle){0, 0, (float)tex.width, (float)tex.height},
                   (Rectangle){x, y, w, h},
                   (Vector2){0, 0}, 0, WHITE);
    
    // Borde dorado si está seleccionada (aunque el reverso no se selecciona normalmente)
    DrawRectangleRoundedLines((Rectangle){x, y, w, h}, 0.1f, 8, (Color){0, 0, 0, 100});
}

void DrawCardBack(float x, float y, float scale) {
    if (g_useTextures && g_cardTextures.loaded && g_cardTextures.cardBack.id != 0) {
        DrawCardBackTexture(x, y, scale);
        return;
    }
    
    // Renderizado procedural (fallback)
    float w = CARD_WIDTH * scale;
    float h = CARD_HEIGHT * scale;
    
    // Sombra
    DrawCardShadow(x, y, scale);
    
    // Fondo blanco
    DrawRectangleRounded((Rectangle){x, y, w, h}, 0.1f, 8, WHITE);
    
    // Borde
    DrawRectangleRoundedLines((Rectangle){x, y, w, h}, 0.1f, 8, BLACK);
    
    // Patrón de reverso
    Color backColor = (Color){0, 80, 0, 255};
    DrawRectangleRounded((Rectangle){x + 5*scale, y + 5*scale, w - 10*scale, h - 10*scale}, 0.05f, 8, backColor);
    
    // Patrón decorativo simple
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 4; j++) {
            float cx = x + 15*scale + i * 25*scale;
            float cy = y + 20*scale + j * 25*scale;
            DrawCircle(cx, cy, 5*scale, (Color){0, 80, 30, 255});
        }
    }
}

// Verifica si el ratón está sobre una carta
bool IsMouseOverCard(float x, float y, float scale) {
    Vector2 mousePos = GetMousePosition();
    float w = CARD_WIDTH * scale;
    float h = CARD_HEIGHT * scale;
    return CheckCollisionPointRec(mousePos, (Rectangle){x, y, w, h});
}

void DrawCardShadow(float x, float y, float scale) {
    float w = CARD_WIDTH * scale;
    float h = CARD_HEIGHT * scale;
    float shadowOffset = 4 * scale;
    DrawRectangleRounded((Rectangle){x + shadowOffset, y + shadowOffset, w, h}, 0.1f, 8, (Color){0, 0, 0, 60});
}

void DrawCardFaceTexture(Card* card, float x, float y, float scale) {
    if (!g_cardTextures.loaded) {
        DrawCardFace(card, x, y, scale);
        return;
    }
    
    Texture2D tex = GetCardTexture(&g_cardTextures, card->suit, card->rank);
    if (tex.id == 0) {
        DrawCardFace(card, x, y, scale);
        return;
    }
    
    float w = CARD_WIDTH * scale;
    float h = CARD_HEIGHT * scale;
    bool isHovered = IsMouseOverCard(x, y, scale);
    
    // Sombra
    DrawCardShadow(x, y, scale);
    
    // Fondo blanco para la carta (por si la textura tiene transparencia)
    DrawRectangleRounded((Rectangle){x, y, w, h}, 0.1f, 8, WHITE);
    
    // Dibujar textura
    DrawTexturePro(tex,
                   (Rectangle){0, 0, (float)tex.width, (float)tex.height},
                   (Rectangle){x, y, w, h},
                   (Vector2){0, 0}, 0, WHITE);
    
    // Efecto hover (brillo suave)
    if (isHovered && !card->selected) {
        DrawRectangleRounded((Rectangle){x, y, w, h}, 0.1f, 8, (Color){255, 255, 255, 40});
    }
    
    // Efecto de selección (overlay dorado)
    if (card->selected) {
        DrawRectangleRounded((Rectangle){x, y, w, h}, 0.1f, 8, (Color){255, 215, 0, 80});
        DrawRectangleRoundedLines((Rectangle){x, y, w, h}, 0.1f, 8, GOLD);
    }
}

void DrawCardFace(Card* card, float x, float y, float scale) {
    // Si hay texturas disponibles, usarlas
    if (g_useTextures && g_cardTextures.loaded) {
        Texture2D tex = GetCardTexture(&g_cardTextures, card->suit, card->rank);
        if (tex.id != 0) {
            DrawCardFaceTexture(card, x, y, scale);
            return;
        }
    }
    
    // Renderizado procedural (fallback)
    float w = CARD_WIDTH * scale;
    float h = CARD_HEIGHT * scale;
    Color suitColor = GetSuitColor(card->suit);
    bool isHovered = IsMouseOverCard(x, y, scale);
    
    // Sombra
    DrawCardShadow(x, y, scale);
    
    // Fondo
    Color bgColor = card->selected ? (Color){255, 255, 200, 255} : WHITE;
    if (isHovered && !card->selected) {
        bgColor = (Color){255, 255, 240, 255}; // Ligeramente más brillante en hover
    }
    DrawRectangleRounded((Rectangle){x, y, w, h}, 0.1f, 8, bgColor);
    
    // Borde
    Color borderColor = card->selected ? GOLD : (isHovered ? (Color){100, 100, 100, 255} : BLACK);
    DrawRectangleRoundedLines((Rectangle){x, y, w, h}, 0.1f, 8, borderColor);
    
    // Símbolo del palo arriba a la izquierda
    const char* rankStr = GetRankSymbol(card->rank);
    const char* suitStr = GetSuitSymbol(card->suit);
    
    int fontSize = (int)(16 * scale);
    DrawText(rankStr, (int)(x + 8*scale), (int)(y + 8*scale), fontSize, suitColor);
    DrawText(suitStr, (int)(x + 8*scale), (int)(y + 25*scale), fontSize + 2, suitColor);
    
    // Símbolo del palo abajo a la derecha (invertido)
    int rankWidth = MeasureText(rankStr, fontSize);
    int suitWidth = MeasureText(suitStr, fontSize + 2);
    DrawText(rankStr, (int)(x + w - 8*scale - rankWidth), (int)(y + h - 40*scale), fontSize, suitColor);
    DrawText(suitStr, (int)(x + w - 8*scale - suitWidth), (int)(y + h - 25*scale), fontSize + 2, suitColor);
    
    // Símbolo grande en el centro
    int centerFontSize = (int)(28 * scale);
    int centerWidth = MeasureText(suitStr, centerFontSize);
    DrawText(suitStr, (int)(x + w/2 - centerWidth/2), (int)(y + h/2 - centerFontSize/2), centerFontSize, suitColor);
}

void DrawCard(Card* card, float x, float y, bool faceUp, float scale) {
    if (faceUp) {
        DrawCardFace(card, x, y, scale);
    } else {
        DrawCardBack(x, y, scale);
    }
}

// ========== DIBUJADO DE ESTADOS ==========

void DrawStateMenu(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    
    DrawCenteredText("POKER RACE", 80, 60, GOLD);
    DrawCenteredText("Juego de Cartas Multiplayer", 150, 30, WHITE);
    
    // Botón JUGAR
    float btnX = screenW / 2 - 100;
    float btnY = 300;
    DrawButton("JUGAR", btnX, btnY, 200, 60, (Color){0, 100, 40, 255}, WHITE);
    
    // Botón INSTRUCCIONES
    DrawButton("INSTRUCCIONES", btnX, btnY + 80, 200, 50, (Color){0, 80, 120, 255}, WHITE);
    
    // Botón CONFIGURACIÓN
    DrawButton("CONFIGURACION", btnX, btnY + 140, 200, 50, (Color){80, 80, 80, 255}, WHITE);
    
    DrawCenteredText("Presiona ENTER para comenzar", screenH - 100, 20, LIGHTGRAY);
    
    // Instrucciones
    DrawCenteredText("Forma la mejor mano de 5 cartas con 8 cartas repartidas", screenH - 50, 16, LIGHTGRAY);
}

void DrawStateInstructions(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    
    DrawCenteredText("COMO JUGAR", 40, 40, GOLD);
    
    // Panel de instrucciones
    int panelY = 100;
    int lineHeight = 35;
    int startX = screenW / 2 - 350;
    
    // Sección: Objetivo
    DrawText("obj:", startX, panelY, 24, WHITE);
    panelY += lineHeight;
    DrawText("Forma la mejor mano de poker con las cartas que tienes.", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight + 10;
    
    // Sección: Como jugar
    DrawText("COMO JUGAR:", startX, panelY, 24, WHITE);
    panelY += lineHeight;
    DrawText("1. Recibes 8 cartas", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight;
    DrawText("2. Selecciona 1-5 cartas para formar tu mano", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight;
    DrawText("3. Puedes DESCARTAR hasta 5 cartas UNA vez", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight;
    DrawText("4. Presiona CONFIRMAR para jugar tu mano", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight + 10;
    
    // Sección: Manos y puntuación
    DrawText("MANOS Y PUNTOS:", startX, panelY, 24, WHITE);
    panelY += lineHeight;
    DrawText("Pareja: 10 pts    Doble Pareja: 20 pts    Trio: 30 pts", startX + 20, panelY, 18, LIGHTGRAY);
    panelY += lineHeight;
    DrawText("Escalera: 40 pts  Color: 50 pts           Full House: 60 pts", startX + 20, panelY, 18, LIGHTGRAY);
    panelY += lineHeight + 10;
    
    // Sección: Controles
    DrawText("CONTROLES:", startX, panelY, 24, WHITE);
    panelY += lineHeight;
    DrawText("Raton: Click en cartas para seleccionar", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight;
    DrawText("Botones: Usa los botones verdes para continuar", startX + 20, panelY, 20, LIGHTGRAY);
    panelY += lineHeight;
    DrawText("Enter: Tambien puedes presionar ENTER", startX + 20, panelY, 20, LIGHTGRAY);
    
    // Botón VOLVER
    DrawButton("VOLVER", screenW/2 - 100, screenH - 80, 200, 50, (Color){0, 100, 40, 255}, WHITE);
}

void DrawStateConfig(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int centerX = screenW / 2;
    
    DrawCenteredText("CONFIGURACION DE AUDIO", 50, 42, GOLD);
    
    // Obtener volúmenes actuales
    int masterVol = 100, musicVol = 50, sfxVol = 80;
    AudioGetVolumes(&masterVol, &musicVol, &sfxVol);
    
    int baseY = 160;
    int gapY = 100;
    
    // Master Volume
    DrawText("Master:", centerX - 180, baseY, 28, BLACK);
    DrawButton("-", centerX - 60, baseY - 5, 40, 40, (Color){220, 220, 220, 255}, BLACK);
    DrawRectangle(centerX, baseY, 200, 30, (Color){30, 30, 30, 255});
    DrawRectangle(centerX, baseY, (int)(masterVol * 2.0f), 30, GOLD);
    DrawButton("+", centerX + 210, baseY - 5, 40, 40, (Color){220, 220, 220, 255}, BLACK);
    char buf[16];
    snprintf(buf, sizeof(buf), "%d%%", masterVol);
    DrawText(buf, centerX + 260, baseY + 5, 20, BLACK);
    
    // Music Volume
    DrawText("Musica:", centerX - 180, baseY + gapY, 28, BLACK);
    DrawButton("-", centerX - 60, baseY + gapY - 5, 40, 40, (Color){220, 220, 220, 255}, BLACK);
    DrawRectangle(centerX, baseY + gapY, 200, 30, (Color){30, 30, 30, 255});
    DrawRectangle(centerX, baseY + gapY, (int)(musicVol * 2.0f), 30, GOLD);
    DrawButton("+", centerX + 210, baseY + gapY - 5, 40, 40, (Color){220, 220, 220, 255}, BLACK);
    snprintf(buf, sizeof(buf), "%d%%", musicVol);
    DrawText(buf, centerX + 260, baseY + gapY + 5, 20, BLACK);
    
    // SFX Volume
    DrawText("SFX:", centerX - 180, baseY + gapY * 2, 28, BLACK);
    DrawButton("-", centerX - 60, baseY + gapY * 2 - 5, 40, 40, (Color){220, 220, 220, 255}, BLACK);
    DrawRectangle(centerX, baseY + gapY * 2, 200, 30, (Color){30, 30, 30, 255});
    DrawRectangle(centerX, baseY + gapY * 2, (int)(sfxVol * 2.0f), 30, GOLD);
    DrawButton("+", centerX + 210, baseY + gapY * 2 - 5, 40, 40, (Color){220, 220, 220, 255}, BLACK);
    snprintf(buf, sizeof(buf), "%d%%", sfxVol);
    DrawText(buf, centerX + 260, baseY + gapY * 2 + 5, 20, BLACK);
    
    DrawCenteredText("Usa las flechas o botones + y - para ajustar", screenH - 120, 20, BLACK);
    
    // Botón VOLVER
    DrawButton("VOLVER", centerX - 100, screenH - 80, 200, 50, GOLD, BLACK);
}

void DrawStateSetupPlayers(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int startY = 140;
    int spacing = 100;
    
    // Título
    DrawCenteredText("CONFIGURACION", 50, 42, WHITE);
    
    char buffer[64];
    int btnW = 50, btnH = 45;
    int labelW = 220;
    int centerX = screenW / 2;
    
    // Jugadores
    snprintf(buffer, sizeof(buffer), "Jugadores: %d", game->playerCount);
    DrawCenteredText(buffer, startY, 32, GOLD);
    DrawButton("-", centerX - labelW/2 - btnW - 10, startY - 8, btnW, btnH, (Color){60, 60, 60, 255}, WHITE);
    DrawButton("+", centerX + labelW/2 + 10, startY - 8, btnW, btnH, (Color){60, 60, 60, 255}, WHITE);
    
    // Rondas
    snprintf(buffer, sizeof(buffer), "Rondas: %d", game->maxRounds);
    DrawCenteredText(buffer, startY + spacing, 32, GOLD);
    DrawButton("-", centerX - labelW/2 - btnW - 10, startY + spacing - 8, btnW, btnH, (Color){60, 60, 60, 255}, WHITE);
    DrawButton("+", centerX + labelW/2 + 10, startY + spacing - 8, btnW, btnH, (Color){60, 60, 60, 255}, WHITE);
    
    // Puntuación objetivo
    snprintf(buffer, sizeof(buffer), "obj: %d pts", game->targetScore);
    DrawCenteredText(buffer, startY + spacing*2, 32, GOLD);
    DrawButton("-", centerX - labelW/2 - btnW - 10, startY + spacing*2 - 8, btnW, btnH, (Color){60, 60, 60, 255}, WHITE);
    DrawButton("+", centerX + labelW/2 + 10, startY + spacing*2 - 8, btnW, btnH, (Color){60, 60, 60, 255}, WHITE);
    
    // Instrucciones
    DrawCenteredText("Usa TAB para cambiar opcion, FLECHAS para ajustar", screenH - 140, 18, LIGHTGRAY);

    // Botón ATRAS (esquina superior izquierda)
    DrawButton("ATRAS", 20, 20, 120, 40, (Color){60, 60, 60, 220}, WHITE);

    // Botón CONTINUAR
    DrawButton("CONTINUAR", screenW/2 - 100, screenH - 90, 200, 55, (Color){0, 100, 40, 255}, WHITE);
}

void DrawStateDealCards(Game* game) {
    DrawCenteredText("Repartiendo cartas...", GetScreenHeight() / 2, 30, WHITE);
    
    char buffer[64];
    snprintf(buffer, sizeof(buffer), "Ronda %d de %d", game->currentRound, game->maxRounds);
    DrawCenteredText(buffer, 50, 25, GOLD);
}

void DrawStatePlayerTurn(Game* game) {
    Player* current = &game->players[game->currentPlayer];
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int marginTop = 45;      // Margen superior
    int marginBottom = 130;  // Margen inferior para botones
    int btnRowY = screenH - marginBottom;  // Fila de botones principales
    int sortBtnY = btnRowY + 15;  // Botones de ordenamiento (más pequeños, ligeramente desplazados)
    
    char buffer[256];
    
    // ========== HEADER ==========
    snprintf(buffer, sizeof(buffer), "Turno de: %s", current->name);
    if (g_fontsLoaded) {
        float textW = MeasureTextEx(g_fontTitle, buffer, 38, 1).x;
        DrawTextEx(g_fontTitle, buffer, (Vector2){(screenW - textW)/2, marginTop}, 38, 1, GOLD);
    } else {
        DrawCenteredText(buffer, marginTop, 38, GOLD);
    }
    
    // ========== MENSAJE DE JUGADA ==========
    if (current->selectedCount >= 1) {
        HandResult result = EvaluateHand(current->selectedCards, current->selectedCount);
        const char* handName = GetHandTypeName(result.type);
        int points = result.score;
        
        Color msgColor = (points > 0) ? (Color){100, 255, 100, 255} : LIGHTGRAY;
        
        if (points > 0) {
            snprintf(buffer, sizeof(buffer), "%s: %d pts", handName, points);
        } else {
            snprintf(buffer, sizeof(buffer), "%s (sin puntos)", handName);
        }
        
        if (g_fontsLoaded) {
            float textW = MeasureTextEx(g_fontText, buffer, 26, 1).x;
            DrawTextEx(g_fontText, buffer, (Vector2){(screenW - textW)/2, marginTop + 50}, 26, 1, msgColor);
        } else {
            DrawCenteredText(buffer, marginTop + 50, 26, msgColor);
        }
    }
    
    // ========== SCOREBOARD (esquina superior izquierda) ==========
    DrawScoreboard(game, 20, marginTop);
    
    // ========== CONTADOR (esquina superior derecha) ==========
    snprintf(buffer, sizeof(buffer), "Seleccionadas: %d/5", current->selectedCount);
    if (g_fontsLoaded) {
        float textW = MeasureTextEx(g_fontText, buffer, 20, 1).x;
        DrawTextEx(g_fontText, buffer, (Vector2){screenW - textW - 20, marginTop + 10}, 20, 1, WHITE);
    } else {
        int textW = MeasureText(buffer, 20);
        DrawText(buffer, screenW - textW - 20, marginTop + 10, 20, WHITE);
    }
    
    // ========== BOTONES PRINCIPALES (fila inferior) ==========
    // CONFIRMAR (centro)
    if (current->selectedCount >= 1) {
        DrawButton("CONFIRMAR", screenW/2 - 100, btnRowY, 200, 48, (Color){0, 150, 60, 255}, WHITE);
    }
    
    // DESCARTAR (derecha)
    if (!current->hasDiscarded && current->selectedCount >= 1 && current->selectedCount <= 5) {
        DrawButton("DESCARTAR", screenW - 155, btnRowY, 135, 48, (Color){180, 40, 40, 255}, WHITE);
    }
    
    // ========== BOTONES DE ORDENAMIENTO (izquierda, más pequeños) ==========
    DrawButton("VALOR", 20, sortBtnY + 5, 75, 38, (Color){60, 80, 120, 255}, WHITE);
    DrawButton("PALO", 105, sortBtnY + 5, 75, 38, (Color){80, 60, 120, 255}, WHITE);
    
    // ========== INSTRUCCIONES (debajo de todo) ==========
    int infoY = screenH - 45;
    if (g_fontsLoaded) {
        DrawTextEx(g_fontText, "Selecciona 1-5 cartas para formar tu mano", 
                   (Vector2){20, infoY}, 16, 1, LIGHTGRAY);
        if (!current->hasDiscarded) {
            DrawTextEx(g_fontText, "Puedes descartar hasta 5 cartas", 
                       (Vector2){20, infoY + 20}, 14, 1, (Color){200, 200, 150, 255});
        }
    } else {
        DrawText("Selecciona 1-5 cartas para formar tu mano", 20, infoY, 16, LIGHTGRAY);
        if (!current->hasDiscarded) {
            DrawText("Puedes descartar hasta 5 cartas", 20, infoY + 20, 14, (Color){200, 200, 150, 255});
        }
    }
    
    // ========== ÁREA DE CARTAS ==========
    float cardAreaTop = marginTop + 100;
    float cardAreaBottom = btnRowY - 15;
    float cardY = cardAreaTop + (cardAreaBottom - cardAreaTop) / 2;
    float startX = GetHandStartX(current->handCount, screenW);
    
    // Dibujar mano del jugador
    for (int i = 0; i < current->handCount; i++) {
        float cardX = startX + i * (CARD_WIDTH * 1.2f + CARD_SPACING);
        float offsetY = current->hand[i].selected ? -25 : 0;
        float scale = 1.2f * current->hand[i].hoverScale;
        
        // Calcular offset para centrar la carta escalada
        float scaledW = CARD_WIDTH * scale;
        float scaledH = CARD_HEIGHT * scale;
        float offsetX = (CARD_WIDTH * 1.2f - scaledW) / 2;
        float offsetY2 = (CARD_HEIGHT * 1.2f - scaledH) / 2;
        
        DrawCard(&current->hand[i], cardX + offsetX, cardY + offsetY + offsetY2, true, scale);
    }
    
    // Dibujar cartas seleccionadas arriba
    if (current->selectedCount > 0) {
        float selStartX = GetHandStartX(current->selectedCount, screenW);
        float selY = cardAreaTop - 25;
        
        for (int i = 0; i < current->selectedCount; i++) {
            float cardX = selStartX + i * (CARD_WIDTH + CARD_SPACING);
            DrawCard(&current->selectedCards[i], cardX, selY, true, 1.0f);
        }
    }
}

void DrawStateHideScreen(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    
    // Fondo oscuro
    DrawRectangle(0, 0, screenW, screenH, (Color){0, 0, 0, 200});
    
    Player* next = &game->players[game->currentPlayer];
    
    char buffer[128];
    snprintf(buffer, sizeof(buffer), "Pasa el dispositivo a %s", next->name);
    DrawCenteredText(buffer, screenH / 2 - 50, 35, GOLD);
    
    // Botón ESTOY LISTO
    DrawButton("ESTOY LISTO", screenW/2 - 100, screenH/2 + 80, 200, 50, (Color){0, 120, 50, 255}, WHITE);
    
    // Indicador visual
    DrawRectangle(screenW/2 - 150, screenH/2 + 150, 300, 4, GOLD);
}

void DrawStateShowResults(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    
    DrawCenteredText("RESULTADOS DE LA RONDA", 30, 35, GOLD);
    
    // Botón SIGUIENTE
    DrawButton("SIGUIENTE", screenW/2 - 100, screenH - 80, 200, 50, (Color){0, 100, 40, 255}, WHITE);
    
    char buffer[128];
    snprintf(buffer, sizeof(buffer), "Ronda %d", game->currentRound);
    DrawCenteredText(buffer, 70, 25, WHITE);
    
    // Dibujar cada jugador y su mano
    float yOffset = 120;
    float playerHeight = 120;
    
    for (int p = 0; p < game->playerCount; p++) {
        Player* player = &game->players[p];
        
        // Nombre y puntuación
        snprintf(buffer, sizeof(buffer), "%s - Puntos: +%d (Total: %d)", 
                 player->name, player->lastResult.score, player->score);
        DrawText(buffer, 50, (int)yOffset, 22, WHITE);
        
        // Mano del jugador
        float handX = 50;
        float handY = yOffset + 30;
        for (int i = 0; i < player->selectedCount; i++) {
            DrawCard(&player->selectedCards[i], handX + i * (CARD_WIDTH + 10), handY, true, 0.8f);
        }
        
        // Tipo de mano
        DrawHandResult(&player->lastResult, 50 + player->selectedCount * (CARD_WIDTH * 0.8f + 10) + 20, handY + 20);
        
        yOffset += playerHeight;
    }
    
    DrawCenteredText("Presiona ENTER para continuar", screenH - 40, 20, LIGHTGRAY);
}

void DrawStateRoundEnd(Game* game) {
    DrawCenteredText("Calculando ganador...", GetScreenHeight() / 2, 30, WHITE);
}

void DrawStateShop(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int centerX = screenW / 2;

    DrawCenteredText("TIENDA DE COMODINES", 40, 40, GOLD);

    char moneyBuf[32];
    snprintf(moneyBuf, sizeof(moneyBuf), "Dinero: %d", game->jokerSystem.money);
    int cardW = 160;
    int cardH = 180;
    int totalW = SHOP_JOKER_COUNT * cardW + (SHOP_JOKER_COUNT - 1) * 20;
    int startX = centerX - totalW / 2;

    for (int i = 0; i < SHOP_JOKER_COUNT; i++) {
        Joker* joker = &game->jokerSystem.shopJokers[i];
        int x = startX + i * (cardW + 20);
        int y = screenH / 2 - cardH / 2;

        Color bgColor = (Color){30, 30, 50, 255};
        if (joker->purchased) {
            bgColor = (Color){0, 60, 0, 255};
        } else if (game->jokerSystem.money < joker->price) {
            bgColor = (Color){60, 20, 20, 255};
        }

        DrawRectangleRounded((Rectangle){(float)x, (float)y, cardW, cardH}, 0.15f, 10, bgColor);
        DrawRectangleRoundedLines((Rectangle){(float)x, (float)y, cardW, cardH}, 0.15f, 10, GOLD);

        Color nameColor = joker->purchased ? GREEN : WHITE;
        int nameW = MeasureText(joker->name, 22);
        DrawText(joker->name, x + cardW / 2 - nameW / 2, y + 15, 22, nameColor);

        char priceBuf[16];
        snprintf(priceBuf, sizeof(priceBuf), "$%d", joker->price);
        Color priceColor = joker->purchased ? GREEN : (game->jokerSystem.money >= joker->price ? GOLD : (Color){200, 50, 50, 255});
        int priceW = MeasureText(priceBuf, 20);
        DrawText(priceBuf, x + cardW / 2 - priceW / 2, y + 45, 20, priceColor);

        DrawText(joker->description, x + 10, y + 80, 16, LIGHTGRAY);

        if (!joker->purchased && game->jokerSystem.money >= joker->price) {
            DrawButton("COMPRAR", x, y + cardH - 50, cardW, 42, (Color){0, 150, 60, 255}, WHITE);
        }
    }

    if (game->jokerSystem.money >= 1) {
        DrawButton("REROLL", centerX + 250, screenH / 2 - 80, 100, 50, (Color){80, 60, 120, 255}, WHITE);
    }

    if (game->jokerSystem.ownedCount > 0) {
        DrawCenteredText("Tus Comodines:", screenH / 2 + 120, 20, GOLD);
        for (int i = 0; i < game->jokerSystem.ownedCount; i++) {
            char buf[64];
            snprintf(buf, sizeof(buf), "%s", game->jokerSystem.ownedJokers[i].name);
            DrawText(buf, 50 + i * 150, screenH / 2 + 150, 16, GREEN);
        }
    }

        DrawButton("CONTINUAR", centerX - 100, screenH - 100, 200, 55, (Color){0, 100, 40, 255}, WHITE);
}

void DrawStateGameOver(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int marginTop = 60;
    int marginBottom = 120;
    
    DrawRectangle(0, 0, screenW, screenH, (Color){0, 0, 0, 230});
    
    // Título FIN DEL JUEGO
    DrawCenteredText("FIN DEL JUEGO", marginTop, 48, GOLD);
    
    // Encontrar ganador
    int winner = -1;
    int maxScore = -1;
    for (int i = 0; i < game->playerCount; i++) {
        if (game->players[i].score > maxScore) {
            maxScore = game->players[i].score;
            winner = i;
        }
    }
    
    if (winner >= 0) {
        char buffer[128];
        snprintf(buffer, sizeof(buffer), "Ganador: %s con %d puntos!", 
                 game->players[winner].name, maxScore);
        DrawCenteredText(buffer, marginTop + 70, 32, GREEN);
    }
    
    // Tabla final
    float y = marginTop + 120;
    for (int i = 0; i < game->playerCount; i++) {
        char buffer[64];
        Color color = (i == winner) ? GOLD : WHITE;
        snprintf(buffer, sizeof(buffer), "%s: %d puntos (%d rondas ganadas)", 
                 game->players[i].name, game->players[i].score, 
                 game->players[i].totalRoundsWon);
        DrawCenteredText(buffer, y, 24, color);
        y += 32;
    }
    
    // Instrucción
    DrawCenteredText("Presiona ENTER o R para reiniciar", screenH - marginBottom + 20, 20, LIGHTGRAY);
    
    // Botón COMPARTIR
    float shareY = screenH - marginBottom - 100;
    DrawButton("COMPARTIR", screenW/2 - 120/2 - 70, shareY, 140, 45, (Color){100, 100, 100, 255}, WHITE);
    
    // Botón JUGAR DE NUEVO (al fondo, separado del texto)
    DrawButton("JUGAR DE NUEVO", screenW/2 - 120, screenH - marginBottom - 30, 240, 55, (Color){0, 120, 50, 255}, WHITE);
}

// ========== UTILIDADES DE UI ==========

void DrawButton(const char* text, float x, float y, float width, float height, 
                Color bgColor, Color textColor) {
    // Sombra
    DrawRectangle(x + 3, y + 3, width, height, (Color){0, 0, 0, 100});
    
    // Botón
    Color buttonColor = CheckCollisionPointRec(GetMousePosition(), (Rectangle){x, y, width, height}) 
                        ? (Color){bgColor.r + 40, bgColor.g + 40, bgColor.b + 40, 255} 
                        : bgColor;
    DrawRectangleRounded((Rectangle){x, y, width, height}, 0.2f, 8, buttonColor);
    DrawRectangleRoundedLines((Rectangle){x, y, width, height}, 0.2f, 8, WHITE);
    
    // Texto
    int fontSize = (int)(height * 0.4f);
    int textWidth = MeasureText(text, fontSize);
    DrawText(text, (int)(x + width/2 - textWidth/2), (int)(y + height/2 - fontSize/2), 
             fontSize, textColor);
}

bool IsButtonClicked(const char* text, float x, float y, float width, float height) {
    Rectangle rect = {x, y, width, height};
    Vector2 pos = GetMousePosition();
    
    #if defined(PLATFORM_WEB)
    // Soporte para touch: verificar si hay touch activo
    int touchCount = GetTouchPointCount();
    if (touchCount > 0) {
        pos = GetTouchPosition(0);
    }
    #endif
    
    if (CheckCollisionPointRec(pos, rect)) {
        if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
            return true;
        }
    }
    return false;
}

void DrawCenteredText(const char* text, float y, int fontSize, Color color) {
    int textWidth = MeasureText(text, fontSize);
    DrawText(text, GetScreenWidth()/2 - textWidth/2, (int)y, fontSize, color);
}

void DrawScoreboard(Game* game, float x, float y) {
    float width = 180;
    float height = 30 + game->playerCount * 35;
    
    // Fondo
    DrawRectangleRounded((Rectangle){x, y, width, height}, 0.1f, 8, (Color){0, 0, 0, 180});
    DrawRectangleRoundedLines((Rectangle){x, y, width, height}, 0.1f, 8, GOLD);
    
    // Título
    DrawText("PUNTUACION", (int)(x + 10), (int)(y + 8), 18, GOLD);
    
    // Jugadores
    for (int i = 0; i < game->playerCount; i++) {
        Player* p = &game->players[i];
        char buffer[64];
        Color nameColor = (i == game->currentPlayer) ? GREEN : WHITE;
        snprintf(buffer, sizeof(buffer), "%s: %d", p->name, p->score);
        DrawText(buffer, (int)(x + 10), (int)(y + 35 + i * 30), 16, nameColor);
    }
}

void DrawHandResult(HandResult* result, float x, float y) {
    DrawText(result->name, (int)x, (int)y, 20, GOLD);
    
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "+%d pts", result->score);
    DrawText(buffer, (int)x, (int)(y + 25), 18, GREEN);
}

float GetHandStartX(int cardCount, float screenWidth) {
    float cardSpacing = CARD_WIDTH * 1.2f + CARD_SPACING;
    float totalWidth = cardCount * cardSpacing - CARD_SPACING;
    return (screenWidth - totalWidth) / 2;
}

// ========== HIGH SCORES SCREEN ==========

void DrawHighScoresScreen(HighScoreEntry* entries, int count) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    
    // Fondo oscuro semitransparente
    DrawRectangle(0, 0, screenW, screenH, (Color){0, 0, 0, 200});
    
    // Título
    DrawCenteredText("MEJORES PUNTUACIONES", 40, 40, GOLD);
    
    // Encabezados
    int startY = 100;
    int lineHeight = 35;
    int nameX = screenW/2 - 200;
    int scoreX = screenW/2 + 50;
    int dateX = screenW/2 + 150;
    
    DrawText("Jugador", nameX, startY, 20, LIGHTGRAY);
    DrawText("Puntos", scoreX, startY, 20, LIGHTGRAY);
    DrawText("Fecha", dateX, startY, 20, LIGHTGRAY);
    
    // Línea separadora
    DrawRectangle(screenW/2 - 250, startY + 30, 500, 2, GOLD);
    
    // Mostrar entradas
    for (int i = 0; i < count; i++) {
        int y = startY + 50 + i * lineHeight;
        Color color = (i == 0) ? GOLD : (i == 1) ? (Color){192, 192, 192, 255} : (i == 2) ? (Color){205, 127, 50, 255} : WHITE;
        
        char rankStr[4];
        snprintf(rankStr, sizeof(rankStr), "%d.", i + 1);
        DrawText(rankStr, nameX - 40, y, 20, color);
        
        DrawText(entries[i].name, nameX, y, 20, color);
        
        char scoreStr[16];
        snprintf(scoreStr, sizeof(scoreStr), "%d", entries[i].score);
        DrawText(scoreStr, scoreX, y, 20, color);
        
        DrawText(entries[i].date, dateX, y, 18, (Color){200, 200, 200, 255});
    }
    
    if (count == 0) {
        DrawCenteredText("No hay puntuaciones registradas", startY + 100, 24, LIGHTGRAY);
    }
    
    // Botón VOLVER
    DrawButton("VOLVER", screenW/2 - 75, screenH - 100, 150, 45, (Color){0, 100, 40, 255}, WHITE);
}

