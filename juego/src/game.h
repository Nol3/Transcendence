#ifndef GAME_H
#define GAME_H

#include "card.h"
#include "poker_hand.h"
#include "joker.h"

#define MAX_PLAYERS 4
#define CARDS_PER_HAND 8
#define CARDS_TO_SELECT 5
#define ROUNDS_TO_WIN 5
#define TARGET_SCORE 300

typedef enum {
    STATE_MENU = 0,
    STATE_INSTRUCTIONS,
    STATE_CONFIG,
    STATE_SETUP_PLAYERS,
    STATE_DEAL_CARDS,
    STATE_PLAYER_TURN,
    STATE_HIDE_SCREEN,
    STATE_SHOW_RESULTS,
    STATE_ROUND_END,
    STATE_SHOP,
    STATE_GAME_OVER
} GameState;

typedef struct {
    int id;
    char name[32];
    int score;
    int totalRoundsWon;
    Card hand[CARDS_PER_HAND];        // 8 cartas repartidas
    int handCount;
    Card selectedCards[CARDS_TO_SELECT]; // 5 cartas seleccionadas
    int selectedCount;
    HandResult lastResult;
    int discardCount;     // Cuántas cartas ha descartado este turno
    bool hasDiscarded;    // Ya usó su descarte este turno
} Player;

// Estructura para animación de reparto de cartas
typedef struct {
    bool active;
    int cardIndex;
    int playerIndex;
    float startX, startY;
    float currentX, currentY;
    float targetX, targetY;
    float progress;
    float speed;
    Card card;
} CardAnimation;

#define MAX_CARD_ANIMATIONS 16
#define MAX_HIGH_SCORES 10

// Estructura para entrada de high score
typedef struct {
    char name[32];
    int score;
    int roundsWon;
    char date[20];  // Fecha en formato YYYY-MM-DD
} HighScoreEntry;

typedef struct {
    GameState state;
    Player players[MAX_PLAYERS];
    int playerCount;
    int currentPlayer;
    int currentRound;
    int maxRounds;        // Número de rondas configurables (default: 5)
    int targetScore;      // Puntuación objetivo configurable (default: 300)
    Deck deck;
    int winnerId;  // -1 si no hay ganador aún
    
    // Animaciones
CardAnimation cardAnimations[MAX_CARD_ANIMATIONS];
    int animationCount;
    bool dealingInProgress;
    bool dealCardsInitialized;
    JokerSystem jokerSystem;
} Game;

// Funciones principales
void GameInit(Game* game);
void GameUpdate(Game* game);
void GameDraw(Game* game);

// Manejo de estados
void UpdateStateMenu(Game* game);
void UpdateStateInstructions(Game* game);
void UpdateStateConfig(Game* game);
void UpdateStateSetupPlayers(Game* game);
void UpdateStateDealCards(Game* game);
void UpdateStatePlayerTurn(Game* game);
void UpdateStateHideScreen(Game* game);
void UpdateStateShowResults(Game* game);
void UpdateStateRoundEnd(Game* game);
void UpdateStateShop(Game* game);
void UpdateStateGameOver(Game* game);

// Utilidades del juego
void StartNewRound(Game* game);
void DealCardsToPlayer(Game* game, int playerId);
void SelectCardForPlayer(Player* player, int handIndex);
void DeselectCardForPlayer(Player* player, int selectedIndex);
void DiscardAndDrawCards(Game* game, Player* player);
int CalculateRoundWinner(Game* game);
bool CheckGameEnd(Game* game);

// Funciones de ordenamiento
void SortHandByRank(Player* player);   // Ordenar por valor (mayor a menor)
void SortHandBySuit(Player* player);  // Ordenar por palo (agrupado)

// Funciones de animación
void StartDealAnimation(Game* game);
void UpdateCardAnimations(Game* game);
void DrawCardAnimations(Game* game);
bool IsDealAnimationComplete(Game* game);

// Funciones de high scores
void LoadHighScores(HighScoreEntry* entries, int* count);
void SaveHighScores(HighScoreEntry* entries, int count);
bool AddHighScore(HighScoreEntry* entries, int* count, const char* name, int score, int roundsWon);

// Utilidades
int GetGameWinner(Game* game);

#endif // GAME_H
