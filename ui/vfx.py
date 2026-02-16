# vfx.py
"""Visual effects: particles, death bursts, zap lightning, hit sparks, shockwaves."""

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
    _trails.clear()


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

def enemy_death_burst(x, y, color=(255, 80, 80), count=16, speed=5.0, size=5):
    for i in range(count):
        angle = (i / count) * math.pi * 2 + random.uniform(-0.2, 0.2)
        spd = random.uniform(speed * 0.3, speed)
        life = random.randint(15, 35)
        c = (min(255, color[0]+random.randint(-30,60)),
             min(255, color[1]+random.randint(-30,60)),
             min(255, color[2]+random.randint(-30,60)))
        _particles.append({"x": x+random.randint(-4,4), "y": y+random.randint(-4,4),
            "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": c, "life": life, "max_life": life,
            "size": random.uniform(size*0.5, size*1.3), "type": "death"})
    _flashes.append({"x": x, "y": y, "radius": 25+count,
        "color": (min(255,color[0]+80),min(255,color[1]+80),min(255,color[2]+80)), "life": 10})
    _shockwaves.append({"x": x, "y": y, "radius": 5, "max_radius": 35+count*2,
        "color": color, "life": 12, "max_life": 12, "width": 2})
    _screen_flashes.append({"color": color, "life": 3, "max_life": 3, "intensity": 0.03})


def boss_death_burst(x, y, color=(255, 50, 50)):
    for i in range(60):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 10)
        life = random.randint(20, 55)
        c = random.choice([color, (255,255,random.randint(50,200)),
            (255,random.randint(100,200),50), (255,200,200)])
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": c, "life": life, "max_life": life,
            "size": random.uniform(3,8), "type": "spark" if i%3==0 else "death"})
    for i in range(3):
        _shockwaves.append({"x": x, "y": y, "radius": 5+i*10, "max_radius": 120+i*40,
            "color": (255,min(255,150+i*50),50+i*30), "life": 20+i*5, "max_life": 20+i*5, "width": 4-i})
    _flashes.append({"x": x, "y": y, "radius": 100, "color": (255,220,150), "life": 18})
    _screen_flashes.append({"color": (255,200,100), "life": 12, "max_life": 12, "intensity": 0.2})


def hit_spark(x, y, color=(255, 255, 200), count=6):
    for _ in range(count):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 5)
        life = random.randint(6, 16)
        _particles.append({"x": x+random.randint(-3,3), "y": y+random.randint(-3,3),
            "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": color, "life": life, "max_life": life,
            "size": random.uniform(1.5, 3.5), "type": "spark"})
    _flashes.append({"x": x, "y": y, "radius": 8, "color": color, "life": 4})


def beam_hit(x, y, color=(255, 100, 100)):
    for _ in range(3):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(1, 3)
        _particles.append({"x": x+random.randint(-6,6), "y": y+random.randint(-6,6),
            "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": (255,random.randint(150,255),random.randint(100,200)),
            "life": 8, "max_life": 8, "size": random.uniform(1,3), "type": "spark"})


def bullet_trail(x, y, color=(255, 255, 200), size=2):
    _trails.append({"x": x+random.uniform(-2,2), "y": y+random.uniform(-2,2),
        "color": color, "life": 8, "max_life": 8, "size": size})


def gem_sparkle(x, y):
    for _ in range(5):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(1, 3)
        life = random.randint(8, 18)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd-1.5,
            "color": random.choice([(0,255,255),(100,255,200),(50,200,255)]),
            "life": life, "max_life": life, "size": random.uniform(1.5,3), "type": "sparkle"})


def gold_sparkle(x, y):
    for _ in range(6):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(1.5, 3.5)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd-1,
            "color": (255,random.randint(180,230),random.randint(0,80)),
            "life": 14, "max_life": 14, "size": random.uniform(1.5,3), "type": "sparkle"})


