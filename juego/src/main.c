#include "raylib.h"
#include "game.h"
#include "card_textures.h"
#include "renderer.h"
#include "audio.h"

#if defined(PLATFORM_WEB)
    #include <emscripten/emscripten.h>
#endif

#define SCREEN_WIDTH 1280
#define SCREEN_HEIGHT 720
#define TITLE "Poker Race - Juego de Cartas"

Game game;

void UpdateDrawFrame(void) {
    GameUpdate(&game);
    GameDraw(&game);
}

int main(void) {
    InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, TITLE);
    SetTargetFPS(60);
    SetExitKey(KEY_NULL);

    AudioInit();
    LoadGameFonts();
    LoadTableTexture();
    LoadCardTextures(&g_cardTextures);
    GameInit(&game);
    AudioPlayGameStart();
    AudioStartMusic();

#if defined(PLATFORM_WEB)
    emscripten_set_main_loop(UpdateDrawFrame, 0, 1);
#else
    while (!WindowShouldClose()) {
        UpdateDrawFrame();
    }
#endif

    AudioStopMusic();
    UnloadCardTextures(&g_cardTextures);
    UnloadGameFonts();
    AudioClose();
    CloseWindow();
    return 0;
}
