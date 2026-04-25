#!/usr/bin/env python3
import struct
import math
import os

SAMPLE_RATE = 44100
OUTPUT_DIR = "assets/audio"

def write_wav_header(f, num_samples, channels, sample_width, sample_rate):
    f.write(b'RIFF')
    data_size = num_samples * channels * sample_width
    f.write(struct.pack('<I', 36 + data_size))
    f.write(b'WAVE')
    f.write(b'fmt ')
    f.write(struct.pack('<I', 16))
    f.write(struct.pack('<H', 1))
    f.write(struct.pack('<H', channels))
    f.write(struct.pack('<I', sample_rate))
    f.write(struct.pack('<I', sample_rate * channels * sample_width))
    f.write(struct.pack('<H', channels * sample_width))
    f.write(struct.pack('<H', sample_width * 8))

def write_wav_data(f, samples, channels, sample_width):
    f.write(b'data')
    data_size = len(samples) * channels * sample_width
    f.write(struct.pack('<I', data_size))
    for s in samples:
        s = max(-1.0, min(1.0, s))
        if sample_width == 1:
            f.write(struct.pack('B', int((s + 1.0) * 127.5)))
        else:
            f.write(struct.pack('<h', int(s * 32767)))

def generate_sine(duration, frequency, volume=0.5, attack=0.01, release=0.05):
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = 1.0
        if t < attack:
            env = t / attack
        elif t > duration - release:
            env = (duration - t) / release
        samples.append(math.sin(2.0 * math.pi * frequency * t) * volume * env)
    return samples

def generate_noise(duration, volume=0.3):
    import random
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    decay = 1.0
    for i in range(num_samples):
        decay = max(0, 1.0 - (i / num_samples) * 0.5)
        samples.append((random.random() * 2.0 - 1.0) * volume * decay)
    return samples

def generate_chirp(duration, f_start, f_end, volume=0.4):
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        f = f_start + (f_end - f_start) * (t / duration)
        samples.append(math.sin(2.0 * math.pi * f * t) * volume)
    return samples

def generate_square(duration, frequency, volume=0.3):
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        val = 1.0 if (int(frequency * t) % 2) == 0 else -1.0
        samples.append(val * volume)
    return samples

def save_wav(filename, samples, channels=1, sample_width=2):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'wb') as f:
        write_wav_header(f, len(samples), channels, sample_width, SAMPLE_RATE)
        write_wav_data(f, samples, channels, sample_width)
    print(f"  Created: {path}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generando archivos de audio WAV...")

    save_wav("card_flip.wav",      generate_sine(0.15, 600, 0.4) + generate_sine(0.10, 900, 0.3))
    save_wav("card_select.wav",    generate_sine(0.05, 800, 0.3) + generate_sine(0.03, 1200, 0.2))
    save_wav("card_deal.wav",      generate_chirp(0.20, 200, 800, 0.4) + generate_noise(0.10, 0.2))
    save_wav("button_click.wav",   generate_sine(0.03, 600, 0.4) + generate_sine(0.02, 400, 0.3))
    save_wav("win_round.wav",     [s * 0.5 for s in generate_sine(0.10, 523, 0.5)] +
                                   [s * 0.5 for s in generate_sine(0.10, 659, 0.5)] +
                                   [s * 0.5 for s in generate_sine(0.15, 784, 0.5)])
    save_wav("win_game.wav",      [s * 0.4 for s in generate_sine(0.08, 523, 0.5)] +
                                   [s * 0.4 for s in generate_sine(0.08, 659, 0.5)] +
                                   [s * 0.4 for s in generate_sine(0.08, 784, 0.5)] +
                                   [s * 0.4 for s in generate_sine(0.08, 1047, 0.5)] +
                                   [s * 0.5 for s in generate_sine(0.25, 1047, 0.6)])
    save_wav("discard.wav",       generate_sine(0.10, 400, 0.4) + generate_noise(0.08, 0.2))
    save_wav("error.wav",         generate_square(0.10, 200, 0.3) + generate_square(0.10, 150, 0.3))

    print(f"\n{8} archivos de audio creados en {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()