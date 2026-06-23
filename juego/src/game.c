#include "game.h"
#include "renderer.h"
#include "audio.h"
#include "cJSON.h"
#include "lang.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#if defined(PLATFORM_WEB)
    #include <emscripten/emscripten.h>
#else
    #define EMSCRIPTEN_KEEPALIVE
#endif

// Funciones de notificación vacías para desktop
#ifndef NOTIFY
#define NOTIFY(t) ((void)0)
#define NOTIFY_INT(t, v) ((void)0)
#endif

// Escapa comillas/backslashes para incrustar texto de forma segura en una
// cadena literal de JavaScript (evita romper el script o inyección).
static void JsEscape(const char* in, char* out, size_t out_size) {
    size_t j = 0;
    for (size_t i = 0; in && in[i] != '\0' && j + 2 < out_size; i++) {
        char c = in[i];
        if (c == '\r' || c == '\n') continue;
        if (c == '\\' || c == '\'' || c == '"') out[j++] = '\\';
        out[j++] = c;
    }
    out[j] = '\0';
}

// Notifica al parent window (Angular) el resultado final de la partida.
// score se envía como "<mi_puntuacion>-<puntuacion_rival>". En desktop es no-op.
static void EmitGameFinished(const char* winner, int player_score, int opponent_score) {
#if defined(PLATFORM_WEB)
    char safe_winner[64];
    JsEscape(winner, safe_winner, sizeof(safe_winner));
    char script[256];
    snprintf(script, sizeof(script),
        "window.parent.postMessage({type:'game-finished',winner:'%s',score:'%d-%d'},'*');",
        safe_winner, player_score, opponent_score);
    emscripten_run_script(script);
#else
    (void)winner; (void)player_score; (void)opponent_score;
#endif
}

static char g_player_name[128] = "Jugador 1";

EMSCRIPTEN_KEEPALIVE
void set_language(const char* lang_code) {
    LangSet(lang_code);
}

extern Game game;

EMSCRIPTEN_KEEPALIVE
void set_player_name_from_json(const char* json_string) {
    if (!json_string) return;
    cJSON* root = cJSON_Parse(json_string);
    if (!root) return;

    cJSON* username = cJSON_GetObjectItemCaseSensitive(root, "username");
    if (!cJSON_IsString(username) || !username->valuestring) {
        cJSON* data = cJSON_GetObjectItemCaseSensitive(root, "data");
        if (cJSON_IsObject(data)) {
            cJSON* user = cJSON_GetObjectItemCaseSensitive(data, "user");
            if (cJSON_IsObject(user)) {
                username = cJSON_GetObjectItemCaseSensitive(user, "username");
            }
        }
    }

    if (cJSON_IsString(username) && username->valuestring) {
        strncpy(g_player_name, username->valuestring, sizeof(g_player_name) - 1);
        g_player_name[sizeof(g_player_name) - 1] = '\0';

        strncpy(game.players[0].name, g_player_name, sizeof(game.players[0].name) - 1);
        game.players[0].name[sizeof(game.players[0].name) - 1] = '\0';
    }

    cJSON_Delete(root);
}

// Configuración del juego desde Angular (módulo Game Customization).
// JSON: { "players": 2-4, "targetScore": 100-1000, "rounds": 1-10,
//         "theme": "classic|neon|crimson|violet|gold" }
EMSCRIPTEN_KEEPALIVE
void set_game_config(const char* json_string) {
    if (!json_string) return;
    cJSON* root = cJSON_Parse(json_string);
    if (!root) return;

    cJSON* players = cJSON_GetObjectItemCaseSensitive(root, "players");
    if (cJSON_IsNumber(players)) {
        int p = (int)players->valuedouble;
        if (p < 2) p = 2;
        if (p > MAX_PLAYERS) p = MAX_PLAYERS;
        game.playerCount = p;
    }

    cJSON* target = cJSON_GetObjectItemCaseSensitive(root, "targetScore");
    if (cJSON_IsNumber(target)) {
        int t = (int)target->valuedouble;
        if (t < 100) t = 100;
        if (t > 1000) t = 1000;
        game.targetScore = t;
    }

    cJSON* rounds = cJSON_GetObjectItemCaseSensitive(root, "rounds");
    if (cJSON_IsNumber(rounds)) {
        int r = (int)rounds->valuedouble;
        if (r < 1) r = 1;
        if (r > 10) r = 10;
        game.maxRounds = r;
    }

    cJSON* theme = cJSON_GetObjectItemCaseSensitive(root, "theme");
    if (cJSON_IsString(theme) && theme->valuestring) {
        const char* t = theme->valuestring;
        if (strcmp(t, "neon") == 0)         g_tableTint = (Color){120, 180, 255, 255};
        else if (strcmp(t, "crimson") == 0) g_tableTint = (Color){255, 140, 140, 255};
        else if (strcmp(t, "violet") == 0)  g_tableTint = (Color){200, 150, 255, 255};
        else if (strcmp(t, "gold") == 0)    g_tableTint = (Color){255, 220, 130, 255};
        else                                g_tableTint = (Color){255, 255, 255, 255}; // classic
    }

    cJSON_Delete(root);
}

