# vfx.py
"""Visual effects: particles, death bursts, zap lightning, hit sparks, shockwaves.
Performance-optimized: no per-frame Surface allocation, cached fonts, O(n) list ops."""

import pygame
import math
import random

# ═══════════════════ PARTICLE SYSTEM ═══════════════════

_particles = []
_flashes = []
_zap_bolts = []
_damage_nums = []
_shockwaves = []
_screen_flashes = []
_ambient = []
_trails = []

# Pre-cached resources
_dmg_fonts = {}  # {size: font}
_screen_overlay = None  # Reusable overlay surface

MAX_PARTICLES = 300
MAX_TRAILS = 80
MAX_DAMAGE_NUMS = 30


def _get_dmg_font(size):
    if size not in _dmg_fonts:
        _dmg_fonts[size] = pygame.font.SysFont("Arial", size, bold=True)
    return _dmg_fonts[size]


def tick_and_draw(surf):
    _draw_ambient(surf)
    _draw_trails(surf)
    _draw_particles(surf)
    _draw_shockwaves(surf)
    _draw_flashes(surf)
    _draw_zap_bolts(surf)
    _draw_damage_nums(surf)
    _draw_screen_flashes(surf)


def clear():
    _particles.clear(); _flashes.clear(); _zap_bolts.clear()
    _damage_nums.clear(); _shockwaves.clear(); _screen_flashes.clear()
    _trails.clear(); _ambient.clear()


# ═══════════════════ AMBIENT ═══════════════════

def spawn_ambient(sw, sh, count=3):
    while len(_ambient) < 40:
        _ambient.append({
            "x": random.randint(0, sw), "y": random.randint(0, sh),
            "dx": random.uniform(-0.3, 0.3), "dy": random.uniform(-0.5, -0.1),
            "life": random.randint(60, 180), "max_life": 180,
            "size": random.uniform(1, 2.5),
            "color": random.choice([(50,80,120),(40,60,100),(60,40,90),(30,70,80),(80,50,70)]),
        })


# ═══════════════════ EFFECTS ═══════════════════

def enemy_death_burst(x, y, color=(255, 80, 80), count=12, speed=5.0, size=5):
    # Cap particles
    count = min(count, 12)
    for i in range(count):
        angle = (i / count) * math.pi * 2 + random.uniform(-0.2, 0.2)
        spd = random.uniform(speed * 0.3, speed)
        life = random.randint(12, 28)
        c = (min(255, color[0]+random.randint(-30,60)),
             min(255, color[1]+random.randint(-30,60)),
             min(255, color[2]+random.randint(-30,60)))
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": c, "life": life, "max_life": life,
            "size": random.uniform(size*0.5, size*1.3), "type": "death"})
    _flashes.append({"x": x, "y": y, "radius": 20+count, "color": color, "life": 8})
    if len(_particles) > MAX_PARTICLES:
        del _particles[:len(_particles) - MAX_PARTICLES]


def boss_death_burst(x, y, color=(255, 50, 50)):
    for i in range(30):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 10)
        life = random.randint(15, 40)
        c = random.choice([color, (255,255,random.randint(50,200)),
            (255,random.randint(100,200),50)])
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": c, "life": life, "max_life": life,
            "size": random.uniform(3,7), "type": "spark" if i%3==0 else "death"})
    _shockwaves.append({"x": x, "y": y, "radius": 5, "max_radius": 120,
        "color": color, "life": 18, "max_life": 18, "width": 3})
    _flashes.append({"x": x, "y": y, "radius": 80, "color": (255,220,150), "life": 14})
    _screen_flashes.append({"color": (255,200,100), "life": 10, "max_life": 10, "intensity": 0.15})
    if len(_particles) > MAX_PARTICLES:
        del _particles[:len(_particles) - MAX_PARTICLES]


def hit_spark(x, y, color=(255, 255, 200), count=4):
    for _ in range(count):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 5)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": color, "life": 8, "max_life": 8, "size": random.uniform(1.5, 3), "type": "spark"})


def beam_hit(x, y, color=(255, 100, 100)):
    for _ in range(2):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(1, 3)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": (255,random.randint(150,255),random.randint(100,200)),
            "life": 6, "max_life": 6, "size": random.uniform(1,2.5), "type": "spark"})


def bullet_trail(x, y, color=(255, 255, 200), size=2):
    if len(_trails) < MAX_TRAILS:
        _trails.append({"x": x, "y": y, "color": color, "life": 6, "max_life": 6, "size": size})


def gem_sparkle(x, y):
    for _ in range(3):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(1, 3)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd-1.5,
            "color": random.choice([(0,255,255),(100,255,200)]),
            "life": 12, "max_life": 12, "size": random.uniform(1.5,2.5), "type": "sparkle"})


def gold_sparkle(x, y):
    for _ in range(4):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(1.5, 3)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd-1,
            "color": (255,random.randint(180,230),random.randint(0,80)),
            "life": 12, "max_life": 12, "size": random.uniform(1.5,2.5), "type": "sparkle"})