def player_hit_burst(x, y):
    for _ in range(10):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 6)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": (255,random.randint(20,80),random.randint(20,50)),
            "life": 18, "max_life": 18, "size": random.uniform(2,5), "type": "death"})
    _screen_flashes.append({"color": (255,0,0), "life": 6, "max_life": 6, "intensity": 0.08})


def dash_zap(start, end, color=(100, 200, 255)):
    dx = end[0]-start[0]; dy = end[1]-start[1]
    dist = math.hypot(dx, dy)
    if dist < 5: return
    for bolt in range(3):
        segments = max(4, int(dist/12))
        points = [start]
        jitter = 18 if bolt == 0 else 25
        for i in range(1, segments):
            t = i/segments
            bx = start[0]+dx*t+random.randint(-jitter,jitter)
            by = start[1]+dy*t+random.randint(-jitter,jitter)
            points.append((bx, by))
        points.append(end)
        _zap_bolts.append({"points": points, "color": color if bolt==0 else (180,230,255),
            "life": 14-bolt*3, "width": 4-bolt})
    for _ in range(4):
        bx = start[0]+dx*random.uniform(0.2,0.8)+random.randint(-15,15)
        by = start[1]+dy*random.uniform(0.2,0.8)+random.randint(-15,15)
        be = (bx+random.randint(-40,40), by+random.randint(-40,40))
        bpts = [(bx,by)]
        for j in range(3):
            t2 = (j+1)/4
            bpts.append((bx+(be[0]-bx)*t2+random.randint(-10,10), by+(be[1]-by)*t2+random.randint(-10,10)))
        bpts.append(be)
        _zap_bolts.append({"points": bpts, "color": (150,220,255), "life": 8, "width": 1})
    for pos in [start, end]:
        for _ in range(10):
            angle = random.uniform(0, math.pi*2)
            spd = random.uniform(2, 7)
            _particles.append({"x": pos[0], "y": pos[1], "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
                "color": random.choice([(150,220,255),(200,240,255),(100,180,255)]),
                "life": 14, "max_life": 14, "size": random.uniform(2,5), "type": "spark"})
    _flashes.append({"x": start[0], "y": start[1], "radius": 25, "color": color, "life": 8})
    _flashes.append({"x": end[0], "y": end[1], "radius": 35, "color": (200,240,255), "life": 12})
    _shockwaves.append({"x": end[0], "y": end[1], "radius": 5, "max_radius": 50,
        "color": color, "life": 10, "max_life": 10, "width": 2})
    _screen_flashes.append({"color": (180,220,255), "life": 4, "max_life": 4, "intensity": 0.06})
    steps = max(4, int(dist/20))
    for i in range(steps):
        t = i/steps
        _particles.append({"x": start[0]+dx*t+random.randint(-5,5), "y": start[1]+dy*t+random.randint(-5,5),
            "dx": random.uniform(-1,1), "dy": random.uniform(-2,0),
            "color": (200,240,255), "life": 20, "max_life": 20, "size": random.uniform(1.5,3), "type": "sparkle"})


def level_up_burst(x, y):
    for i in range(24):
        angle = (i/24)*math.pi*2
        spd = random.uniform(2, 6)
        _particles.append({"x": x, "y": y, "dx": math.cos(angle)*spd, "dy": math.sin(angle)*spd,
            "color": (255,215+random.randint(-20,40),random.randint(0,80)),
            "life": 30, "max_life": 30, "size": random.uniform(2.5,5), "type": "sparkle"})
    _shockwaves.append({"x": x, "y": y, "radius": 5, "max_radius": 60,
        "color": (255,215,0), "life": 14, "max_life": 14, "width": 3})
    _flashes.append({"x": x, "y": y, "radius": 55, "color": (255,215,0), "life": 14})
    _screen_flashes.append({"color": (255,230,100), "life": 5, "max_life": 5, "intensity": 0.05})