void GameInit(Game* game) {
    memset(game, 0, sizeof(Game));
    game->state = STATE_MENU;
    game->playerCount = 2;
    game->currentPlayer = 0;
    game->currentRound = 1;
    game->maxRounds = 5;
    game->targetScore = 300;
    game->winnerId = -1;

    // Sembrar el RNG una sola vez por partida. DeckShuffle reutiliza este
    // stream, evitando barajas idénticas en rondas dentro del mismo segundo.
    srand((unsigned int)time(NULL));

    // Inicializar jugadores con nombres por defecto
    for (int i = 0; i < MAX_PLAYERS; i++) {
        game->players[i].id = i;
        if (i == 0) {
            snprintf(game->players[i].name, sizeof(game->players[i].name), "%.31s", g_player_name);
        } else {
            snprintf(game->players[i].name, sizeof(game->players[i].name), "Jugador %d", i + 1);
        }
        game->players[i].score = 0;
        game->players[i].totalRoundsWon = 0;
        game->players[i].handCount = 0;
        game->players[i].selectedCount = 0;
    }
    
    DeckInit(&game->deck);
}

void GameUpdate(Game* game) {
    // Actualizar animaciones de cartas si están activas
    UpdateCardAnimations(game);
    
    // Si estamos en reparto y la animación terminó, pasar al turno del jugador
    if (game->state == STATE_DEAL_CARDS && !game->dealingInProgress && game->animationCount > 0) {
        game->state = STATE_PLAYER_TURN;
        NOTIFY_INT("player", game->currentPlayer);
        NOTIFY("player-turn");
        game->animationCount = 0;
        game->dealCardsInitialized = false;
    }
    
    switch (game->state) {
        case STATE_MENU:
            UpdateStateMenu(game);
            break;
        case STATE_INSTRUCTIONS:
            UpdateStateInstructions(game);
            break;
        case STATE_CONFIG:
            UpdateStateConfig(game);
            break;
        case STATE_SETUP_PLAYERS:
            UpdateStateSetupPlayers(game);
            break;
        case STATE_DEAL_CARDS:
            UpdateStateDealCards(game);
            break;
        case STATE_PLAYER_TURN:
            UpdateStatePlayerTurn(game);
            break;
        case STATE_HIDE_SCREEN:
            UpdateStateHideScreen(game);
            break;
        case STATE_SHOW_RESULTS:
            UpdateStateShowResults(game);
            break;
        case STATE_ROUND_END:
            UpdateStateRoundEnd(game);
            break;
        case STATE_GAME_OVER:
            UpdateStateGameOver(game);
            break;
    }
}

// Color de fondo negro
#define TABLE_BG (Color){0, 0, 0, 255}

void GameDraw(Game* game) {
    BeginDrawing();
    DrawTableBackground();
    
    switch (game->state) {
        case STATE_MENU:
            DrawStateMenu(game);
            break;
        case STATE_INSTRUCTIONS:
            DrawStateInstructions(game);
            break;
        case STATE_CONFIG:
            DrawStateConfig(game);
            break;
        case STATE_SETUP_PLAYERS:
            DrawStateSetupPlayers(game);
            break;
        case STATE_DEAL_CARDS:
            DrawCardAnimations(game); // Dibujar animaciones de reparto
            DrawStateDealCards(game);
            break;
        case STATE_PLAYER_TURN:
            DrawStatePlayerTurn(game);
            break;
        case STATE_HIDE_SCREEN:
            DrawStateHideScreen(game);
            break;
        case STATE_SHOW_RESULTS:
            DrawStateShowResults(game);
            break;
        case STATE_ROUND_END:
            DrawStateRoundEnd(game);
            break;
        case STATE_GAME_OVER:
            DrawStateGameOver(game);
            break;
    }

    EndDrawing();
}

// ========== ESTADOS ==========

