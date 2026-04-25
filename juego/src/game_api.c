#include "game_api.h"
#include "game.h"
#include "audio.h"
#include <stdbool.h>

extern Game game;

static bool isPaused = false;

void GamePause(bool paused) {
    isPaused = paused;
}

bool GameIsPaused(void) {
    return isPaused;
}

void GameRestart(void) {
    GameInit(&game);
}

void GameSetVolume(float master, float music, float sfx) {
    AudioSetVolume(master, music, sfx);
}