def wave_start_effect(sw, sh):
    cx, cy = sw//2, sh//2
    _shockwaves.append({"x": cx, "y": cy, "radius": 10, "max_radius": max(sw,sh),
        "color": (0,255,255), "life": 30, "max_life": 30, "width": 2})
    _screen_flashes.append({"color": (0,200,255), "life": 6, "max_life": 6, "intensity": 0.04})


def damage_number(x, y, amount, is_crit=False):
    color = (255,255,50) if is_crit else (255,100,80)
    text = f"{amount}" if not is_crit else f"{amount}!"
    _damage_nums.append({"x": x+random.randint(-10,10), "y": y-10, "text": text,
        "color": color, "life": 45, "dy": -2.0 if is_crit else -1.5, "size": 22 if is_crit else 14})


# ═══════════════════ RENDERERS ═══════════════════

def _draw_ambient(surf):
    for p in _ambient[:]:
        p["x"] += p["dx"]; p["y"] += p["dy"]; p["life"] -= 1
        if p["life"] <= 0 or p["y"] < -10:
            _ambient.remove(p); continue
        ratio = min(1.0, p["life"]/60)
        alpha = int(40*ratio); sz = int(p["size"])
        ps = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*p["color"], alpha), (sz+1, sz+1), sz)
        surf.blit(ps, (int(p["x"])-sz-1, int(p["y"])-sz-1))


def _draw_trails(surf):
    for t in _trails[:]:
        t["life"] -= 1
        if t["life"] <= 0: _trails.remove(t); continue
        ratio = t["life"]/t["max_life"]
        alpha = int(80*ratio); sz = max(1, int(t["size"]*ratio))
        ps = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*t["color"], alpha), (sz+1, sz+1), sz)
        surf.blit(ps, (int(t["x"])-sz-1, int(t["y"])-sz-1))