void UpdateStateMenu(Game* game) {
    if (IsKeyPressed(KEY_ENTER) || IsButtonClicked("JUGAR", GetScreenWidth()/2 - 100, 300, 200, 50)) {
        game->state = STATE_SETUP_PLAYERS;
    }
    
    // Botón INSTRUCCIONES
    if (IsButtonClicked("INSTRUCCIONES", GetScreenWidth()/2 - 100, 380, 200, 50)) {
        game->state = STATE_INSTRUCTIONS;
    }
    
    // Botón CONFIGURACIÓN
    if (IsButtonClicked("CONFIGURACION", GetScreenWidth()/2 - 100, 460, 200, 50)) {
        game->state = STATE_CONFIG;
    }
}

void UpdateStateInstructions(Game* game) {
    if (IsKeyPressed(KEY_ESCAPE) || IsButtonClicked("VOLVER", GetScreenWidth()/2 - 100, GetScreenHeight() - 80, 200, 50) || IsButtonClicked("ATRAS", GetScreenWidth() - 140, 20, 120, 40)) {
        game->state = STATE_MENU;
    }
}

void UpdateStateConfig(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int centerX = screenW / 2;
    
    if (IsKeyPressed(KEY_ESCAPE) || IsButtonClicked("VOLVER", centerX - 100, screenH - 80, 200, 50) || IsButtonClicked("ATRAS", screenW - 140, 20, 120, 40)) {
        game->state = STATE_MENU;
    }
    
    // Obtener volúmenes actuales del audio
    int masterVol = 100, musicVol = 50, sfxVol = 80;
    AudioGetVolumes(&masterVol, &musicVol, &sfxVol);
    
    int baseY = 180;
    int gapY = 100;

    // Slider Master (+/- con botones)
    if (IsButtonClicked("+", centerX + 150, baseY - 5, 40, 40)) {
        masterVol = (masterVol >= 100) ? 100 : masterVol + 10;
        AudioSetMasterVolume(masterVol / 100.0f);
    }
    if (IsButtonClicked("-", centerX - 120, baseY - 5, 40, 40)) {
        masterVol = (masterVol <= 0) ? 0 : masterVol - 10;
        AudioSetMasterVolume(masterVol / 100.0f);
    }

    // Slider Música
    if (IsButtonClicked("+", centerX + 150, baseY + gapY - 5, 40, 40)) {
        musicVol = (musicVol >= 100) ? 100 : musicVol + 10;
        AudioSetMusicVolume(musicVol / 100.0f);
    }
    if (IsButtonClicked("-", centerX - 120, baseY + gapY - 5, 40, 40)) {
        musicVol = (musicVol <= 0) ? 0 : musicVol - 10;
        AudioSetMusicVolume(musicVol / 100.0f);
    }

    // Slider SFX
    if (IsButtonClicked("+", centerX + 150, baseY + gapY * 2 - 5, 40, 40)) {
        sfxVol = (sfxVol >= 100) ? 100 : sfxVol + 10;
        AudioSetSFXVolume(sfxVol / 100.0f);
    }
    if (IsButtonClicked("-", centerX - 120, baseY + gapY * 2 - 5, 40, 40)) {
        sfxVol = (sfxVol <= 0) ? 0 : sfxVol - 10;
        AudioSetSFXVolume(sfxVol / 100.0f);
    }
}

