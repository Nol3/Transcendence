#include "audio.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>

static bool audioInitialized = false;

typedef struct {
    Sound sound;
    bool loaded;
} SoundEntry;

static SoundEntry soundEntries[8] = {0};
static bool soundsLoaded = false;
static bool soundsFailed = false;
static int masterVolume = 100;
static int musicVolume = 50;
static int sfxVolume = 80;

static const char* SOUND_FILES[8] = {
    "assets/audio/card_flip.wav",
    "assets/audio/card_select.wav",
    "assets/audio/card_deal.wav",
    "assets/audio/button_click.wav",
    "assets/audio/win_round.wav",
    "assets/audio/win_game.wav",
    "assets/audio/discard.wav",
    "assets/audio/error.wav"
};

#define IDX_CARD_FLIP     0
#define IDX_CARD_SELECT   1
#define IDX_CARD_DEAL     2
#define IDX_BUTTON_CLICK  3
#define IDX_WIN_ROUND     4
#define IDX_WIN_GAME      5
#define IDX_DISCARD      6
#define IDX_ERROR        7

static Wave GenWaveSineManual(float duration, float frequency, int sampleRate) {
    Wave wave = {0};
    wave.frameCount = (int)(sampleRate * duration);
    wave.sampleRate = sampleRate;
    wave.sampleSize = 16;
    wave.channels = 1;
    int dataSize = wave.frameCount * sizeof(short);
    wave.data = RL_MALLOC(dataSize);
    short *data = (short*)wave.data;
    for (int i = 0; i < wave.frameCount; i++) {
        float time = (float)i / sampleRate;
        float value = sinf(2.0f * PI * frequency * time);
        data[i] = (short)(value * 32000);
    }
    return wave;
}

static void PlayTone(float frequency, float duration) {
    if (!audioInitialized) return;
    Wave wave = GenWaveSineManual(duration, frequency, 22050);
    Sound sound = LoadSoundFromWave(wave);
    if (sound.frameCount > 0) {
        SetSoundVolume(sound, masterVolume / 100.0f);
        PlaySound(sound);
    }
    UnloadWave(wave);
}

static void LoadSounds(void) {
    if (soundsLoaded || soundsFailed) return;
    int loaded = 0;
    for (int i = 0; i < 8; i++) {
        soundEntries[i].sound = LoadSound(SOUND_FILES[i]);
        if (soundEntries[i].sound.frameCount > 0) {
            soundEntries[i].loaded = true;
            loaded++;
        }
    }
    if (loaded == 0) {
        soundsFailed = true;
    } else {
        soundsLoaded = true;
    }
}

static void PlaySoundByIndex(int idx) {
    if (!audioInitialized || idx < 0 || idx >= 8) return;
    if (soundsFailed) {
        float tones[] = {800, 800, 600, 600, 523, 523, 400, 200};
        PlayTone(tones[idx], 0.08f);
        return;
    }
    if (!soundsLoaded) LoadSounds();
    if (soundEntries[idx].loaded) {
        SetSoundVolume(soundEntries[idx].sound, (masterVolume / 100.0f) * (sfxVolume / 100.0f));
        PlaySound(soundEntries[idx].sound);
    } else {
        float tones[] = {800, 800, 600, 600, 523, 523, 400, 200};
        PlayTone(tones[idx], 0.08f);
    }
}

void AudioInit(void) {
    if (!audioInitialized) {
        InitAudioDevice();
        audioInitialized = true;
    }
}

void AudioClose(void) {
    if (soundsLoaded) {
        for (int i = 0; i < 8; i++) {
            if (soundEntries[i].loaded) {
                UnloadSound(soundEntries[i].sound);
                soundEntries[i].loaded = false;
            }
        }
        soundsLoaded = false;
    }
    soundsFailed = false;
    if (audioInitialized) {
        CloseAudioDevice();
        audioInitialized = false;
    }
}

