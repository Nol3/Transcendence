# Makefile para Poker Race - Juego de Cartas
# Compila para Desktop (Windows/Linux/Mac) y Web (Emscripten)

# Detectar sistema operativo
ifeq ($(OS),Windows_NT)
    PLATFORM_OS := WINDOWS
else
    UNAMEOS := $(shell uname)
    ifeq ($(UNAMEOS),Linux)
        PLATFORM_OS := LINUX
    else ifeq ($(UNAMEOS),Darwin)
        PLATFORM_OS := OSX
    endif
endif

# Configuración
PROJECT_NAME := poker_race
SRC_DIR := src
BUILD_DIR := build
WEB_DIR := web

SOURCES := $(wildcard $(SRC_DIR)/*.c)

# === COMPILACIÓN DESKTOP ===

# Windows con MinGW
ifeq ($(PLATFORM_OS),WINDOWS)
    CC := gcc
    RAYLIB_DIR := ../raylib-6.0_win64_mingw-w64
    CFLAGS := -Wall -std=c99 -O2 -I$(RAYLIB_DIR)/include
    LDFLAGS := -L$(RAYLIB_DIR)/lib -lraylib -lopengl32 -lgdi32 -lwinmm
    TARGET := $(BUILD_DIR)/$(PROJECT_NAME).exe
endif

# Linux (incluye WSL)
ifeq ($(PLATFORM_OS),LINUX)
    CC := gcc
    # Detectar si estamos en WSL (verificando existencia de directorio Windows)
    WSL_RAYLIB_DIR := /mnt/c/Users/aleja/Desktop/claude/RayLib/raylib-6.0
    ifneq ($(wildcard $(WSL_RAYLIB_DIR)/src/raylib.h),)
        # WSL detectado: usar raylib desde Windows
        RAYLIB_DIR := $(WSL_RAYLIB_DIR)
        CFLAGS := -Wall -std=c99 -O2 -I$(RAYLIB_DIR)/src
        LDFLAGS := -L$(RAYLIB_DIR)/src -lraylib -lGL -lm -lpthread -ldl -lrt -lX11
        $(info Detected WSL, using raylib from: $(RAYLIB_DIR))
    else
        # Linux nativo
        CFLAGS := -Wall -std=c99 -O2
        LDFLAGS := -lraylib -lGL -lm -lpthread -ldl -lrt -lX11
    endif
    TARGET := $(BUILD_DIR)/$(PROJECT_NAME)
endif

# macOS
ifeq ($(PLATFORM_OS),OSX)
    CC := clang
    CFLAGS := -Wall -std=c99 -O2
    LDFLAGS := -lraylib -framework OpenGL -framework Cocoa -framework IOKit -framework CoreVideo
    TARGET := $(BUILD_DIR)/$(PROJECT_NAME)
endif

# === COMPILACIÓN WEB ===

# Emscripten
EMCC := emcc
EMFLAGS := -Wall -std=gnu99 -O2 -I. -I../raylib-6.0/src --post-js poker_api_post.js
EM_LDFLAGS := -L. -L../raylib-6.0/src \
    -s USE_GLFW=3 \
    -s ASYNCIFY \
    -s TOTAL_MEMORY=67108864 \
    -s FORCE_FILESYSTEM=1 \
    -s EXPORTED_RUNTIME_METHODS=ccall \
    --shell-file minshell.html \
    --preload-file assets@/assets \
    --preload-file fonts@/fonts \
    -DPLATFORM_WEB \
    ../raylib-6.0/src/libraylib.web.a
WEB_TARGET := $(WEB_DIR)/index.html

# === REGLAS ===

.PHONY: all desktop web clean run run-web audio

all: desktop

audio:
	python assets/audio/generate_sounds.py

desktop: $(TARGET)

$(TARGET): $(SOURCES) | $(BUILD_DIR)
	$(CC) $(SOURCES) -o $@ $(CFLAGS) $(LDFLAGS)
	@echo "Compilado para desktop: $@"

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

web: $(WEB_TARGET)

$(WEB_TARGET): $(SOURCES) minshell.html | $(WEB_DIR)
	$(EMCC) $(SOURCES) -o $@ $(EMFLAGS) $(EM_LDFLAGS)
	@echo "Compilado para web: $@"

$(WEB_DIR):
	mkdir -p $(WEB_DIR)

run: desktop
	./$(TARGET)

run-web: web
	cd $(WEB_DIR) && python3 -m http.server 8080

clean:
	rm -rf $(BUILD_DIR) $(WEB_DIR)
	@echo "Build limpiado"

# === RAYLIB PARA LINUX/WSL ===

# Compilar raylib para Linux/WSL (ejecutar una vez)
build-raylib-linux:
ifeq ($(PLATFORM_OS),LINUX)
ifeq ($(WSL),1)
	cd $(RAYLIB_DIR)/src && make PLATFORM=PLATFORM_DESKTOP -B
else
	@echo "En Linux nativo, instala raylib con: sudo apt install libraylib-dev"
endif
endif
	@echo "Raylib compilado para Linux"

# === RAYLIB PARA WEB ===

# Compilar raylib para web (ejecutar una vez)
build-raylib-web:
	cd ../raylib-6.0/src && make PLATFORM=PLATFORM_WEB -B OUTPUT_NAME=raylib.web
	@echo "Raylib compilado para web"