void UpdateStateSetupPlayers(Game* game) {
    static int currentOption = 0;  // 0=jugadores, 1=rondas, 2=puntuacion
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();

    // Botón ATRAS / ESC vuelve al menú principal
    if (IsKeyPressed(KEY_ESCAPE) || IsButtonClicked("ATRAS", GetScreenWidth() - 140, 20, 120, 40)) {
        game->state = STATE_MENU;
        return;
    }

    // Cambiar entre opciones con TAB
    if (IsKeyPressed(KEY_TAB)) {
        currentOption = (currentOption + 1) % 3;
    }
    
    // Ajustar valores según opción seleccionada
    if (IsKeyPressed(KEY_UP) || IsKeyPressed(KEY_RIGHT)) {
        switch (currentOption) {
            case 0: // Jugadores
                game->playerCount++;
                if (game->playerCount > MAX_PLAYERS) game->playerCount = MAX_PLAYERS;
                break;
            case 1: // Rondas
                game->maxRounds++;
                if (game->maxRounds > 10) game->maxRounds = 10;
                break;
            case 2: // Puntuación objetivo
                game->targetScore += 50;
                if (game->targetScore > 1000) game->targetScore = 1000;
                break;
        }
    }
    if (IsKeyPressed(KEY_DOWN) || IsKeyPressed(KEY_LEFT)) {
        switch (currentOption) {
            case 0: // Jugadores
                game->playerCount--;
                if (game->playerCount < 2) game->playerCount = 2;
                break;
            case 1: // Rondas
                game->maxRounds--;
                if (game->maxRounds < 1) game->maxRounds = 1;
                break;
            case 2: // Puntuación objetivo
                game->targetScore -= 50;
                if (game->targetScore < 100) game->targetScore = 100;
                break;
        }
    }
    
    // Botones de ajuste con ratón - coordenadas deben coincidir con renderer.c
    int startY = 140;
    int spacing = 100;
    int btnW = 50, btnH = 45;
    int labelW = 220;
    int centerX = screenW / 2;
    
    // Jugadores - botones +/-
    if (IsButtonClicked("+", centerX + labelW/2 + 10, startY - 8, btnW, btnH)) {
        game->playerCount++;
        if (game->playerCount > MAX_PLAYERS) game->playerCount = MAX_PLAYERS;
    }
    if (IsButtonClicked("-", centerX - labelW/2 - btnW - 10, startY - 8, btnW, btnH)) {
        game->playerCount--;
        if (game->playerCount < 2) game->playerCount = 2;
    }
    
    // Rondas - botones +/-
    if (IsButtonClicked("+", centerX + labelW/2 + 10, startY + spacing - 8, btnW, btnH)) {
        game->maxRounds++;
        if (game->maxRounds > 10) game->maxRounds = 10;
    }
    if (IsButtonClicked("-", centerX - labelW/2 - btnW - 10, startY + spacing - 8, btnW, btnH)) {
        game->maxRounds--;
        if (game->maxRounds < 1) game->maxRounds = 1;
    }
    
    // Puntuación - botones +/-
    if (IsButtonClicked("+", centerX + labelW/2 + 10, startY + spacing*2 - 8, btnW, btnH)) {
        game->targetScore += 50;
        if (game->targetScore > 1000) game->targetScore = 1000;
    }
    if (IsButtonClicked("-", centerX - labelW/2 - btnW - 10, startY + spacing*2 - 8, btnW, btnH)) {
        game->targetScore -= 50;
        if (game->targetScore < 100) game->targetScore = 100;
    }
    
    // Botón CONTINUAR
    if (IsKeyPressed(KEY_ENTER) || IsButtonClicked("CONTINUAR", screenW/2 - 100, screenH - 90, 200, 55)) {
        game->state = STATE_DEAL_CARDS;
    }
}

void UpdateStateDealCards(Game* game) {
    // Solo inicializar una vez
    if (!game->dealCardsInitialized) {
        game->dealCardsInitialized = true;
        
        DeckShuffle(&game->deck);
        
        // Repartir 8 cartas a cada jugador
        for (int p = 0; p < game->playerCount; p++) {
            game->players[p].handCount = 0;
            game->players[p].selectedCount = 0;
            game->players[p].discardCount = 0;
            game->players[p].hasDiscarded = false;
            for (int i = 0; i < CARDS_PER_HAND; i++) {
                game->players[p].hand[i] = DeckDraw(&game->deck);
                game->players[p].hand[i].selected = false;
                game->players[p].hand[i].hover = false;
                game->players[p].hand[i].hoverScale = 1.0f;
                game->players[p].handCount++;
            }
        }
        
        game->currentPlayer = 0;
        
        // Iniciar animación de reparto
        StartDealAnimation(game);
    }
    // No cambiamos de estado inmediatamente, esperamos a que termine la animación
    // El cambio se hará en GameUpdate cuando dealingInProgress sea false
}

// Función para verificar si las animaciones de reparto terminaron
bool IsDealAnimationComplete(Game* game) {
    return !game->dealingInProgress;
}

