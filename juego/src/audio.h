#ifndef AUDIO_H
#define AUDIO_H

#include "raylib.h"

void AudioInit(void);
void AudioClose(void);

void AudioPlayCardSelect(void);
void AudioPlayCardDiscard(void);
void AudioPlayButtonClick(void);
void AudioPlayWin(void);
void AudioPlayRoundEnd(void);
void AudioPlayGameStart(void);

void AudioStartMusic(void);
void AudioStopMusic(void);
void AudioUpdateMusic(void);

void AudioSetMasterVolume(float volume);
void AudioSetMusicVolume(float volume);
void AudioSetSFXVolume(float volume);
void AudioSetVolume(float master, float music, float sfx);
void AudioGetVolumes(int* master, int* music, int* sfx);

#endif // AUDIO_H