void AudioPlayCardSelect(void)  { PlaySoundByIndex(IDX_CARD_SELECT); }
void AudioPlayCardDiscard(void) { PlaySoundByIndex(IDX_DISCARD); }
void AudioPlayButtonClick(void) { PlaySoundByIndex(IDX_BUTTON_CLICK); }
void AudioPlayWin(void)         { PlaySoundByIndex(IDX_WIN_GAME); }
void AudioPlayRoundEnd(void)    { PlaySoundByIndex(IDX_WIN_ROUND); }
void AudioPlayGameStart(void)    { PlaySoundByIndex(IDX_CARD_DEAL); }

void AudioSetMasterVolume(float volume) {
    if (volume < 0.0f) volume = 0.0f;
    if (volume > 1.0f) volume = 1.0f;
    masterVolume = (int)(volume * 100);
    SetMasterVolume(volume);
}

void AudioSetMusicVolume(float volume) {
    if (volume < 0.0f) volume = 0.0f;
    if (volume > 1.0f) volume = 1.0f;
    musicVolume = (int)(volume * 100);
}

void AudioSetSFXVolume(float volume) {
    if (volume < 0.0f) volume = 0.0f;
    if (volume > 1.0f) volume = 1.0f;
    sfxVolume = (int)(volume * 100);
}

void AudioSetVolume(float master, float music, float sfx) {
    AudioSetMasterVolume(master);
    AudioSetMusicVolume(music);
    AudioSetSFXVolume(sfx);
}

void AudioGetVolumes(int* master, int* music, int* sfx) {
    if (master) *master = masterVolume;
    if (music) *music = musicVolume;
    if (sfx)  *sfx = sfxVolume;
}

typedef struct {
    Wave wave;
    Sound sound;
    bool playing;
    float phase;
    float targetFreq;
    float currentFreq;
} MusicTrack;

static MusicTrack musicTrack = {0};

static float GetNextMusicSample(float t) {
    float freq = musicTrack.currentFreq;
    float bass = sinf(2.0f * PI * freq * t) * 0.3f;
    float pad  = sinf(2.0f * PI * (freq * 1.5f) * t + sinf(t * 0.5f)) * 0.15f;
    float arp  = sinf(2.0f * PI * (freq * 2.0f) * t) *
                 (t > 0 && t < 0.05f ? t / 0.05f :
                  t > 0.25f && t < 0.30f ? (0.30f - t) / 0.05f :
                  t > 0.5f && t < 0.55f ? (t - 0.5f) / 0.05f :
                  t > 0.75f && t < 0.80f ? (0.80f - t) / 0.05f : 0) * 0.2f;
    return (bass + pad + arp) * (musicVolume / 100.0f);
}

void AudioStartMusic(void) {
    if (!audioInitialized || musicTrack.playing) return;
    musicTrack.wave.frameCount = 44100 * 4;
    musicTrack.wave.sampleRate = 44100;
    musicTrack.wave.sampleSize = 16;
    musicTrack.wave.channels = 1;
    musicTrack.wave.data = RL_MALLOC(musicTrack.wave.frameCount * sizeof(short));
    short* data = (short*)musicTrack.wave.data;
    for (int i = 0; i < musicTrack.wave.frameCount; i++) {
        float t = (float)i / 44100.0f;
        float section = fmodf(t, 4.0f);
        if (section < 1.0f) musicTrack.targetFreq = 110.0f;
        else if (section < 2.0f) musicTrack.targetFreq = 130.81f;
        else if (section < 3.0f) musicTrack.targetFreq = 98.0f;
        else musicTrack.targetFreq = 123.47f;
        musicTrack.currentFreq += (musicTrack.targetFreq - musicTrack.currentFreq) * 0.001f;
        data[i] = (short)(GetNextMusicSample(t) * 28000.0f);
    }
    musicTrack.sound = LoadSoundFromWave(musicTrack.wave);
    musicTrack.playing = true;
    musicTrack.phase = 0.0f;
    SetSoundVolume(musicTrack.sound, musicVolume / 100.0f);
    PlaySound(musicTrack.sound);
}

void AudioStopMusic(void) {
    if (musicTrack.playing) {
        StopSound(musicTrack.sound);
        UnloadSound(musicTrack.sound);
        RL_FREE(musicTrack.wave.data);
        musicTrack.playing = false;
    }
}

void AudioUpdateMusic(void) {
    if (musicTrack.playing) {
        SetSoundVolume(musicTrack.sound, musicVolume / 100.0f);
    }
}