void UpdateStatePlayerTurn(Game* game) {
    Player* current = &game->players[game->currentPlayer];
    
    // ========== DETECCIÓN DE HOVER Y ESCALA ANIMADA ==========
    Vector2 mousePos = GetMousePosition();
    float screenH = GetScreenHeight();
    float screenW = GetScreenWidth();
    float startX = GetHandStartX(current->handCount, screenW);
    int marginTop = 45;
    int marginBottom = 130;
    float cardAreaTop = marginTop + 100;
    float cardAreaBottom = screenH - marginBottom - 15;
    float cardY = cardAreaTop + (cardAreaBottom - cardAreaTop) / 2;
    
    for (int i = 0; i < current->handCount; i++) {
        float cardX = startX + i * (CARD_WIDTH * 1.2f + CARD_SPACING);
        float offsetY = current->hand[i].selected ? -25 : 0;
        Rectangle cardRect = {cardX, cardY + offsetY, CARD_WIDTH * 1.2f, CARD_HEIGHT * 1.2f};
        
        // Detectar hover
        current->hand[i].hover = CheckCollisionPointRec(mousePos, cardRect);
        
        // Animar escala (transición suave)
        float targetScale = (current->hand[i].hover || current->hand[i].selected) ? 1.15f : 1.0f;
        float currentScale = current->hand[i].hoverScale;
        current->hand[i].hoverScale = currentScale + (targetScale - currentScale) * 0.15f; // Lerp suave
    }
    
    // Click en cartas para seleccionar/deseleccionar
    Vector2 clickPos = GetMousePosition();
    
    #if defined(PLATFORM_WEB)
    if (GetTouchPointCount() > 0) {
        clickPos = GetTouchPosition(0);
    }
    #endif
    
    if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
        for (int i = 0; i < current->handCount; i++) {
            float cardX = startX + i * (CARD_WIDTH * 1.2f + CARD_SPACING);
            float offsetY = current->hand[i].selected ? -25 : 0;
            Rectangle cardRect = {cardX, cardY + offsetY, CARD_WIDTH * 1.2f, CARD_HEIGHT * 1.2f};
            
            if (CheckCollisionPointRec(clickPos, cardRect)) {
                if (current->hand[i].selected) {
                    // Deseleccionar
                    current->hand[i].selected = false;
                    AudioPlayCardSelect();
                    // Remover de selectedCards
                    for (int j = 0; j < current->selectedCount; j++) {
                        if (current->selectedCards[j].suit == current->hand[i].suit &&
                            current->selectedCards[j].rank == current->hand[i].rank) {
                            for (int k = j; k < current->selectedCount - 1; k++) {
                                current->selectedCards[k] = current->selectedCards[k + 1];
                            }
                            current->selectedCount--;
                            break;
                        }
                    }
                } else {
                    // Seleccionar (máximo 5)
                    if (current->selectedCount < CARDS_TO_SELECT) {
                        current->hand[i].selected = true;
                        current->selectedCards[current->selectedCount] = current->hand[i];
                        current->selectedCount++;
                        AudioPlayCardSelect();
                    }
                }
                break;
            }
        }
    }
    
    int btnRowY = screenH - marginBottom;
    
    // ========== BOTONES DE ORDENAMIENTO ==========
    int sortBtnY = btnRowY + 15;  // Coincide con renderer.c
    if (IsButtonClicked("VALOR", 20, sortBtnY + 5, 75, 38)) {
        AudioPlayButtonClick();
        SortHandByRank(current);
    }
    if (IsButtonClicked("PALO", 105, sortBtnY + 5, 75, 38)) {
        AudioPlayButtonClick();
        SortHandBySuit(current);
    }
    
    // Botón DESCARTAR (rojo, a la derecha) - máximo 5 cartas, 1 vez por turno
    if (!current->hasDiscarded) {
        if (IsButtonClicked("DESCARTAR", screenW - 155, btnRowY, 135, 48)) {
            AudioPlayCardDiscard();
            DiscardAndDrawCards(game, current);
        }
    }
    
    // Confirmar mano con ENTER o botón (requiere al menos 1 carta seleccionada)
    bool canPlay = current->selectedCount >= 1;
    if (canPlay && (IsKeyPressed(KEY_ENTER) || IsButtonClicked("CONFIRMAR", screenW/2 - 100, btnRowY, 200, 48))) {   
        // Evaluar la mano seleccionada y acumular su puntuación
        current->lastResult = EvaluateHand(current->selectedCards, current->selectedCount);
        current->score += current->lastResult.score;
        
        // Resetear estado de descarte para el siguiente turno
        current->hasDiscarded = false;
        current->discardCount = 0;
        
        // Pasar al siguiente jugador
        game->currentPlayer++;
        if (game->currentPlayer >= game->playerCount) {
            game->state = STATE_SHOW_RESULTS;
        } else {
            game->state = STATE_HIDE_SCREEN;
        }
    }
}

void UpdateStateHideScreen(Game* game) {
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    if (IsKeyPressed(KEY_ENTER) || IsButtonClicked("ESTOY LISTO", screenW/2 - 100, screenH/2 + 80, 200, 50)) {
        game->state = STATE_PLAYER_TURN;
        NOTIFY_INT("player", game->currentPlayer);
        NOTIFY("player-turn");
    }
}

void UpdateStateShowResults(Game* game) {
    // Mostrar todas las manos por un tiempo
    static float timer = 0;
    timer += GetFrameTime();
    
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    
    if (IsKeyPressed(KEY_ENTER) || timer > 5.0f || IsButtonClicked("SIGUIENTE", screenW/2 - 100, screenH - 80, 200, 50)) {
        timer = 0;
        game->state = STATE_ROUND_END;
    }
}