def player_hit_burst(x, y):
    for _ in range(8):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 5)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": (255,random.randint(20,80),random.randint(20,50)),
            "life": 14, "max_life": 14, "size": random.uniform(2,4), "type": "death"})
    _screen_flashes.append({"color": (255,0,0), "life": 5, "max_life": 5, "intensity": 0.06})


def dash_zap(start, end, color=(100, 200, 255)):
    dx = end[0]-start[0]; dy = end[1]-start[1]
    dist = math.hypot(dx, dy)
    if dist < 5: return
    # Main bolt + 1 branch (was 3+4)
    for bolt in range(2):
        segments = max(3, int(dist/16))
        points = [start]
        jitter = 15 if bolt == 0 else 22
        for i in range(1, segments):
            t = i/segments
            bx = start[0]+dx*t+random.randint(-jitter,jitter)
            by = start[1]+dy*t+random.randint(-jitter,jitter)
            points.append((bx, by))
        points.append(end)
        _zap_bolts.append({"points": points, "color": color if bolt==0 else (180,230,255),
            "life": 10-bolt*3, "width": 3-bolt})
    # Fewer sparks
    for _ in range(6):
        bx = start[0]+dx*random.uniform(0.2,0.8)+random.randint(-10,10)
        by = start[1]+dy*random.uniform(0.2,0.8)+random.randint(-10,10)
        _particles.append({"x": bx, "y": by, "dx": random.uniform(-3,3), "dy": random.uniform(-3,3),
            "color": (150,220,255), "life": 10, "max_life": 10, "size": random.uniform(2,4), "type": "spark"})
    _flashes.append({"x": end[0], "y": end[1], "radius": 30, "color": (200,240,255), "life": 8})
    _screen_flashes.append({"color": (180,220,255), "life": 3, "max_life": 3, "intensity": 0.04})


def level_up_burst(x, y):
    for i in range(16):
        angle = (i/16)*math.pi*2
        spd = random.uniform(2, 5)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": (255,215+random.randint(-20,40),random.randint(0,80)),
            "life": 24, "max_life": 24, "size": random.uniform(2.5,4.5), "type": "sparkle"})
    _shockwaves.append({"x": x, "y": y, "radius": 5, "max_radius": 55,
        "color": (255,215,0), "life": 12, "max_life": 12, "width": 3})
    _flashes.append({"x": x, "y": y, "radius": 45, "color": (255,215,0), "life": 10})
    _screen_flashes.append({"color": (255,230,100), "life": 4, "max_life": 4, "intensity": 0.04})


def wave_start_effect(sw, sh):
    cx, cy = sw//2, sh//2
    _shockwaves.append({"x": cx, "y": cy, "radius": 10, "max_radius": max(sw,sh)//2,
        "color": (0,255,255), "life": 20, "max_life": 20, "width": 2})
    _screen_flashes.append({"color": (0,200,255), "life": 4, "max_life": 4, "intensity": 0.03})


def companion_zap(x, y, color=(0, 255, 255)):
    """Small electric zap for roomba/saw companion hits. Lightweight."""
    # 3-4 short radiating lines as spark particles
    for _ in range(random.randint(3, 4)):
        angle = random.uniform(0, math.pi * 2)
        length = random.uniform(4, 8)
        _particles.append({
            "x": x, "y": y,
            "dx": math.cos(angle) * length * 0.4,
            "dy": math.sin(angle) * length * 0.4,
            "color": color, "life": random.randint(5, 7), "max_life": 7,
            "size": random.uniform(1.5, 2.5), "type": "spark",
        })
    # Tiny bright center spark
    _particles.append({
        "x": x, "y": y, "dx": 0, "dy": 0,
        "color": (220, 255, 255), "life": 5, "max_life": 5,
        "size": 2.5, "type": "sparkle",
    })


def damage_number(x, y, amount, is_crit=False):
    if len(_damage_nums) >= MAX_DAMAGE_NUMS:
        return  # Drop if too many
    color = (255,255,50) if is_crit else (255,100,80)
    text = f"{amount}" if not is_crit else f"{amount}!"
    _damage_nums.append({"x": x+random.randint(-8,8), "y": y-10, "text": text,
        "color": color, "life": 35, "dy": -1.8 if is_crit else -1.3, "size": 20 if is_crit else 14})


# ═══════════════════ RENDERERS (optimized) ═══════════════════

def _draw_ambient(surf):
    alive = []
    for p in _ambient:
        p["x"] += p["dx"]; p["y"] += p["dy"]; p["life"] -= 1
        if p["life"] <= 0 or p["y"] < -10:
            continue
        sz = max(1, int(p["size"]))
        c = p["color"]
        # Direct draw, no alpha surface needed for tiny ambient dots
        pygame.draw.circle(surf, c, (int(p["x"]), int(p["y"])), sz)
        alive.append(p)
    _ambient.clear()
    _ambient.extend(alive)


