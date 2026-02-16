# sound_manager.py
# Procedurally generated sound effects — no external audio files needed.
# All sounds are synthesised from numpy arrays and loaded into pygame.

import pygame
import numpy as np

SAMPLE_RATE = 44100


def _make_sound(samples):
    """Convert a float32 numpy array (-1..1) into a pygame Sound."""
    arr = np.clip(samples, -1.0, 1.0)
    arr = (arr * 32767).astype(np.int16)
    # Stereo: duplicate the channel
    stereo = np.column_stack([arr, arr])
    return pygame.sndarray.make_sound(stereo)


def _envelope(length, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    """Simple ADSR envelope."""
    n = int(SAMPLE_RATE * length)
    env = np.ones(n)
    a = int(SAMPLE_RATE * attack)
    d = int(SAMPLE_RATE * decay)
    r = int(SAMPLE_RATE * release)
    s_start = a + d
    s_end = n - r
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0 and a + d <= n:
        env[a:a+d] = np.linspace(1, sustain, d)
    if s_end > s_start:
        env[s_start:s_end] = sustain
    if r > 0:
        env[s_end:] = np.linspace(sustain, 0, n - s_end)
    return env


def _sine(freq, length):
    t = np.linspace(0, length, int(SAMPLE_RATE * length), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def _noise(length):
    return np.random.uniform(-1, 1, int(SAMPLE_RATE * length)).astype(np.float32)


def _generate_shoot():
    """Short snappy pop."""
    length = 0.08
    t = np.linspace(0, length, int(SAMPLE_RATE * length), endpoint=False)
    freq = np.linspace(800, 300, len(t))
    wave = np.sin(2 * np.pi * freq * t / SAMPLE_RATE * SAMPLE_RATE)
    env = _envelope(length, attack=0.002, decay=0.05, sustain=0.0, release=0.03)
    return (wave * env * 0.4).astype(np.float32)


def _generate_hit():
    """Thud/impact."""
    length = 0.12
    noise = _noise(length) * 0.6
    tone = _sine(120, length) * 0.4
    wave = noise + tone
    env = _envelope(length, attack=0.002, decay=0.08, sustain=0.1, release=0.04)
    return (wave * env * 0.5).astype(np.float32)


def _generate_player_hurt():
    """Player takes damage — low thud + distortion."""
    length = 0.2
    noise = _noise(length) * 0.5
    tone = _sine(80, length) * 0.5
    wave = noise + tone
    env = _envelope(length, attack=0.005, decay=0.1, sustain=0.2, release=0.09)
    return (wave * env * 0.7).astype(np.float32)


def _generate_level_up():
    """Ascending arpeggio."""
    notes = [523, 659, 784, 1047]  # C5 E5 G5 C6
    chunks = []
    for freq in notes:
        length = 0.1
        wave = _sine(freq, length)
        env = _envelope(length, attack=0.01, decay=0.04, sustain=0.5, release=0.05)
        chunks.append((wave * env * 0.5).astype(np.float32))
    return np.concatenate(chunks)


def _generate_wave_start():
    """Rising sweep."""
    length = 0.4
    t = np.linspace(0, length, int(SAMPLE_RATE * length), endpoint=False)
    freq = np.linspace(200, 600, len(t))
    wave = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
    env = _envelope(length, attack=0.05, decay=0.1, sustain=0.6, release=0.2)
    return (wave * env * 0.4).astype(np.float32)


def _generate_death():
    """Descending sad tone."""
    length = 0.6
    t = np.linspace(0, length, int(SAMPLE_RATE * length), endpoint=False)
    freq = np.linspace(400, 100, len(t))
    wave = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
    noise = _noise(length) * 0.15
    env = _envelope(length, attack=0.01, decay=0.2, sustain=0.3, release=0.3)
    return ((wave + noise) * env * 0.5).astype(np.float32)


def _generate_gem_pickup():
    """Tiny bright blip."""
    length = 0.06
    wave = _sine(1200, length) + _sine(1500, length) * 0.5
    env = _envelope(length, attack=0.002, decay=0.03, sustain=0.0, release=0.03)
    return (wave * env * 0.3).astype(np.float32)


def _generate_dash():
    """Whoosh."""
    length = 0.15
    noise = _noise(length)
    t = np.linspace(0, length, int(SAMPLE_RATE * length), endpoint=False)
    freq = np.linspace(600, 200, len(t))
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * 0.3
    wave = noise * 0.5 + tone
    env = _envelope(length, attack=0.01, decay=0.08, sustain=0.1, release=0.06)
    return (wave * env * 0.5).astype(np.float32)


def _generate_boss_spawn():
    """Ominous low boom."""
    length = 0.8
    tone1 = _sine(60, length) * 0.5
    tone2 = _sine(90, length) * 0.3
    noise = _noise(length) * 0.2
    wave = tone1 + tone2 + noise
    env = _envelope(length, attack=0.02, decay=0.3, sustain=0.4, release=0.3)
    return (wave * env * 0.6).astype(np.float32)


class SoundManager:
    def __init__(self, config):
        self.config = config
        self.sounds = {}
        self._build_sounds()

    def _build_sounds(self):
        generators = {
            "shoot":        _generate_shoot,
            "hit":          _generate_hit,
            "player_hurt":  _generate_player_hurt,
            "level_up":     _generate_level_up,
            "wave_start":   _generate_wave_start,
            "death":        _generate_death,
            "gem_pickup":   _generate_gem_pickup,
            "dash":         _generate_dash,
            "boss_spawn":   _generate_boss_spawn,
        }
        for name, fn in generators.items():
            try:
                self.sounds[name] = _make_sound(fn())
            except Exception as e:
                print(f"[SoundManager] Failed to generate '{name}': {e}")

    def _sfx_volume(self):
        master = self.config.get("master_volume", 1.0)
        sfx    = self.config.get("sfx_volume", 1.0)
        return master * sfx

    def play(self, name, volume=1.0):
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(self._sfx_volume() * volume)
            snd.play()

    def play_shoot(self):   self.play("shoot",       0.35)
    def play_hit(self):     self.play("hit",          0.5)
    def play_hurt(self):    self.play("player_hurt",  0.8)
    def play_level_up(self):self.play("level_up",     0.9)
    def play_wave_start(self): self.play("wave_start",0.7)
    def play_death(self):   self.play("death",        1.0)
    def play_gem(self):     self.play("gem_pickup",   0.4)
    def play_dash(self):    self.play("dash",         0.6)
    def play_boss_spawn(self): self.play("boss_spawn",1.0)