void UpdateStateRoundEnd(Game* game) {
    int roundWinner = CalculateRoundWinner(game);
    if (roundWinner >= 0) {
        game->players[roundWinner].totalRoundsWon++;
        AudioPlayRoundEnd();
    }

    if (CheckGameEnd(game)) {
        // Fijar el ganador de la partida antes de la pantalla final.
        // Sin esto, winnerId quedaba en -1 y los high scores no se guardaban.
        game->winnerId = GetGameWinner(game);
        game->state = STATE_GAME_OVER;
        NOTIFY_INT("score", game->players[game->winnerId].score);
        NOTIFY("gameover");

        // Reporta el resultado al parent (Angular). players[0] es el humano
        // (su nombre se fija vía set-username); el rival es la mejor IA.
        {
            int my_score = game->players[0].score;
            int opp_score = 0;
            for (int i = 1; i < game->playerCount; i++) {
                if (game->players[i].score > opp_score)
                    opp_score = game->players[i].score;
            }
            EmitGameFinished(game->players[game->winnerId].name, my_score, opp_score);
        }

        AudioPlayWin();
    } else {
        NOTIFY_INT("round", game->currentRound);
        NOTIFY("round-end");
        StartNewRound(game);  // Avanza de ronda y vuelve a repartir
    }
}

void UpdateStateGameOver(Game* game) {
    static bool highScoresProcessed = false;
    int screenW = GetScreenWidth();
    int screenH = GetScreenHeight();
    int marginBottom = 120;

    if (!highScoresProcessed) {
        HighScoreEntry entries[MAX_HIGH_SCORES];
        int count = 0;
        LoadHighScores(entries, &count);

        if (game->winnerId >= 0) {
            AddHighScore(entries, &count,
                game->players[game->winnerId].name,
                game->players[game->winnerId].score,
                game->players[game->winnerId].totalRoundsWon);
            SaveHighScores(entries, count);
        }

        highScoresProcessed = true;
    }
    
    if (IsKeyPressed(KEY_ENTER) || IsKeyPressed(KEY_R) ||
        IsButtonClicked("JUGAR DE NUEVO", screenW/2 - 120, screenH - marginBottom - 65, 240, 55)) {
        highScoresProcessed = false;
        GameInit(game);
    }
}

// ========== UTILIDADES ==========

void StartNewRound(Game* game) {
    game->currentRound++;
    game->currentPlayer = 0;
    game->dealCardsInitialized = false;  // Fuerza el reparto en STATE_DEAL_CARDS
    game->state = STATE_DEAL_CARDS;
}

int CalculateRoundWinner(Game* game) {
    int bestPlayer = -1;
    int bestScore = -1;
    HandType bestHand = HAND_HIGH_CARD;
    
    for (int i = 0; i < game->playerCount; i++) {
        Player* p = &game->players[i];
        HandResult* result = &p->lastResult;
        
        // Comparar primero por tipo de mano
        if (result->type > bestHand) {
            bestHand = result->type;
            bestScore = result->score;
            bestPlayer = i;
        } else if (result->type == bestHand) {
            // Desempate por score
            if (result->score > bestScore) {
                bestScore = result->score;
                bestPlayer = i;
            }
        }
    }
    
    return bestPlayer;
}

bool CheckGameEnd(Game* game) {
    for (int i = 0; i < game->playerCount; i++) {
        if (game->players[i].score >= game->targetScore) {
            return true;
        }
    }

    if (game->currentRound >= game->maxRounds) {
        return true;
    }

    return false;
}

void DiscardAndDrawCards(Game* game, Player* player) {
    // Contar cartas seleccionadas para descartar (máximo 5)
    int cardsToDiscard = player->selectedCount;
    if (cardsToDiscard > 5) cardsToDiscard = 5;
    if (cardsToDiscard == 0) return;
    
    // Remover cartas seleccionadas de la mano
    for (int i = 0; i < player->handCount; i++) {
        if (player->hand[i].selected) {
            // Desplazar todas las cartas posteriores
            for (int j = i; j < player->handCount - 1; j++) {
                player->hand[j] = player->hand[j + 1];
            }
            player->handCount--;
            i--; // Revisar la misma posición nuevamente
        }
    }
    
    // Limpiar selección
    player->selectedCount = 0;
    for (int i = 0; i < player->handCount; i++) {
        player->hand[i].selected = false;
        player->hand[i].hover = false;
        player->hand[i].hoverScale = 1.0f;
    }
    
    // Robar nuevas cartas hasta tener 8
    for (int i = player->handCount; i < CARDS_PER_HAND; i++) {
        if (!DeckIsEmpty(&game->deck)) {
            player->hand[i] = DeckDraw(&game->deck);
            player->hand[i].selected = false;
            player->hand[i].hover = false;
            player->hand[i].hoverScale = 1.0f;
            player->handCount++;
        }
    }
    
    // Marcar que ya usó el descarte
    player->hasDiscarded = true;
    player->discardCount = cardsToDiscard;
}