def _draw_particles(surf):
    for p in _particles[:]:
        p["x"] += p["dx"]; p["y"] += p["dy"]; p["life"] -= 1
        p["dx"] *= 0.91; p["dy"] *= 0.91
        if p["type"] == "death": p["dy"] += 0.18
        if p["life"] <= 0: _particles.remove(p); continue
        ratio = p["life"]/p["max_life"]
        alpha = int(255*ratio); sz = max(1, int(p["size"]*ratio))
        c = p["color"]
        ps = pygame.Surface((sz*2+4, sz*2+4), pygame.SRCALPHA)
        cx, cy = sz+2, sz+2
        if p["type"] == "spark":
            pts = [(cx,cy-sz),(cx+sz,cy),(cx,cy+sz),(cx-sz,cy)]
            pygame.draw.polygon(ps, (*c, alpha), pts)
            if sz > 1: pygame.draw.circle(ps, (255,255,255,alpha), (cx,cy), max(1,sz//2))
        elif p["type"] == "sparkle":
            w = max(1, sz//2)
            pygame.draw.line(ps, (*c, alpha), (cx,cy-sz), (cx,cy+sz), w)
            pygame.draw.line(ps, (*c, alpha), (cx-sz,cy), (cx+sz,cy), w)
            pygame.draw.circle(ps, (255,255,255,alpha//2), (cx,cy), max(1,w))
        else:
            if sz > 2: pygame.draw.circle(ps, (*c, alpha//4), (cx,cy), sz+2)
            pygame.draw.circle(ps, (*c, alpha), (cx,cy), sz)
            if sz > 2:
                bc = (min(255,c[0]+100),min(255,c[1]+100),min(255,c[2]+100))
                pygame.draw.circle(ps, (*bc, alpha), (cx,cy), max(1,sz//2))
        surf.blit(ps, (int(p["x"])-sz-2, int(p["y"])-sz-2))


def _draw_shockwaves(surf):
    for s in _shockwaves[:]:
        s["life"] -= 1
        if s["life"] <= 0: _shockwaves.remove(s); continue
        ratio = s["life"]/s["max_life"]
        progress = 1.0 - ratio
        r = int(s["radius"]+(s["max_radius"]-s["radius"])*progress)
        alpha = int(150*ratio); c = s["color"]; w = max(1, int(s["width"]*ratio))
        ring = pygame.Surface((r*2+6, r*2+6), pygame.SRCALPHA)
        rcx, rcy = r+3, r+3
        if w > 1: pygame.draw.circle(ring, (*c, alpha//4), (rcx,rcy), r+2, w+2)
        pygame.draw.circle(ring, (*c, alpha), (rcx,rcy), r, w)
        pygame.draw.circle(ring, (255,255,255,alpha//3), (rcx,rcy), max(1,r-1), max(1,w//2))
        surf.blit(ring, (s["x"]-r-3, s["y"]-r-3))


def _draw_flashes(surf):
    for f in _flashes[:]:
        f["life"] -= 1
        if f["life"] <= 0: _flashes.remove(f); continue
        ratio = f["life"]/max(1, f["life"]+4)
        r = int(f["radius"]*(1+(1-ratio)*0.4)); alpha = int(80*ratio)
        fs = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA); c = f["color"]
        pygame.draw.circle(fs, (*c, alpha//2), (r+2,r+2), r)
        pygame.draw.circle(fs, (*c, alpha), (r+2,r+2), r*2//3)
        pygame.draw.circle(fs, (255,255,255,alpha//2), (r+2,r+2), r//3)
        surf.blit(fs, (f["x"]-r-2, f["y"]-r-2))


def _draw_zap_bolts(surf):
    for z in _zap_bolts[:]:
        z["life"] -= 1
        if z["life"] <= 0: _zap_bolts.remove(z); continue
        ratio = z["life"]/14; alpha = int(240*ratio)
        c = z["color"]; w = max(1, int(z["width"]*ratio))
        zs = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pts = z["points"]
        for i in range(len(pts)-1):
            pygame.draw.line(zs, (*c, alpha//4), pts[i], pts[i+1], w+6)
            pygame.draw.line(zs, (*c, alpha//2), pts[i], pts[i+1], w+3)
            pygame.draw.line(zs, (*c, alpha), pts[i], pts[i+1], w)
            if w > 1: pygame.draw.line(zs, (255,255,255,alpha), pts[i], pts[i+1], max(1,w-1))
        surf.blit(zs, (0,0))


def _draw_screen_flashes(surf):
    for f in _screen_flashes[:]:
        f["life"] -= 1
        if f["life"] <= 0: _screen_flashes.remove(f); continue
        ratio = f["life"]/f["max_life"]
        alpha = int(255*f["intensity"]*ratio)
        if alpha > 0:
            overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            overlay.fill((*f["color"], alpha))
            surf.blit(overlay, (0,0))


def _draw_damage_nums(surf):
    for d in _damage_nums[:]:
        d["life"] -= 1; d["y"] += d["dy"]; d["dy"] *= 0.96
        if d["life"] <= 0: _damage_nums.remove(d); continue
        ratio = min(1.0, d["life"]/20); alpha = int(255*ratio)
        sz = d["size"]
        if d["life"] > 35: sz = int(sz*(1.0+(d["life"]-35)*0.05))
        fnt = pygame.font.SysFont("Arial", sz, bold=True)
        ts = fnt.render(d["text"], True, (*d["color"],))
        ss = fnt.render(d["text"], True, (0,0,0))
        sa = pygame.Surface(ss.get_size(), pygame.SRCALPHA); sa.blit(ss, (0,0)); sa.set_alpha(alpha//2)
        surf.blit(sa, (int(d["x"])-ts.get_width()//2+2, int(d["y"])+2))
        ta = pygame.Surface(ts.get_size(), pygame.SRCALPHA); ta.blit(ts, (0,0)); ta.set_alpha(alpha)
        surf.blit(ta, (int(d["x"])-ts.get_width()//2, int(d["y"])))