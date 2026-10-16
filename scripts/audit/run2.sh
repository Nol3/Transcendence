#!/bin/bash
set -e
T=/mnt/c/Users/aleja/Desktop/github/Transcendence/juego
W=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/poker_audit
cd "$W"
echo "########## TEST 2: verificacion completa tras el arreglo ##########"
gcc -O2 -std=c99 -Wall -I"$T/src" -I"$T/raylib-6.0/src" test_eval2.c "$T/src/poker_hand.c" "$T/src/lang.c" -o test_eval2
./test_eval2