int GetGameWinner(Game* game) {
    int winner = -1;
    int maxScore = -1;
    
    for (int i = 0; i < game->playerCount; i++) {
        if (game->players[i].score > maxScore) {
            maxScore = game->players[i].score;
            winner = i;
        }
    }
    
    return winner;
}

// ========== FUNCIONES DE ORDENAMIENTO ==========

// Helper para comparar cartas por valor (mayor a menor)
// El As se almacena como rank=1 pero vale 14 (igual que en poker_hand.c)
static int RankSortValue(int rank) {
    return (rank == 1) ? 14 : rank;
}

static int CompareCardsByRankDesc(const void* a, const void* b) {
    const Card* cardA = (const Card*)a;
    const Card* cardB = (const Card*)b;
    return RankSortValue(cardB->rank) - RankSortValue(cardA->rank);  // Mayor a menor
}

// Helper para contar cartas por palo
static void CountSuits(Player* player, int* suitCounts) {
    for (int s = 0; s < 4; s++) suitCounts[s] = 0;
    for (int i = 0; i < player->handCount; i++) {
        suitCounts[player->hand[i].suit]++;
    }
}

// Ordenar mano por valor de carta (mayor a menor)
void SortHandByRank(Player* player) {
    if (player->handCount < 2) return;
    qsort(player->hand, player->handCount, sizeof(Card), CompareCardsByRankDesc);
}

// Ordenar mano por palo (agrupando por palo con más cartas)
void SortHandBySuit(Player* player) {
    if (player->handCount < 2) return;
    
    int suitCounts[4];
    CountSuits(player, suitCounts);
    
    // Ordenar usando qsort_r si está disponible, o implementación manual
    // Usamos un bubble sort simple para máxima compatibilidad
    for (int i = 0; i < player->handCount - 1; i++) {
        for (int j = 0; j < player->handCount - i - 1; j++) {
            int suitCountJ = suitCounts[player->hand[j].suit];
            int suitCountJ1 = suitCounts[player->hand[j + 1].suit];
            
            bool shouldSwap = false;
            if (suitCountJ1 > suitCountJ) {
                // Palo con más cartas primero
                shouldSwap = true;
            } else if (suitCountJ1 == suitCountJ) {
                int suitJ = player->hand[j].suit;
                int suitJ1 = player->hand[j + 1].suit;
                if (suitJ1 > suitJ) {
                    // Mismo conteo pero distinto palo: agrupar por índice de palo
                    shouldSwap = true;
                } else if (suitJ1 == suitJ) {
                    // Mismo palo: ordenar por valor (As=14 arriba)
                    if (RankSortValue(player->hand[j + 1].rank) > RankSortValue(player->hand[j].rank)) {
                        shouldSwap = true;
                    }
                }
            }
            
            if (shouldSwap) {
                Card temp = player->hand[j];
                player->hand[j] = player->hand[j + 1];
                player->hand[j + 1] = temp;
            }
        }
    }
}

// ========== FUNCIONES DE ANIMACIÓN ==========

void StartDealAnimation(Game* game) {
    // Posición inicial del mazo (centro superior de la pantalla)
    float deckX = GetScreenWidth() / 2.0f - CARD_WIDTH / 2;
    float deckY = 100;

    // Posición central de las cartas en mano
    float handY = GetScreenHeight() / 2.0f;
    float handStartX = GetHandStartX(CARDS_PER_HAND, GetScreenWidth());

    game->animationCount = 0;
    game->dealingInProgress = true;

    // Solo se anima la mano del jugador actual: es la única que se mostrará
    // tras el reparto. El reparto lógico ya entregó cartas a todos los
    // jugadores en UpdateStateDealCards. Así nunca se exceden las
    // MAX_CARD_ANIMATIONS ni se solapan manos de varios jugadores.
    Player* player = &game->players[game->currentPlayer];
    for (int i = 0; i < CARDS_PER_HAND && game->animationCount < MAX_CARD_ANIMATIONS; i++) {
        CardAnimation* anim = &game->cardAnimations[game->animationCount];
        anim->active = true;
        anim->cardIndex = i;
        anim->playerIndex = game->currentPlayer;
        anim->startX = deckX;
        anim->startY = deckY;
        anim->currentX = deckX;
        anim->currentY = deckY;
        anim->targetX = handStartX + i * (CARD_WIDTH * 1.2f + CARD_SPACING);
        anim->targetY = handY;
        anim->progress = 0.0f;
        anim->speed = 0.03f + (i * 0.005f);  // Velocidad escalonada por carta
        anim->card = player->hand[i];
        game->animationCount++;
    }
}

