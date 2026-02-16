# hat_menu.py
"""Hat collection and equip menu."""

import pygame, sys, math
import core.settings as settings_module
from core.settings import HAT_DEFS, RARITY_COLORS, save_config
from core.game_state import (
    display_mgr, clock, font, small_font, title_font, menu_font, header_font, desc_font
)



WHITE = (255, 255, 255)


def _draw_hat_preview(surf, cx, cy, hat_id, hat_color, sz=28):
    """Draw a preview of a hat shape."""
    if not hat_color:
        return
    c = hat_color
    r = sz // 2
    top = cy - r
    hid = hat_id

    if hid == "beanie":
        pygame.draw.arc(surf, c, (cx-r, top, sz, r), 0, math.pi, 3)
        pygame.draw.circle(surf, c, (cx, top), 3)
    elif hid == "cap":
        pygame.draw.rect(surf, c, (cx-r, cy-2, sz, 5), border_radius=2)
        pygame.draw.rect(surf, c, (cx-r+4, cy-r+2, sz-8, r), border_radius=3)
        pygame.draw.line(surf, c, (cx-r, cy-2), (cx-r-6, cy+2), 2)
    elif hid == "headband":
        pygame.draw.rect(surf, c, (cx-r, cy-2, sz, 4), border_radius=1)
    elif hid == "bandana":
        pts = [(cx-r, cy-2), (cx+r, cy-2), (cx+r-3, cy+4), (cx-r+3, cy+4)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "tophat":
        pygame.draw.rect(surf, c, (cx-r, cy, sz, 4), border_radius=1)
        pygame.draw.rect(surf, c, (cx-r+4, cy-r, sz-8, r+2), border_radius=2)
    elif hid == "wizard":
        pts = [(cx, top-4), (cx-r, cy+2), (cx+r, cy+2)]
        pygame.draw.polygon(surf, c, pts)
        pygame.draw.circle(surf, (255,255,100), (cx, top-4), 3)
    elif hid == "cowboy":
        pygame.draw.rect(surf, c, (cx-r-2, cy, sz+4, 4), border_radius=1)
        pygame.draw.arc(surf, c, (cx-r+2, cy-r+4, sz-4, r), 0, math.pi, 3)
    elif hid == "beret":
        pygame.draw.ellipse(surf, c, (cx-r, cy-r//2, sz, r))
        pygame.draw.circle(surf, c, (cx+2, cy-r//2), 3)
    elif hid == "antenna":
        pygame.draw.line(surf, c, (cx, cy), (cx-5, top-4), 2)
        pygame.draw.line(surf, c, (cx, cy), (cx+5, top-4), 2)
        pygame.draw.circle(surf, c, (cx-5, top-4), 4)
        pygame.draw.circle(surf, c, (cx+5, top-4), 4)
    elif hid == "catears":
        pygame.draw.polygon(surf, c, [(cx-r+2, cy), (cx-r, top), (cx-4, cy)])
        pygame.draw.polygon(surf, c, [(cx+4, cy), (cx+r, top), (cx+r-2, cy)])
    elif hid == "devilhorns":
        pygame.draw.line(surf, c, (cx-8, cy), (cx-12, top-2), 3)
        pygame.draw.line(surf, c, (cx+8, cy), (cx+12, top-2), 3)
    elif hid == "halo":
        pygame.draw.ellipse(surf, (*c, 180), (cx-r, top, sz, r//2), 2)
    elif hid == "crown":
        pts = [(cx-r+2, cy), (cx-r+2, top+4), (cx-r//2, cy-4), (cx, top),
               (cx+r//2, cy-4), (cx+r-2, top+4), (cx+r-2, cy)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "viking":
        pygame.draw.arc(surf, c, (cx-r+2, cy-r+4, sz-4, r), 0, math.pi, 3)
        pygame.draw.line(surf, c, (cx-r+2, cy-2), (cx-r-4, top-2), 3)
        pygame.draw.line(surf, c, (cx+r-2, cy-2), (cx+r+4, top-2), 3)
    elif hid == "flamehat":
        for i in range(-8, 10, 4):
            h2 = 8 + (hash(i) % 6)
            pygame.draw.line(surf, c, (cx+i, cy), (cx+i, cy-h2), 2)
    elif hid == "icehat":
        pts = [(cx-r+2, cy), (cx-r//2, top), (cx, cy-4), (cx+r//2, top), (cx+r-2, cy)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "voidhat":
        pygame.draw.circle(surf, c, (cx, cy-4), r//2+2, 2)
        pygame.draw.circle(surf, (40,0,60), (cx, cy-4), r//3)
    elif hid == "stormhat":
        pygame.draw.arc(surf, c, (cx-r+2, cy-r+4, sz-4, r), 0, math.pi, 3)
        pygame.draw.line(surf, (255,255,100), (cx-3, top+2), (cx-5, cy+4), 2)
        pygame.draw.line(surf, (255,255,100), (cx+3, top+2), (cx+5, cy+4), 2)
    elif hid == "omegahat":
        colors = [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,200,255),(150,0,255)]
        for i, rc in enumerate(colors):
            pygame.draw.arc(surf, rc, (cx-r-i, top-i, sz+i*2, r//2+i*2), 0, math.pi, 2)
    elif hid == "shadowhat":
        vs = pygame.Surface((sz+4, r+4), pygame.SRCALPHA)
        vs.fill((*c, 80))
        surf.blit(vs, (cx-r-2, top-2))
    elif hid == "hardhat":
        pygame.draw.arc(surf, c, (cx-r, top, sz, r), 0, math.pi, 3)
        pygame.draw.rect(surf, c, (cx-r-2, cy-1, sz+4, 3))
    elif hid == "bucket":
        pygame.draw.rect(surf, c, (cx-r+2, top, sz-4, r), border_radius=2)
        pygame.draw.rect(surf, (min(255,c[0]+30),min(255,c[1]+30),min(255,c[2]+30)),
                         (cx-r, cy-1, sz, 3))
    elif hid == "party":
        pts = [(cx, top-4), (cx-r+2, cy+1), (cx+r-2, cy+1)]
        pygame.draw.polygon(surf, c, pts)
        pygame.draw.circle(surf, (255,255,0), (cx, top-4), 2)
    elif hid == "bow":
        pygame.draw.polygon(surf, c, [(cx-r, cy-1), (cx-3, cy-4), (cx-3, cy+2)])
        pygame.draw.polygon(surf, c, [(cx+r, cy-1), (cx+3, cy-4), (cx+3, cy+2)])
        pygame.draw.circle(surf, (min(255,c[0]+40),min(255,c[1]+40),min(255,c[2]+40)), (cx, cy-1), 2)
    elif hid == "earmuffs":
        pygame.draw.arc(surf, c, (cx-r, top, sz, r//2), 0, math.pi, 2)
        pygame.draw.circle(surf, c, (cx-r, cy), 4)
        pygame.draw.circle(surf, c, (cx+r, cy), 4)
    elif hid == "fez":
        pygame.draw.rect(surf, c, (cx-r//2, top, r, r), border_radius=2)
        pygame.draw.rect(surf, c, (cx-r//2-2, cy-1, r+4, 2))
        pygame.draw.circle(surf, (255,215,0), (cx+r//2+2, top-1), 2)
    elif hid == "pirate":
        pygame.draw.arc(surf, c, (cx-r, top, sz, r), 0, math.pi, 3)
        pygame.draw.rect(surf, c, (cx-r-2, cy-1, sz+4, 3))
        pygame.draw.circle(surf, (220,220,220), (cx, cy-4), 3)
    elif hid == "chef":
        pygame.draw.circle(surf, c, (cx-4, top+2), 5)
        pygame.draw.circle(surf, c, (cx+4, top+2), 5)
        pygame.draw.circle(surf, c, (cx, top), 6)
    elif hid == "mohawk":
        for i in range(-4, 6, 2):
            h2 = 10 - abs(i)
            pygame.draw.line(surf, c, (cx+i, cy), (cx+i, cy-h2), 2)
    elif hid == "flower":
        colors = [(255,120,180),(255,200,100),(180,100,255),(100,200,255),(255,150,100)]
        for i, fc in enumerate(colors):
            a = (i / 5) * math.pi * 2 - math.pi/2
            fx = cx + int(8 * math.cos(a))
            fy = cy-3 + int(5 * math.sin(a))
            pygame.draw.circle(surf, fc, (fx, fy), 3)
        pygame.draw.circle(surf, (255,255,100), (cx, cy-3), 2)
    elif hid == "straw":
        pygame.draw.rect(surf, c, (cx-r-2, cy-1, sz+4, 3))
        pygame.draw.arc(surf, c, (cx-r+2, top, sz-4, r), 0, math.pi, 3)
    elif hid == "bunnyears":
        pygame.draw.ellipse(surf, c, (cx-r+2, top-6, 6, 16))
        pygame.draw.ellipse(surf, c, (cx+r-8, top-6, 6, 16))
    elif hid == "propeller":
        pygame.draw.rect(surf, c, (cx-r+4, cy-3, sz-8, 6), border_radius=2)
        pygame.draw.line(surf, (255,50,50), (cx-8, cy-5), (cx+8, cy-5), 2)
        pygame.draw.circle(surf, (200,200,200), (cx, cy-5), 2)
    elif hid == "shark":
        pts = [(cx, top-4), (cx-6, cy+1), (cx+6, cy+1)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "mushroom":
        pygame.draw.ellipse(surf, c, (cx-r, top, sz, r))
        pygame.draw.rect(surf, (220,200,180), (cx-3, cy-2, 6, 4), border_radius=1)
        pygame.draw.circle(surf, (255,255,255), (cx-4, top+3), 2)
    elif hid == "samurai":
        pygame.draw.arc(surf, c, (cx-r, top+2, sz, r), 0, math.pi, 3)
        pygame.draw.polygon(surf, (200,170,0), [(cx, top-4), (cx-3, top+4), (cx+3, top+4)])
    elif hid == "disco":
        pygame.draw.circle(surf, c, (cx, cy-4), r//2+2)
        for i in range(4):
            a = (i / 4) * math.pi * 2
            sx2 = cx + int(4 * math.cos(a))
            sy2 = cy-4 + int(4 * math.sin(a))
            pygame.draw.circle(surf, [(255,255,100),(100,255,255),(255,100,255),(255,200,100)][i], (sx2, sy2), 1)
    elif hid == "hydrahat":
        for off in [-6, 0, 6]:
            pygame.draw.line(surf, c, (cx+off, cy), (cx+off, top), 2)
            pygame.draw.circle(surf, c, (cx+off, top), 2)
    elif hid == "phantomhat":
        vs = pygame.Surface((sz, r), pygame.SRCALPHA)
        vs.fill((*c, 60))
        surf.blit(vs, (cx-r, top))
        pygame.draw.circle(surf, (*c, 150), (cx-4, cy-4), 2)
        pygame.draw.circle(surf, (*c, 150), (cx+4, cy-4), 2)
    elif hid == "fortresshat":
        pygame.draw.rect(surf, c, (cx-r, cy-3, sz, 6))
        for bx in range(-r+1, r, 5):
            pygame.draw.rect(surf, c, (cx+bx, cy-7, 3, 4))
    elif hid == "neonhat":
        pygame.draw.rect(surf, (*c, 180), (cx-r, cy-3, sz, 5), border_radius=2)
        gs2 = pygame.Surface((sz+4, 10), pygame.SRCALPHA)
        pygame.draw.rect(gs2, (*c, 40), (0, 0, sz+4, 10), border_radius=4)
        surf.blit(gs2, (cx-r-2, cy-6))
    elif hid == "galaxyhat":
        pygame.draw.circle(surf, c, (cx, cy-4), r//2+2)
        pygame.draw.circle(surf, (255,255,200), (cx, cy-4), 2)
    elif hid == "glitchhat":
        for i in range(4):
            gx = cx - 8 + (i * 5)
            gc = [(255,0,255),(0,255,255),(255,255,0),(255,0,100)][i]
            pygame.draw.rect(surf, gc, (gx, cy-6+i*2, 5, 2))
    elif hid == "tinfoil":
        pts = [(cx-r, cy), (cx-r//2, top-2), (cx+2, top+2), (cx+r-2, top-4), (cx+r, cy)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "backwards_cap":
        pygame.draw.rect(surf, c, (cx-r, cy-2, sz, 5), border_radius=2)
        pygame.draw.rect(surf, c, (cx-r+3, top+2, sz-6, r-2), border_radius=3)
        pygame.draw.line(surf, c, (cx+r-2, cy-2), (cx+r+4, cy+1), 2)
    elif hid == "nightcap":
        pygame.draw.arc(surf, c, (cx-r+4, top, sz-8, r), 0, math.pi, 3)
        pygame.draw.line(surf, c, (cx+r-4, top+r//3), (cx+r+2, top-2), 2)
        pygame.draw.circle(surf, (200,180,255), (cx+r+2, top-2), 2)
    elif hid == "afro":
        pygame.draw.circle(surf, c, (cx, cy-4), r)
    elif hid == "nurse":
        pygame.draw.rect(surf, c, (cx-r+4, top+2, sz-8, r-2), border_radius=2)
        pygame.draw.line(surf, (255,50,50), (cx-2, cy-4), (cx+2, cy-4), 2)
        pygame.draw.line(surf, (255,50,50), (cx, cy-6), (cx, cy-2), 2)
    elif hid == "aviator":
        pygame.draw.circle(surf, c, (cx-5, cy-1), 4, 2)
        pygame.draw.circle(surf, c, (cx+5, cy-1), 4, 2)
        pygame.draw.line(surf, c, (cx-1, cy-1), (cx+1, cy-1), 1)
    elif hid == "ushanka":
        pygame.draw.arc(surf, c, (cx-r, top, sz, r), 0, math.pi, 3)
        pygame.draw.rect(surf, c, (cx-r-2, cy-2, 5, 6), border_radius=1)
        pygame.draw.rect(surf, c, (cx+r-3, cy-2, 5, 6), border_radius=1)
    elif hid == "witchhat":
        pts = [(cx, top-6), (cx-r, cy+1), (cx+r, cy+1)]
        pygame.draw.polygon(surf, c, pts)
        pygame.draw.rect(surf, c, (cx-r-1, cy-1, sz+2, 3))
    elif hid == "antlers":
        pygame.draw.line(surf, c, (cx-6, cy), (cx-9, top), 2)
        pygame.draw.line(surf, c, (cx-9, top), (cx-12, top+3), 1)
        pygame.draw.line(surf, c, (cx-9, top), (cx-6, top-3), 1)
        pygame.draw.line(surf, c, (cx+6, cy), (cx+9, top), 2)
        pygame.draw.line(surf, c, (cx+9, top), (cx+12, top+3), 1)
        pygame.draw.line(surf, c, (cx+9, top), (cx+6, top-3), 1)
    elif hid == "tiara":
        pygame.draw.arc(surf, c, (cx-r+2, top+2, sz-4, r-2), 0, math.pi, 2)
        pygame.draw.circle(surf, (255,200,255), (cx, top+3), 2)
    elif hid == "bloodcrown":
        pts = [(cx-r+2,cy),(cx-r+2,top+3),(cx-r//2,cy-2),(cx,top),
               (cx+r//2,cy-2),(cx+r-2,top+3),(cx+r-2,cy)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "soulflame":
        for i in range(-6,8,3):
            h2 = 6 + abs(i) % 4
            pygame.draw.line(surf, c, (cx+i, cy), (cx+i, cy-h2), 2)
    elif hid == "thunderhelm":
        pygame.draw.arc(surf, c, (cx-r+2, top+2, sz-4, r), 0, math.pi, 3)
        pygame.draw.line(surf, (255,255,100), (cx-3, top+2), (cx-5, cy+2), 1)
        pygame.draw.line(surf, (255,255,100), (cx+3, top+2), (cx+5, cy+2), 1)
    elif hid == "toxicmask":
        pygame.draw.ellipse(surf, c, (cx-r+2, top+2, sz-4, r-2))
        pygame.draw.circle(surf, (0,0,0), (cx-4, cy-3), 2)
        pygame.draw.circle(surf, (0,0,0), (cx+4, cy-3), 2)
    elif hid == "magichat":
        pts = [(cx, top-4), (cx-r+2, cy+1), (cx+r-2, cy+1)]
        pygame.draw.polygon(surf, c, pts)
        pygame.draw.circle(surf, (255,255,200), (cx, top-4), 2)
    elif hid == "phoenixhat":
        for off in [-4,-2,0,2,4]:
            h2 = 10 - abs(off)*2
            fc = (255, max(80,160-abs(off)*30), 0)
            pygame.draw.line(surf, fc, (cx+off, cy), (cx+off, cy-h2), 2)
    elif hid == "cosmichat":
        pygame.draw.circle(surf, c, (cx, cy-3), r//2+3)
        pygame.draw.circle(surf, (20,10,40), (cx, cy-3), r//2)
        pygame.draw.circle(surf, (255,255,200), (cx, cy-3), 1)
    else:
        pygame.draw.circle(surf, c, (cx, cy-4), r//2, 2)


def show_hat_menu():
    """Show hat collection with equip ability."""
    t = 0.0
    scroll = 0
    equipped = settings_module.config.get("equipped_hat", None)
    collected = settings_module.config.get("collected_hats", [])

    # Sort: collected first, by rarity
    rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "uncommon": 3, "common": 4}
    hats = sorted(HAT_DEFS, key=lambda h: (0 if h["id"] in collected else 1, rarity_order.get(h["rarity"], 5)))

    while True:
        t += 0.03
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill((5, 5, 15))

        # Title
        tt = header_font.render("HAT COLLECTION", True, (255, 150, 200))
        surf.blit(tt, (sw//2 - tt.get_width()//2, 16))

        count = sum(1 for h in HAT_DEFS if h["id"] in collected and h["id"] != "none")
        total = len(HAT_DEFS) - 1  # exclude "none"
        ct = small_font.render(f"Collected: {count}/{total}", True, (100, 110, 130))
        surf.blit(ct, (sw//2 - ct.get_width()//2, 50))

        # Grid of hat cards
        card_w, card_h = 120, 100
        cols = max(1, (sw - 60) // (card_w + 10))
        gap = 10
        grid_w = cols * card_w + (cols-1) * gap
        gx = sw//2 - grid_w//2
        gy = 70 - scroll

        rects = []
        for i, hat in enumerate(hats):
            if hat["id"] == "none":
                continue
            row, col = i // cols, i % cols
            cx = gx + col * (card_w + gap)
            cy = gy + row * (card_h + gap)

            # Skip if off screen
            if cy + card_h < 60 or cy > sh:
                rects.append((pygame.Rect(0,0,0,0), hat))
                continue

            cr = pygame.Rect(cx, cy, card_w, card_h)
            rects.append((cr, hat))
            owned = hat["id"] in collected
            is_eq = hat["id"] == equipped
            hov = cr.collidepoint(mx, my) and owned
            rc = RARITY_COLORS.get(hat["rarity"], (180,180,190))

            # Card bg
            bg = pygame.Surface((card_w, card_h))
            if not owned:
                bg.fill((20, 20, 30))
                bg.set_alpha(200)
            elif is_eq:
                bg.fill(rc[:3])
                bg.set_alpha(50)
            elif hov:
                bg.fill(rc[:3])
                bg.set_alpha(30)
            else:
                bg.fill(rc[:3])
                bg.set_alpha(12)
            surf.blit(bg, (cx, cy))

            # Border
            bc = rc if owned else (40, 40, 55)
            bw = 3 if is_eq else (2 if hov else 1)
            pygame.draw.rect(surf, bc, cr, bw, border_radius=6)

            if is_eq:
                # "EQUIPPED" badge
                eb = small_font.render("EQUIPPED", True, rc)
                surf.blit(eb, (cx + card_w//2 - eb.get_width()//2, cy + 2))

            if owned:
                # Draw hat preview
                _draw_hat_preview(surf, cx + card_w//2, cy + 40, hat["id"], hat.get("color"), sz=30)
                # Name
                nt = small_font.render(hat["name"], True, rc)
                surf.blit(nt, (cx + card_w//2 - nt.get_width()//2, cy + 60))
                # Rarity
                rt = desc_font.render(hat["rarity"].upper(), True, rc)
                surf.blit(rt, (cx + card_w//2 - rt.get_width()//2, cy + 78))
                # Animated badge
                if hat.get("anim"):
                    ab_t = desc_font.render("★ FX", True, (255,255,100))
                    surf.blit(ab_t, (cx + card_w - ab_t.get_width() - 4, cy + 2))
            else:
                # Locked
                pygame.draw.line(surf, (40,40,55), (cx+card_w//2-8, cy+36), (cx+card_w//2+8, cy+36), 2)
                pygame.draw.line(surf, (40,40,55), (cx+card_w//2, cy+28), (cx+card_w//2, cy+44), 2)
                lt = desc_font.render("???", True, (50, 50, 65))
                surf.blit(lt, (cx + card_w//2 - lt.get_width()//2, cy + 60))
                rt = desc_font.render(hat["rarity"].upper(), True, (40, 40, 55))
                surf.blit(rt, (cx + card_w//2 - rt.get_width()//2, cy + 78))

        # Unequip button
        ub_rect = pygame.Rect(sw//2 - 80, sh - 80, 160, 36)
        ub_hov = ub_rect.collidepoint(mx, my)
        ub_bg = pygame.Surface((160, 36))
        ub_bg.fill((100, 100, 120))
        ub_bg.set_alpha(40 if ub_hov else 15)
        surf.blit(ub_bg, ub_rect.topleft)
        pygame.draw.rect(surf, (160,170,190) if ub_hov else (80,80,100), ub_rect, 2, border_radius=5)
        ubt = menu_font.render("Remove Hat" if equipped else "No Hat", True,
                               WHITE if ub_hov else (120,130,150))
        surf.blit(ubt, (ub_rect.centerx - ubt.get_width()//2, ub_rect.centery - ubt.get_height()//2))

        # Back button
        bb_rect = pygame.Rect(sw//2 - 80, sh - 38, 160, 32)
        bb_hov = bb_rect.collidepoint(mx, my)
        bbt = menu_font.render("Back", True, WHITE if bb_hov else (100,110,130))
        surf.blit(bbt, (bb_rect.centerx - bbt.get_width()//2, bb_rect.centery - bbt.get_height()//2))

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return
            if ev.type == pygame.MOUSEWHEEL:
                scroll = max(0, scroll - ev.y * 30)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if bb_rect.collidepoint(ev.pos):
                    return
                if ub_rect.collidepoint(ev.pos):
                    equipped = None
                    settings_module.config["equipped_hat"] = None
                    save_config(settings_module.config)
                for cr, hat in rects:
                    if cr.collidepoint(ev.pos) and hat["id"] in collected:
                        equipped = hat["id"]
                        settings_module.config["equipped_hat"] = hat["id"]
                        save_config(settings_module.config)
                        break

        clock.tick(settings_module.FPS or 0)