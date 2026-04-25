#ifndef GAME_API_H
#define GAME_API_H

#include <stdbool.h>

void GamePause(bool paused);
bool GameIsPaused(void);
void GameRestart(void);
void GameSetVolume(float master, float music, float sfx);

#endif