void UpdateCardAnimations(Game* game) {
    if (!game->dealingInProgress) return;
    
    bool anyActive = false;
    
    for (int i = 0; i < game->animationCount; i++) {
        CardAnimation* anim = &game->cardAnimations[i];
        if (!anim->active) continue;
        
        anyActive = true;
        anim->progress += anim->speed;
        
        if (anim->progress >= 1.0f) {
            anim->progress = 1.0f;
            anim->active = false;
            anim->currentX = anim->targetX;
            anim->currentY = anim->targetY;
        } else {
            // Interpolación suave (ease-out)
            float t = anim->progress;
            float easeOut = 1.0f - (1.0f - t) * (1.0f - t);
            anim->currentX = anim->startX + (anim->targetX - anim->startX) * easeOut;
            anim->currentY = anim->startY + (anim->targetY - anim->startY) * easeOut;
        }
    }
    
    if (!anyActive) {
        game->dealingInProgress = false;
    }
}

void DrawCardAnimations(Game* game) {
    for (int i = 0; i < game->animationCount; i++) {
        CardAnimation* anim = &game->cardAnimations[i];
        if (!anim->active && anim->progress >= 1.0f) continue;
        
        // Dibujar placeholder en posición destino antes de que llegue la carta
        if (anim->progress < 0.3f) {
            // Dibujar carta boca abajo como placeholder en el destino
            DrawCardBack(anim->targetX, anim->targetY, 1.0f);
        }
        
        // Dibujar carta animada (boca abajo mientras se mueve)
        DrawCard(&anim->card, anim->currentX, anim->currentY, false, 1.0f);
    }
}

// ========== FUNCIONES DE HIGH SCORES ==========

void LoadHighScores(HighScoreEntry* entries, int* count) {
    *count = 0;
    FILE* file = fopen("highscores.dat", "rb");
    if (file) {
        if (fread(count, sizeof(int), 1, file) != 1) {
            *count = 0;  // Archivo corrupto o vacío
        }
        if (*count < 0) *count = 0;
        if (*count > MAX_HIGH_SCORES) *count = MAX_HIGH_SCORES;
        if (fread(entries, sizeof(HighScoreEntry), *count, file) != (size_t)*count) {
            *count = 0;  // Datos incompletos: descartar
        }
        fclose(file);
    }
}

void SaveHighScores(HighScoreEntry* entries, int count) {
    if (count > MAX_HIGH_SCORES) count = MAX_HIGH_SCORES;
    FILE* file = fopen("highscores.dat", "wb");
    if (file) {
        fwrite(&count, sizeof(int), 1, file);
        fwrite(entries, sizeof(HighScoreEntry), count, file);
        fclose(file);
    }
}

bool AddHighScore(HighScoreEntry* entries, int* count, const char* name, int score, int roundsWon) {
    // Encontrar posición para insertar (ordenado por puntuación descendente)
    int insertPos = -1;
    for (int i = 0; i < *count; i++) {
        if (score > entries[i].score) {
            insertPos = i;
            break;
        }
    }
    
    // Si no hay espacio y la puntuación es menor que todas, no añadir
    if (insertPos == -1 && *count >= MAX_HIGH_SCORES) {
        return false;
    }
    
    // Si no encontró posición pero hay espacio, añadir al final
    if (insertPos == -1) {
        insertPos = *count;
    }
    
    // Mover entradas para hacer espacio
    for (int i = *count - 1; i >= insertPos; i--) {
        if (i + 1 < MAX_HIGH_SCORES) {
            entries[i + 1] = entries[i];
        }
    }
    
    // Insertar nueva entrada
    strncpy(entries[insertPos].name, name, 31);
    entries[insertPos].name[31] = '\0';
    entries[insertPos].score = score;
    entries[insertPos].roundsWon = roundsWon;
    
    // Fecha actual
    time_t now = time(NULL);
    struct tm* tm = localtime(&now);
    if (tm) {
        strftime(entries[insertPos].date, sizeof(entries[insertPos].date), "%Y-%m-%d", tm);
    } else {
        entries[insertPos].date[0] = '\0';
    }
    
    if (*count < MAX_HIGH_SCORES) {
        (*count)++;
    }
    
    return true;
}
