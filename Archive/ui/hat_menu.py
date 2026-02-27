# hat_menu.py
"""Hat collection and equip menu — global standards, click-to-unequip."""

import pygame, sys, math
import core.settings as settings_module
from core.settings import HAT_DEFS, RARITY_COLORS, save_config
import core.game_state as _gs
from core.game_state import display_mgr, clock

# ── Shared colors ──
ACCENT = (0, 200, 255)
BG_DARK = (5, 6, 16)
TEXT_DIM = (60, 65, 80)
TEXT_MID = (130, 140, 160)
TEXT_BRIGHT = (220, 225, 240)
BORDER = (35, 40, 60)
WHITE = (255, 255, 255)

RARITY_ORDER = {"exotic": 0, "legendary": 1, "epic": 2, "rare": 3, "uncommon": 4, "common": 5}


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
        pygame.draw.ellipse(surf, c, (cx-r, top, sz, r//2), 2)
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
        pygame.draw.rect(surf, c, (cx-r, top, sz, r))
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
    elif hid == "earmuffs":
        pygame.draw.arc(surf, c, (cx-r, top, sz, r//2), 0, math.pi, 2)
        pygame.draw.circle(surf, c, (cx-r, cy), 4)
        pygame.draw.circle(surf, c, (cx+r, cy), 4)
    elif hid == "fez":
        pygame.draw.rect(surf, c, (cx-r//2, top, r, r), border_radius=2)
        pygame.draw.rect(surf, c, (cx-r//2-2, cy-1, r+4, 2))
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
        fcolors = [(255,120,180),(255,200,100),(180,100,255),(100,200,255),(255,150,100)]
        for i, fc in enumerate(fcolors):
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
    elif hid == "samurai":
        pygame.draw.arc(surf, c, (cx-r, top+2, sz, r), 0, math.pi, 3)
        pygame.draw.polygon(surf, (200,170,0), [(cx, top-4), (cx-3, top+4), (cx+3, top+4)])
    elif hid == "disco":
        pygame.draw.circle(surf, c, (cx, cy-4), r//2+2)
    elif hid == "hydrahat":
        for off in [-6, 0, 6]:
            pygame.draw.line(surf, c, (cx+off, cy), (cx+off, top), 2)
            pygame.draw.circle(surf, c, (cx+off, top), 2)
    elif hid == "phantomhat":
        pygame.draw.rect(surf, c, (cx-r, top, sz, r))
    elif hid == "fortresshat":
        pygame.draw.rect(surf, c, (cx-r, cy-3, sz, 6))
        for bx in range(-r+1, r, 5):
            pygame.draw.rect(surf, c, (cx+bx, cy-7, 3, 4))
    elif hid == "neonhat":
        pygame.draw.rect(surf, c, (cx-r, cy-3, sz, 5), border_radius=2)
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
        pygame.draw.line(surf, c, (cx+6, cy), (cx+9, top), 2)
        pygame.draw.line(surf, c, (cx+9, top), (cx+12, top+3), 1)
    elif hid == "tiara":
        pygame.draw.arc(surf, c, (cx-r+2, top+2, sz-4, r-2), 0, math.pi, 2)
        pygame.draw.circle(surf, (255,200,255), (cx, top+3), 2)
    elif hid == "bloodcrown":
        pts = [(cx-r+2,cy),(cx-r+2,top+3),(cx-r//2,cy-2),(cx,top),
               (cx+r//2,cy-2),(cx+r-2,top+3),(cx+r-2,cy)]
        pygame.draw.polygon(surf, c, pts)
    elif hid == "soulflame":
        for i in range(-6, 8, 3):
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
            fc = (255, max(80, 160-abs(off)*30), 0)
            pygame.draw.line(surf, fc, (cx+off, cy), (cx+off, cy-h2), 2)
    elif hid == "cosmichat":
        pygame.draw.circle(surf, c, (cx, cy-3), r//2+3)
        pygame.draw.circle(surf, (20,10,40), (cx, cy-3), r//2)
        pygame.draw.circle(surf, (255,255,200), (cx, cy-3), 1)
    else:
        pygame.draw.circle(surf, c, (cx, cy-4), r//2, 2)


def _back_btn(surf, mx, my):
    r = pygame.Rect(16, 16, 90, 34)
    hov = r.collidepoint(mx, my)
    c = ACCENT if hov else TEXT_DIM
    pygame.draw.rect(surf, c, r, 1 if not hov else 2, border_radius=5)
    t = _gs.small_font.render("< Back", True, TEXT_BRIGHT if hov else TEXT_MID)
    surf.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))
    return r


def show_hat_menu():
    """Show hat collection with click-to-equip/unequip."""
    scroll = 0
    equipped = settings_module.config.get("equipped_hat", None)
    collected = settings_module.config.get("collected_hats", [])

    # Filter out "none", sort: owned first, then by rarity
    hats = [h for h in HAT_DEFS if h["id"] != "none"]
    hats.sort(key=lambda h: (0 if h["id"] in collected else 1, RARITY_ORDER.get(h["rarity"], 9)))

    while True:
        sw, sh = settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()
        mx, my = pygame.mouse.get_pos()

        surf.fill(BG_DARK)

        # ── Back button (universal, top-left) ──
        back_r = _back_btn(surf, mx, my)

        # ── Title ──
        tt = _gs.menu_font.render("COSMETICS", True, TEXT_BRIGHT)
        surf.blit(tt, (sw//2 - tt.get_width()//2, 20))

        # ── Collected count (top-right) ──
        count = sum(1 for h in hats if h["id"] in collected)
        total = len(hats)
        ct = _gs.small_font.render(f"{count}/{total} collected", True, TEXT_DIM)
        surf.blit(ct, (sw - ct.get_width() - 20, 24))

        # ── Grid ──
        card_w, card_h = 120, 100
        cols = max(1, (sw - 60) // (card_w + 10))
        gap = 10
        grid_w = cols * card_w + (cols - 1) * gap
        gx = sw // 2 - grid_w // 2
        gy = 54 - scroll

        total_rows = (len(hats) + cols - 1) // cols
        total_grid_h = total_rows * (card_h + gap)
        max_scroll = max(0, total_grid_h - (sh - 100))

        rects = []
        for i, hat in enumerate(hats):
            row, col = i // cols, i % cols
            cx = gx + col * (card_w + gap)
            cy = gy + row * (card_h + gap)

            cr = pygame.Rect(cx, cy, card_w, card_h)
            rects.append((cr, hat))

            # Skip off-screen
            if cy + card_h < 55 or cy > sh:
                continue

            owned = hat["id"] in collected
            is_eq = hat["id"] == equipped
            hov = cr.collidepoint(mx, my) and cy + card_h > 0 and cy < sh
            rc = RARITY_COLORS.get(hat["rarity"], (180, 180, 190))

            # Card background
            if not owned:
                pygame.draw.rect(surf, (15, 16, 26), cr, 0, border_radius=6)
                border_c = (30, 32, 48)
            elif is_eq:
                pygame.draw.rect(surf, (15, 22, 35), cr, 0, border_radius=6)
                border_c = rc
            elif hov:
                pygame.draw.rect(surf, (18, 22, 38), cr, 0, border_radius=6)
                border_c = rc
            else:
                pygame.draw.rect(surf, (12, 14, 26), cr, 0, border_radius=6)
                border_c = BORDER

            bw = 2 if (is_eq or hov) else 1
            pygame.draw.rect(surf, border_c, cr, bw, border_radius=6)

            # Equipped badge
            if is_eq:
                eb = _gs.desc_font.render("EQUIPPED", True, rc)
                surf.blit(eb, (cx + card_w//2 - eb.get_width()//2, cy + 3))

            if owned:
                # Hat preview
                _draw_hat_preview(surf, cx + card_w//2, cy + 42, hat["id"], hat.get("color"), sz=30)
                # Name
                nt = _gs.small_font.render(hat["name"], True, rc)
                surf.blit(nt, (cx + card_w//2 - nt.get_width()//2, cy + 62))
                # Rarity
                rt = _gs.desc_font.render(hat["rarity"].upper(), True, rc)
                surf.blit(rt, (cx + card_w//2 - rt.get_width()//2, cy + 80))
                # Animated/FX badge for exotic
                if hat.get("anim") and hat["rarity"] == "exotic":
                    ab = _gs.desc_font.render("* FX", True, (255, 100, 140))
                    surf.blit(ab, (cx + card_w - ab.get_width() - 4, cy + 3))
                elif hat.get("anim"):
                    ab = _gs.desc_font.render("*", True, (255, 255, 100))
                    surf.blit(ab, (cx + card_w - ab.get_width() - 4, cy + 3))
            else:
                # Locked — dim, no plus signs
                pygame.draw.circle(surf, (30, 32, 48), (cx + card_w//2, cy + 40), 10, 1)
                lt = _gs.desc_font.render("???", True, (40, 42, 58))
                surf.blit(lt, (cx + card_w//2 - lt.get_width()//2, cy + 62))
                rt = _gs.desc_font.render(hat["rarity"].upper(), True, (35, 38, 52))
                surf.blit(rt, (cx + card_w//2 - rt.get_width()//2, cy + 80))

        # Scroll indicator
        if max_scroll > 0:
            vis_h = sh - 100
            bar_h = max(20, int(vis_h * vis_h / (total_grid_h + 1)))
            bar_y = 54 + int(scroll / max(1, max_scroll) * (vis_h - bar_h))
            pygame.draw.rect(surf, (25, 28, 42), (sw - 14, 54, 5, vis_h), border_radius=3)
            pygame.draw.rect(surf, ACCENT, (sw - 14, bar_y, 5, bar_h), border_radius=3)

        # ── Bottom bar: equipped hat info ──
        bottom_y = sh - 36
        pygame.draw.line(surf, BORDER, (20, bottom_y - 6), (sw - 20, bottom_y - 6), 1)
        if equipped:
            eq_hat = next((h for h in hats if h["id"] == equipped), None)
            if eq_hat:
                eq_rc = RARITY_COLORS.get(eq_hat["rarity"], TEXT_MID)
                eq_txt = _gs.small_font.render(f"Equipped: {eq_hat['name']}", True, eq_rc)
                surf.blit(eq_txt, (20, bottom_y))
                hint = _gs.desc_font.render("Click equipped hat to unequip", True, TEXT_DIM)
                surf.blit(hint, (sw - hint.get_width() - 20, bottom_y + 4))
        else:
            nt = _gs.small_font.render("No hat equipped", True, TEXT_DIM)
            surf.blit(nt, (20, bottom_y))

        display_mgr.present()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return
            if ev.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(max_scroll, scroll - ev.y * 35))
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if back_r.collidepoint(ev.pos):
                    return
                for cr, hat in rects:
                    if cr.collidepoint(ev.pos) and hat["id"] in collected:
                        if equipped == hat["id"]:
                            equipped = None
                            settings_module.config["equipped_hat"] = None
                        else:
                            equipped = hat["id"]
                            settings_module.config["equipped_hat"] = hat["id"]
                        save_config(settings_module.config)
                        break

        clock.tick(settings_module.FPS or 0)