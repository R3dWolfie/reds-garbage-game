# sprite_loader.py
import pygame
import os

ASSET_DIR = "assets"

_cache = {}


def load_sprite(filename, size=None, fallback_color=None, fallback_size=(40, 40)):
    """
    Try to load an image from assets/.
    If it doesn't exist, create a colored rectangle as fallback.
    Results are cached.
    """
    key = (filename, size, fallback_color, fallback_size)
    if key in _cache:
        return _cache[key].copy()

    path = os.path.join(ASSET_DIR, filename)

    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.scale(img, size)
            _cache[key] = img
            return img.copy()
        except pygame.error:
            pass

    # Fallback: colored rectangle
    s = size if size else fallback_size
    img = pygame.Surface(s, pygame.SRCALPHA)
    color = fallback_color if fallback_color else (255, 0, 255)
    img.fill(color)
    _cache[key] = img
    return img.copy()


def load_sprite_sheet(filename, frame_width, frame_height, num_frames, scale=None):
    """
    Load a horizontal sprite sheet and return a list of frames.
    Falls back to a list of colored rectangles.
    """
    path = os.path.join(ASSET_DIR, filename)
    frames = []

    if os.path.exists(path):
        try:
            sheet = pygame.image.load(path).convert_alpha()
            for i in range(num_frames):
                frame = sheet.subsurface(pygame.Rect(i * frame_width, 0, frame_width, frame_height))
                if scale:
                    frame = pygame.transform.scale(frame, scale)
                frames.append(frame)
            return frames
        except pygame.error:
            pass

    # Fallback
    s = scale if scale else (frame_width, frame_height)
    for i in range(num_frames):
        img = pygame.Surface(s, pygame.SRCALPHA)
        brightness = 150 + int(105 * (i / max(1, num_frames - 1)))
        img.fill((brightness, 0, brightness))
        frames.append(img)

    return frames