def _draw_trails(surf):
    alive = []
    for t in _trails:
        t["life"] -= 1
        if t["life"] <= 0:
            continue
        sz = max(1, int(t["size"] * t["life"] / t["max_life"]))
        pygame.draw.circle(surf, t["color"], (int(t["x"]), int(t["y"])), sz)
        alive.append(t)
    _trails.clear()
    _trails.extend(alive)


def _draw_particles(surf):
    alive = []
    for p in _particles:
        p["x"] += p["dx"]; p["y"] += p["dy"]; p["life"] -= 1
        p["dx"] *= 0.91; p["dy"] *= 0.91
        if p["type"] == "death": p["dy"] += 0.18
        if p["life"] <= 0:
            continue
        ratio = p["life"] / p["max_life"]
        sz = max(1, int(p["size"] * ratio))
        c = p["color"]
        px, py = int(p["x"]), int(p["y"])

        if p["type"] == "spark":
            # Diamond shape — just draw directly
            pts = [(px, py-sz), (px+sz, py), (px, py+sz), (px-sz, py)]
            pygame.draw.polygon(surf, c, pts)
        elif p["type"] == "sparkle":
            # Cross
            w = max(1, sz//2)
            pygame.draw.line(surf, c, (px, py-sz), (px, py+sz), w)
            pygame.draw.line(surf, c, (px-sz, py), (px+sz, py), w)
        else:
            # Circle
            pygame.draw.circle(surf, c, (px, py), sz)
            if sz > 2:
                bc = (min(255,c[0]+80), min(255,c[1]+80), min(255,c[2]+80))
                pygame.draw.circle(surf, bc, (px, py), max(1, sz//2))
        alive.append(p)
    _particles.clear()
    _particles.extend(alive)


def _draw_shockwaves(surf):
    alive = []
    for s in _shockwaves:
        s["life"] -= 1
        if s["life"] <= 0:
            continue
        ratio = s["life"] / s["max_life"]
        progress = 1.0 - ratio
        r = int(s["radius"] + (s["max_radius"] - s["radius"]) * progress)
        c = s["color"]
        w = max(1, int(s["width"] * ratio))
        # Direct circle draw on surf — no SRCALPHA surface
        if r > 1:
            pygame.draw.circle(surf, c, (int(s["x"]), int(s["y"])), r, w)
        alive.append(s)
    _shockwaves.clear()
    _shockwaves.extend(alive)


def _draw_flashes(surf):
    alive = []
    for f in _flashes:
        f["life"] -= 1
        if f["life"] <= 0:
            continue
        ratio = f["life"] / max(1, f["life"] + 4)
        r = int(f["radius"] * (1 + (1-ratio)*0.3))
        c = f["color"]
        # Simple circle, no alpha surface
        if r > 0:
            pygame.draw.circle(surf, c, (int(f["x"]), int(f["y"])), r)
        alive.append(f)
    _flashes.clear()
    _flashes.extend(alive)


def _draw_zap_bolts(surf):
    alive = []
    for z in _zap_bolts:
        z["life"] -= 1
        if z["life"] <= 0:
            continue
        c = z["color"]
        w = max(1, int(z["width"] * z["life"] / 10))
        pts = z["points"]
        # Draw directly on surf — no full-screen SRCALPHA surface
        for i in range(len(pts)-1):
            pygame.draw.line(surf, c, pts[i], pts[i+1], w+2)
        # Bright core
        for i in range(len(pts)-1):
            pygame.draw.line(surf, (255,255,255), pts[i], pts[i+1], max(1, w))
        alive.append(z)
    _zap_bolts.clear()
    _zap_bolts.extend(alive)


def _draw_screen_flashes(surf):
    global _screen_overlay
    alive = []
    for f in _screen_flashes:
        f["life"] -= 1
        if f["life"] <= 0:
            continue
        ratio = f["life"] / f["max_life"]
        alpha = int(255 * f["intensity"] * ratio)
        if alpha > 0:
            sw, sh = surf.get_size()
            # Reuse overlay surface
            if _screen_overlay is None or _screen_overlay.get_size() != (sw, sh):
                _screen_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            _screen_overlay.fill((*f["color"], alpha))
            surf.blit(_screen_overlay, (0, 0))
        alive.append(f)
    _screen_flashes.clear()
    _screen_flashes.extend(alive)


def _draw_damage_nums(surf):
    alive = []
    for d in _damage_nums:
        d["life"] -= 1; d["y"] += d["dy"]; d["dy"] *= 0.96
        if d["life"] <= 0:
            continue
        # Cached font lookup
        fnt = _get_dmg_font(d["size"])
        ts = fnt.render(d["text"], True, d["color"])
        # Shadow
        ss = fnt.render(d["text"], True, (0, 0, 0))
        surf.blit(ss, (int(d["x"]) - ts.get_width()//2 + 1, int(d["y"]) + 1))
        surf.blit(ts, (int(d["x"]) - ts.get_width()//2, int(d["y"])))
        alive.append(d)
    _damage_nums.clear()
    _damage_nums.extend(alive)