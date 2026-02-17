# game.py
"""Main game loop (run_game)."""

import pygame
import sys
import random
import math
import core.settings as settings_module
from core.settings import *
from entities.objects import Bullet, LaserBeam, ExpGem, HealthOrb, EnemyProjectile, GoldCoin, XPRoomba, SpinningSaw
from entities.enemy import (Enemy, Boss, ArrowEnemy, TankEnemy, SplitterEnemy, ZigZagEnemy,
                            TeleportEnemy, ShieldEnemy, SwarmEnemy, VortexEnemy, NecroEnemy,
                            SpiralEnemy, MineLayerEnemy, ProximityMine, LaserDrone, LeechPriest, PhaseWraith,
                            ChargerBull, MimicEnemy, OrbiterEnemy, SniperEnemy, ParasiteEnemy,
                            BossMinion, HydraSpawnling, PhantomWisp, FortressGuard, StormWisp,
                            VoidLing, InfernoImp, FrostShard, ShadowShade, OmegaDrone,
                            HydraBoss, HydraMini, PhantomBoss, FortressBoss, StormBoss,
                            VoidBoss, InfernoBoss, FrostBoss, ShadowBoss, OmegaBoss,
                            create_boss_for_wave)
from core.sprite_loader import load_sprite
from networking.net_common import *
import core.game_state as _gs
from core.game_state import (
    display_mgr, clock, sounds, gs, PLAYER_CLASSES,
    trigger_shake, get_shake, consume_shake,
    GAME_NAME, VERSION
)
from game.helpers import (
    get_nearest_enemies, handle_enemy_death, apply_magnet,
    apply_gold_magnet, get_perma_stats, add_gold, hat_notifications
)
from ui.hud import draw_ui, draw_boss_health_bar, draw_wave_banner, draw_enemy_health_bars, draw_fps_ping
from ui.upgrade_menu import show_upgrade_menu
from ui.menus import show_pause_menu, show_game_over
from ui import vfx
from entities.remote_ghosts import RemoteEnemyGhost, RemotePlayerGhost

def run_game(class_key, starting_wave=1):

    # Reset per-run multiplayer state
    gs._was_revived = set()

    # Create player from selected class
    PlayerClass = PLAYER_CLASSES[class_key]
    player_obj = PlayerClass()
    player_obj.reposition(settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT)

    # Hexagon background state
    hex_time = 0.0
    hex_grid = []
    hex_radius = 50
    hex_h = hex_radius * 2
    hex_w = int(hex_radius * math.sqrt(3))
    for row in range(-1, settings_module.SCREEN_HEIGHT // int(hex_h * 0.75) + 3):
        for col in range(-1, settings_module.SCREEN_WIDTH // hex_w + 3):
            x = col * hex_w + (row % 2) * (hex_w // 2)
            y = row * int(hex_h * 0.75)
            phase = (col * 0.3 + row * 0.5) % (2 * math.pi)
            hex_grid.append((x, y, phase))

    # Groups
    all_sprites = pygame.sprite.Group()
    vfx.clear()
    enemies_grp = pygame.sprite.Group()
    bullets_grp = pygame.sprite.Group()
    gems_grp = pygame.sprite.Group()
    health_orbs_grp = pygame.sprite.Group()
    enemy_projectiles_grp = pygame.sprite.Group()  # For Tank enemy bullets
    mines_grp = pygame.sprite.Group()  # Proximity mines
    gold_grp = pygame.sprite.Group()  # Gold coins
    roombas_grp = pygame.sprite.Group()  # XP Roombas
    saws_grp = pygame.sprite.Group()  # Spinning Saws

    all_sprites.add(player_obj)

    # ---- Apply perma upgrades ----
    pstats = get_perma_stats()

    # Base magnet from perma shop
    player_obj.stats["magnet"] += int(pstats["base_magnet"] / MAGNET_PER_UPGRADE) if MAGNET_PER_UPGRADE > 0 else 0

    # Starting HP bonus
    if pstats["starting_hp"] > 0:
        player_obj.stats["max_health"] += pstats["starting_hp"]
        player_obj.current_health = player_obj.stats["max_health"]

    # Crit chance (stored on player for bullet damage)
    player_obj.crit_chance = pstats["crit_chance"]

    # Armor (damage reduction)
    player_obj.armor = pstats["armor"]

    # Revivals
    revivals_remaining = pstats["revivals"]

    # Dash power from perma shop
    dash_cd_reduction = pstats.get("dash_cooldown_reduction", 0)
    dash_dur_bonus = pstats.get("dash_duration_bonus", 0)
    player_obj.dash_cooldown_max = max(5, player_obj.dash_cooldown_max - dash_cd_reduction)
    player_obj.dash_duration_max += dash_dur_bonus

    # Store roomba range mult for dynamic updates
    _roomba_range_mult = pstats.get("roomba_range", 1.0)
    _roomba_damage = pstats.get("roomba_damage", 0)

    # New perma stats
    _health_regen_rate = pstats.get("health_regen", 0)  # HP per second
    _health_regen_accum = 0.0
    _dodge_chance = pstats.get("dodge_chance", 0)
    _thorns_damage = pstats.get("thorns_damage", 0)
    _bullet_bounces = pstats.get("bullet_bounces", 0)
    _shield_level = pstats.get("shield_level", 0)
    _shield_recharge_time = pstats.get("shield_recharge", 18) * FPS  # in frames
    _shield_timer = 0  # counts up to recharge time
    _shield_active = _shield_level > 0
    _saw_size_mult = pstats.get("saw_size_mult", 1.0)
    _fire_rate_mult = pstats.get("fire_rate_mult", 1.0)

    # Apply move speed bonus
    if pstats.get("move_speed_bonus", 0) > 0:
        player_obj.stats["speed"] += pstats["move_speed_bonus"]

    # Apply fire rate bonus
    if _fire_rate_mult < 1.0:
        player_obj.stats["fire_rate"] = max(3, round(player_obj.stats["fire_rate"] * _fire_rate_mult, 1))

    # Gold collected this run
    gold_this_run = 0

    # XP bonus chance
    xp_bonus_chance = pstats["xp_bonus"]

    # Spawn roombas
    roomba_count = pstats["roomba_count"]
    roomba_speed = pstats["roomba_speed"]
    roomba_range_mult = pstats.get("roomba_range", 1.0)
    for i in range(roomba_count):
        r = XPRoomba(player_obj, i, max(1, roomba_count), 50, roomba_speed, roomba_range_mult)
        all_sprites.add(r)
        roombas_grp.add(r)

    # Spawn saws
    saw_count = pstats["saw_count"]
    saw_damage = pstats["saw_damage"]
    saw_speed = pstats["saw_speed"]
    for i in range(saw_count):
        s = SpinningSaw(player_obj, i, max(1, saw_count), saw_damage, saw_speed, _saw_size_mult)
        all_sprites.add(s)
        saws_grp.add(s)

    # Wave state
    current_wave = max(1, starting_wave)
    enemies_to_spawn = 0
    enemies_spawned = 0
    spawn_timer = 0
    BASE_SPAWN_DELAY = 20  # Starting spawn delay (frames) — was 30
    wave_active = False
    wave_cooldown = 0
    WAVE_COOLDOWN_TIME = 120
    wave_banner_timer = 0
    fire_cooldown = 0

    # Party XP (shared in multiplayer, only tracked on host)
    party_level = 1
    party_xp = 0
    party_xp_to_next = 8
    upgrade_pending_players = set()  # Set of player IDs waiting to pick upgrades

    # Helper function for enemies to find nearest player
    def make_nearest_player_finder(enemy):
        """Create a closure that finds nearest player to this specific enemy."""

        def find_nearest():
            # Always check all available players
            min_dist = float('inf')
            target_x, target_y = player_obj.rect.centerx, player_obj.rect.centery

            # Check local player (if alive)
            if not spectating:
                dx = player_obj.rect.centerx - enemy.rect.centerx
                dy = player_obj.rect.centery - enemy.rect.centery
                dist = math.hypot(dx, dy)
                if dist < min_dist:
                    min_dist = dist
                    target_x, target_y = player_obj.rect.centerx, player_obj.rect.centery

            # Check remote players (multiplayer)
            if gs.net_mode and gs.remote_players:
                for ghost in gs.remote_players.values():
                    # Skip dead players
                    if hasattr(ghost, 'is_dead') and ghost.is_dead:
                        continue
                    dx = ghost.rect.centerx - enemy.rect.centerx
                    dy = ghost.rect.centery - enemy.rect.centery
                    dist = math.hypot(dx, dy)
                    if dist < min_dist:
                        min_dist = dist
                        target_x, target_y = ghost.rect.centerx, ghost.rect.centery

            return (target_x, target_y)

        return find_nearest

    def net_shake(frames, intensity):
        """Trigger shake locally and broadcast to multiplayer."""
        trigger_shake(frames, intensity)
        if gs.net_mode == "host" and gs.net_host:
            gs.net_host.broadcast(MSG_SHAKE, {"f": frames, "i": intensity})

    def start_wave(wave_num):
        nonlocal enemies_to_spawn, enemies_spawned, wave_active, spawn_timer, wave_banner_timer
        base_count = 5 + (wave_num * 3)
        # +15% enemies every 10 levels
        scale = 1.0 + (wave_num // 10) * 0.15
        enemies_to_spawn = int(base_count * scale)
        enemies_spawned = 0
        wave_active = True
        spawn_timer = 0
        wave_banner_timer = 120
        net_shake(8, 5)
        vfx.wave_start_effect(settings_module.SCREEN_WIDTH, settings_module.SCREEN_HEIGHT)
        if wave_num % 10 == 0:
            sounds.play_boss_spawn()
            net_shake(12, 8)
        else:
            sounds.play_wave_start()
        boss = None
        if wave_num % 10 == 0:
            boss = create_boss_for_wave(player_obj, wave_num)
            boss._net_id = id(boss)
            boss.get_nearest_player_pos = make_nearest_player_finder(boss)  # Enable smart targeting
            all_sprites.add(boss)
            enemies_grp.add(boss)
            # Broadcast boss spawn to clients
            if gs.net_mode == "host" and gs.net_host:
                gs.net_host.broadcast(MSG_ENEMY_SPAWN, {
                    "enemy_id": boss._net_id,
                    "x": boss.rect.x,
                    "y": boss.rect.y,
                    "is_boss": True,
                    "wave": wave_num,
                    "max_health": boss.max_health,
                    "health": boss.health,
                })
        # Host broadcasts new wave to clients immediately
        if gs.net_mode == "host" and gs.net_host:
            gs.net_host.broadcast(MSG_WAVE_START, {
                "wave": wave_num,
                "active": True,
                "enemies_remaining": enemies_to_spawn,
            })

    # ── Auto-level for wave skip: give player upgrades matching the wave
    if starting_wave > 1:
        auto_levels = starting_wave  # ~1 level per wave
        for lv in range(auto_levels):
            player_obj.level += 1
            player_obj.current_xp = 0
            player_obj.xp_to_next_level = int(8 + player_obj.level ** 1.5 * 3)
            # Every 5th level = big upgrade, otherwise normal
            if (lv + 1) % 5 == 0:
                pick = random.choice(BIG_UPGRADE_POOL)
            else:
                pick = random.choice(UPGRADE_POOL)
            player_obj.apply_upgrade(pick["key"])
        # Heal to full after auto-leveling
        player_obj.current_health = player_obj.stats["max_health"]

    start_wave(current_wave)

    # Dash trail visual: list of (pos, alpha, frame) tuples
    dash_trail = []
    # Spectate state (multiplayer only)
    spectating = False
    spectate_target_id = None

    # Beam weapon state (Arcanist)
    active_beam = None  # {"start": (x,y), "end": (x,y), "timer": int, "width": float, "dmg": int}
    beam_hit_this_frame = set()  # Track enemies already hit by beam this frame

    while True:
        # Delta time: real ms since last frame, normalized to 60fps baseline
        raw_dt = clock.get_time()  # ms since last tick
        dt = max(0.016, min(4.0, raw_dt / 16.667))  # 16.667ms = 60fps, clamp to prevent insanity

        # Clamp dt to 0 during pause — prevents catch-up
        if gs.upgrade_paused_by:
            dt = 0.0

        # Store dt globally so all entities can access it
        settings_module.set_dt(dt)

        sw = settings_module.SCREEN_WIDTH
        sh = settings_module.SCREEN_HEIGHT
        surf = display_mgr.get_screen()

        # ---- EVENTS ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if not spectating:
                        # In multiplayer, pause everyone while settings are open
                        if gs.net_mode == "host" and gs.net_host:
                            gs.upgrade_paused_by = {"player_name": gs.local_username, "level": "settings"}
                            gs.net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name": gs.local_username, "level": "settings"})
                        elif gs.net_mode == "client" and gs.net_client:
                            gs.net_client.send(MSG_UPGRADE_PAUSE, {"player_name": gs.local_username, "level": "settings"})
                        action = show_pause_menu()
                        # Reset clock to prevent dt catch-up from menu time
                        clock.tick(settings_module.FPS or 0)
                        # Unpause on close
                        if gs.net_mode == "host" and gs.net_host:
                            gs.upgrade_paused_by = None
                            gs.net_host.broadcast(MSG_UPGRADE_RESUME, {})
                        elif gs.net_mode == "client" and gs.net_client:
                            gs.net_client.send(MSG_UPGRADE_RESUME, {})
                            gs.upgrade_paused_by = None
                        if action == "main_menu":
                            return "main_menu"
                if event.key == pygame.K_SPACE and not spectating:
                    pass  # Dash is now handled via hold in player update()
                # Spectate: cycle through remote players with arrow keys
                if spectating and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    ids = list(gs.remote_players.keys())
                    if ids:
                        if spectate_target_id not in ids:
                            spectate_target_id = ids[0]
                        else:
                            idx = ids.index(spectate_target_id)
                            if event.key == pygame.K_RIGHT:
                                spectate_target_id = ids[(idx + 1) % len(ids)]
                            else:
                                spectate_target_id = ids[(idx - 1) % len(ids)]

        # ---- WAVE SPAWNING ----
        # Clients don't spawn enemies autonomously — the host controls wave state
        # and broadcasts MSG_WAVE_START. Clients receive that and call start_wave().
        # PAUSE if anyone is choosing an upgrade

        if gs.upgrade_paused_by:
            pass  # Game paused for upgrades/settings

        if not gs.upgrade_paused_by:
            if gs.net_mode != "client":
                if wave_active:
                    if enemies_spawned < enemies_to_spawn:
                        spawn_timer += dt
                        # Spawn faster at higher waves
                        spawn_delay = max(2, int(BASE_SPAWN_DELAY - current_wave * 0.5))
                        if spawn_timer >= spawn_delay:
                            spawn_timer = 0

                            # Choose enemy type based on wave number
                            enemy_type = "basic"
                            w = current_wave

                            if w >= 100:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech","wraith","charger","mimic","orbiter","sniper","parasite"],
                                    weights=[5,4,4,3,4,4,3,8,3,3,5,4,5,4,4,5,4,5,5,4])[0]
                            elif w >= 95:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech","wraith","charger","mimic","orbiter","sniper"],
                                    weights=[5,4,5,4,4,5,4,8,4,4,5,4,5,4,5,6,5,5,6])[0]
                            elif w >= 90:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech","wraith","charger","mimic","orbiter"],
                                    weights=[6,5,5,4,5,5,4,9,4,4,6,5,6,5,5,6,5,7])[0]
                            elif w >= 85:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech","wraith","charger","mimic"],
                                    weights=[7,5,5,4,5,5,4,10,4,5,6,5,6,5,5,7,6])[0]
                            elif w >= 80:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech","wraith","charger"],
                                    weights=[7,6,6,4,5,6,4,10,5,5,7,5,7,5,5,8])[0]
                            elif w >= 75:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech","wraith"],
                                    weights=[8,6,6,5,6,6,5,10,5,5,8,6,7,6,6])[0]
                            elif w >= 70:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser","leech"],
                                    weights=[10,7,7,5,7,7,5,12,5,5,8,7,8,7])[0]
                            elif w >= 65:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer","laser"],
                                    weights=[10,8,7,6,8,7,6,12,6,6,8,7,9])[0]
                            elif w >= 60:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral","minelayer"],
                                    weights=[12,8,8,6,8,8,6,14,6,6,9,9])[0]
                            elif w >= 55:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro",
                                     "spiral"],
                                    weights=[13,9,9,7,9,9,7,14,7,6,10])[0]
                            elif w >= 50:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex","necro"],
                                    weights=[15, 10, 10, 8, 10, 10, 8, 15, 7, 7])[0]
                            elif w >= 45:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm","vortex"],
                                    weights=[18, 12, 10, 8, 12, 10, 8, 15, 7])[0]
                            elif w >= 40:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield","swarm"],
                                    weights=[20, 12, 10, 10, 12, 10, 8, 18])[0]
                            elif w >= 35:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport","shield"],
                                    weights=[25, 15, 10, 10, 15, 12, 13])[0]
                            elif w >= 30:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag","teleport"],
                                    weights=[30, 15, 12, 12, 15, 16])[0]
                            elif w >= 25:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter","zigzag"],
                                    weights=[40, 20, 15, 15, 10])[0]
                            elif w >= 20:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank","splitter"],
                                    weights=[50, 20, 15, 15])[0]
                            elif w >= 15:
                                enemy_type = random.choices(
                                    ["basic","arrow","tank"],
                                    weights=[60, 25, 15])[0]
                            elif w >= 10:
                                enemy_type = random.choices(
                                    ["basic","arrow"],
                                    weights=[70, 30])[0]

                            # Boss-themed minions: 20% chance to spawn after their boss wave
                            boss_minion_map = {
                                11: "bossminion", 21: "hydraspawn", 31: "phantomwisp",
                                41: "fortressguard", 51: "stormwisp", 61: "voidling",
                                71: "infernoimp", 81: "frostshard", 91: "shadowshade", 101: "omegadrone"
                            }
                            for threshold, minion_type in boss_minion_map.items():
                                if w >= threshold and random.random() < 0.18:
                                    enemy_type = minion_type
                                    break

                            # Create enemy based on type
                            enemy_creators = {
                                "arrow": lambda: ArrowEnemy(player_obj, current_wave),
                                "tank": lambda: TankEnemy(player_obj, current_wave),
                                "splitter": lambda: SplitterEnemy(player_obj, current_wave, 'large'),
                                "zigzag": lambda: ZigZagEnemy(player_obj, current_wave),
                                "teleport": lambda: TeleportEnemy(player_obj, current_wave),
                                "shield": lambda: ShieldEnemy(player_obj, current_wave),
                                "swarm": lambda: SwarmEnemy(player_obj, current_wave),
                                "vortex": lambda: VortexEnemy(player_obj, current_wave),
                                "necro": lambda: NecroEnemy(player_obj, current_wave),
                                "spiral": lambda: SpiralEnemy(player_obj, current_wave),
                                "minelayer": lambda: MineLayerEnemy(player_obj, current_wave),
                                "laser": lambda: LaserDrone(player_obj, current_wave),
                                "leech": lambda: LeechPriest(player_obj, current_wave),
                                "wraith": lambda: PhaseWraith(player_obj, current_wave),
                                "charger": lambda: ChargerBull(player_obj, current_wave),
                                "mimic": lambda: MimicEnemy(player_obj, current_wave),
                                "orbiter": lambda: OrbiterEnemy(player_obj, current_wave),
                                "sniper": lambda: SniperEnemy(player_obj, current_wave),
                                "parasite": lambda: ParasiteEnemy(player_obj, current_wave),
                                # Boss-themed minions
                                "bossminion": lambda: BossMinion(player_obj, current_wave),
                                "hydraspawn": lambda: HydraSpawnling(player_obj, current_wave),
                                "phantomwisp": lambda: PhantomWisp(player_obj, current_wave),
                                "fortressguard": lambda: FortressGuard(player_obj, current_wave),
                                "stormwisp": lambda: StormWisp(player_obj, current_wave),
                                "voidling": lambda: VoidLing(player_obj, current_wave),
                                "infernoimp": lambda: InfernoImp(player_obj, current_wave),
                                "frostshard": lambda: FrostShard(player_obj, current_wave),
                                "shadowshade": lambda: ShadowShade(player_obj, current_wave),
                                "omegadrone": lambda: OmegaDrone(player_obj, current_wave),
                            }
                            if enemy_type == "swarm":
                                # Spawn a cluster of 3-5 swarm enemies
                                _tier = current_wave // 10
                                for _ in range(random.randint(3, 5)):
                                    se = SwarmEnemy(player_obj, current_wave)
                                    se._net_id = id(se)
                                    se.get_nearest_player_pos = make_nearest_player_finder(se)
                                    if _tier > 0:
                                        se.max_health = int(se.max_health * (1.0 + _tier * 0.5))
                                        se.health = se.max_health
                                        se.speed *= (1.0 + _tier * 0.12)
                                        se.damage = int(se.damage * (1.0 + _tier * 0.3))
                                    all_sprites.add(se); enemies_grp.add(se)
                                    if gs.net_mode == "host" and gs.net_host:
                                        gs.net_host.broadcast(MSG_ENEMY_SPAWN, {
                                            "enemy_id": se._net_id, "x": se.rect.x, "y": se.rect.y,
                                            "is_boss": False, "wave": current_wave,
                                            "max_health": se.max_health, "health": se.health,
                                            "enemy_type": "swarm", "speed": se.speed,
                                        })
                                e = None  # Already spawned
                            elif enemy_type in enemy_creators:
                                e = enemy_creators[enemy_type]()
                            else:
                                e = Enemy(player_obj, current_wave)

                            if e is not None:
                                e._net_id = id(e)
                                e.get_nearest_player_pos = make_nearest_player_finder(e)
                                # Scale enemy stats every 10 waves
                                _tier = current_wave // 10
                                if _tier > 0:
                                    e.max_health = int(e.max_health * (1.0 + _tier * 0.5))
                                    e.health = e.max_health
                                    e.speed *= (1.0 + _tier * 0.12)
                                    e.damage = int(e.damage * (1.0 + _tier * 0.3))
                                all_sprites.add(e)
                                enemies_grp.add(e)
                            enemies_spawned += 1
                            # Broadcast enemy spawn to clients
                            if e is not None and gs.net_mode == "host" and gs.net_host:
                                gs.net_host.broadcast(MSG_ENEMY_SPAWN, {
                                    "enemy_id": e._net_id,
                                    "x": e.rect.x,
                                    "y": e.rect.y,
                                    "is_boss": False,
                                    "wave": current_wave,
                                    "max_health": e.max_health,
                                    "health": e.health,
                                    "enemy_type": enemy_type,
                                    "speed": e.speed,
                                })
                    else:
                        if len(enemies_grp) == 0:
                            wave_active = False
                            wave_cooldown = WAVE_COOLDOWN_TIME
                            # Tell clients the wave is over
                            if gs.net_mode == "host" and gs.net_host:
                                gs.net_host.broadcast(MSG_WAVE_COMPLETE, {"wave": current_wave})
                else:
                    wave_cooldown -= dt
                    if wave_cooldown <= 0:
                        current_wave += 1
                        start_wave(current_wave)
            # Client: just let existing enemies run; wave advancement comes from host

            # ---- UPDATE ----
            if spectating:
                enemies_grp.update()
                bullets_grp.update()
                gems_grp.update()
                health_orbs_grp.update()
                enemy_projectiles_grp.update()
            else:
                all_sprites.update()

            # ── XP Orb Condensing (every ~1.5 seconds) ──
            _condense_timer = getattr(run_game, '_condense_timer', 0) + 1
            run_game._condense_timer = _condense_timer
            if _condense_timer >= 90 and len(gems_grp) > 30:
                run_game._condense_timer = 0
                gem_list = list(gems_grp)
                used = set()
                for i, g1 in enumerate(gem_list):
                    if id(g1) in used:
                        continue
                    cluster = [g1]
                    cx, cy = g1.rect.centerx, g1.rect.centery
                    for j in range(i + 1, len(gem_list)):
                        g2 = gem_list[j]
                        if id(g2) in used:
                            continue
                        if abs(g2.rect.centerx - cx) < 60 and abs(g2.rect.centery - cy) < 60:
                            cluster.append(g2)
                    if len(cluster) >= 8:
                        total_xp = sum(getattr(g, 'xp_value', 1) for g in cluster)
                        avg_x = sum(g.rect.centerx for g in cluster) // len(cluster)
                        avg_y = sum(g.rect.centery for g in cluster) // len(cluster)
                        for g in cluster:
                            used.add(id(g))
                            g.kill()
                        mega = ExpGem((avg_x, avg_y), xp_value=total_xp)
                        all_sprites.add(mega)
                        gems_grp.add(mega)

            # ── Despawn old health orbs and gold (20s) ──
            if _condense_timer == 45:  # Offset from gem condense
                _now_ms = pygame.time.get_ticks()
                for orb in list(health_orbs_grp):
                    if _now_ms - getattr(orb, 'spawn_time', _now_ms) > 20000:
                        orb.kill()
                for coin in list(gold_grp):
                    if _now_ms - getattr(coin, 'spawn_time', _now_ms) > 20000:
                        coin.kill()

            # Reset frost slow each frame
            player_obj._frost_slowed = False

            # Enemy & Boss abilities (run regardless of spectating)
            for enemy in list(enemies_grp):
                if hasattr(enemy, 'get_nearest_player_pos') and enemy.get_nearest_player_pos:
                    etx, ety = enemy.get_nearest_player_pos()
                else:
                    etx, ety = player_obj.rect.centerx, player_obj.rect.centery

                # Tank / Boss aimed shot
                if hasattr(enemy, 'can_shoot') and enemy.can_shoot():
                    if isinstance(enemy, (PhantomBoss,)):
                        cnt = getattr(enemy, 'spread_count', 5)
                        base_a = math.atan2(ety - enemy.rect.centery, etx - enemy.rect.centerx)
                        for i in range(cnt):
                            a = base_a + (i - cnt // 2) * 0.3
                            tx = enemy.rect.centerx + int(math.cos(a) * 300)
                            ty = enemy.rect.centery + int(math.sin(a) * 300)
                            p = EnemyProjectile(enemy.rect.center, (tx, ty))
                            all_sprites.add(p); enemy_projectiles_grp.add(p)
                        enemy.shoot()
                    elif isinstance(enemy, (FrostBoss,)):
                        cnt = getattr(enemy, 'spread_count', 8)
                        base_a = math.atan2(ety - enemy.rect.centery, etx - enemy.rect.centerx)
                        for i in range(cnt):
                            a = base_a + (i - cnt // 2) * 0.25
                            tx = enemy.rect.centerx + int(math.cos(a) * 300)
                            ty = enemy.rect.centery + int(math.sin(a) * 300)
                            p = EnemyProjectile(enemy.rect.center, (tx, ty), speed=3)
                            all_sprites.add(p); enemy_projectiles_grp.add(p)
                        enemy.shoot()
                    else:
                        p = EnemyProjectile(enemy.rect.center, (etx, ety))
                        all_sprites.add(p); enemy_projectiles_grp.add(p)
                        enemy.shoot(etx, ety)

                # Ring of projectiles
                if hasattr(enemy, 'can_ring') and enemy.can_ring():
                    cnt = getattr(enemy, 'ring_count', 12)
                    for i in range(cnt):
                        a = (i / cnt) * math.pi * 2
                        tx = enemy.rect.centerx + int(math.cos(a) * 400)
                        ty = enemy.rect.centery + int(math.sin(a) * 400)
                        p = EnemyProjectile(enemy.rect.center, (tx, ty), speed=3)
                        all_sprites.add(p); enemy_projectiles_grp.add(p)

                # Minion spawning
                if hasattr(enemy, 'can_spawn_minion') and enemy.can_spawn_minion():
                    for _ in range(random.randint(2, 4)):
                        m = Enemy(player_obj, current_wave)
                        m.rect.centerx = enemy.rect.centerx + random.randint(-60, 60)
                        m.rect.centery = enemy.rect.centery + random.randint(-60, 60)
                        m._net_id = id(m)
                        m.get_nearest_player_pos = make_nearest_player_finder(m)
                        all_sprites.add(m); enemies_grp.add(m)

                # Necro summoning
                if isinstance(enemy, NecroEnemy) and enemy.can_summon():
                    m = Enemy(player_obj, current_wave)
                    m.rect.center = (enemy.rect.centerx + random.randint(-40, 40),
                                     enemy.rect.centery + random.randint(-40, 40))
                    m._net_id = id(m)
                    m.get_nearest_player_pos = make_nearest_player_finder(m)
                    all_sprites.add(m); enemies_grp.add(m)

                # Shadow clone
                if isinstance(enemy, ShadowBoss) and hasattr(enemy, 'can_clone') and enemy.can_clone():
                    clone_count = sum(1 for e in enemies_grp if isinstance(e, ShadowBoss) and getattr(e, 'is_clone', False))
                    if clone_count < enemy.max_clones:
                        c = ShadowBoss(player_obj, current_wave, is_clone=True)
                        c.rect.center = (enemy.rect.centerx + random.randint(-100, 100),
                                         enemy.rect.centery + random.randint(-100, 100))
                        c._net_id = id(c)
                        c.get_nearest_player_pos = make_nearest_player_finder(c)
                        all_sprites.add(c); enemies_grp.add(c)

                # Vortex pull
                if hasattr(enemy, 'pull_radius') and not spectating:
                    dx_v = enemy.rect.centerx - player_obj.rect.centerx
                    dy_v = enemy.rect.centery - player_obj.rect.centery
                    dist_v = math.hypot(dx_v, dy_v)
                    if 0 < dist_v < enemy.pull_radius and not player_obj.dash_invincible:
                        pull = getattr(enemy, 'pull_strength', 1.5)
                        player_obj.rect.x += int((dx_v / dist_v) * pull)
                        player_obj.rect.y += int((dy_v / dist_v) * pull)

                # Frost slow
                if isinstance(enemy, FrostBoss) and not spectating:
                    dist_f = math.hypot(enemy.rect.centerx - player_obj.rect.centerx,
                                        enemy.rect.centery - player_obj.rect.centery)
                    if dist_f < enemy.slow_radius and not player_obj.dash_invincible:
                        player_obj._frost_slowed = True

                # ── Spiral shooter
                if isinstance(enemy, SpiralEnemy) and enemy.can_shoot():
                    p = EnemyProjectile(enemy.rect.center, (etx, ety), speed=4)
                    all_sprites.add(p); enemy_projectiles_grp.add(p)

                # ── Mine layer
                if isinstance(enemy, MineLayerEnemy) and enemy.can_lay_mine():
                    mine = ProximityMine(enemy.rect.center, damage=12 + current_wave // 5)
                    all_sprites.add(mine); mines_grp.add(mine)

                # ── Laser drone beam
                if isinstance(enemy, LaserDrone) and enemy.state == "firing":
                    # Draw beam and deal damage
                    dx_b = enemy.beam_target[0] - enemy.rect.centerx
                    dy_b = enemy.beam_target[1] - enemy.rect.centery
                    d_b = math.hypot(dx_b, dy_b)
                    if d_b > 0 and not spectating:
                        # Extend beam beyond target
                        end_x = enemy.rect.centerx + int((dx_b / d_b) * 600)
                        end_y = enemy.rect.centery + int((dy_b / d_b) * 600)
                        # Check if player is near the beam line
                        # Point-to-line distance
                        px_r = player_obj.rect.centerx - enemy.rect.centerx
                        py_r = player_obj.rect.centery - enemy.rect.centery
                        beam_len = math.hypot(end_x - enemy.rect.centerx, end_y - enemy.rect.centery)
                        if beam_len > 0:
                            # Project player onto beam
                            bx_n = (end_x - enemy.rect.centerx) / beam_len
                            by_n = (end_y - enemy.rect.centery) / beam_len
                            proj = px_r * bx_n + py_r * by_n
                            if 0 < proj < beam_len:
                                perp_dist = abs(px_r * by_n - py_r * bx_n)
                                if perp_dist < 20 and not player_obj.dash_invincible:
                                    now_b = pygame.time.get_ticks()
                                    if now_b - player_obj.last_hit > 500:
                                        beam_dmg = 8 + current_wave // 3
                                        if hasattr(player_obj, 'armor') and player_obj.armor > 0:
                                            beam_dmg = max(1, int(beam_dmg * (1.0 - player_obj.armor)))
                                        player_obj.current_health -= beam_dmg
                                        player_obj.last_hit = now_b
                                        player_obj.set_hurt(True)
                                        sounds.play_hurt()

                # ── Leech Priest heals nearby enemies
                if isinstance(enemy, LeechPriest) and enemy.can_heal():
                    for other in enemies_grp:
                        if other is not enemy and not isinstance(other, LeechPriest):
                            dist_h = math.hypot(other.rect.centerx - enemy.rect.centerx,
                                                other.rect.centery - enemy.rect.centery)
                            if dist_h < enemy.heal_radius:
                                other.health = min(other.max_health, other.health + enemy.heal_amount)

                # ── Parasite seeks and latches onto host enemies
                if isinstance(enemy, ParasiteEnemy) and not enemy.attached:
                    host = enemy.find_host(enemies_grp)
                    if host:
                        dist_p = math.hypot(host.rect.centerx - enemy.rect.centerx,
                                            host.rect.centery - enemy.rect.centery)
                        if dist_p < 20:
                            enemy.attach(host)
                        else:
                            # Chase the host instead of the player
                            dx_p = host.rect.centerx - enemy.rect.centerx
                            dy_p = host.rect.centery - enemy.rect.centery
                            d_p = math.hypot(dx_p, dy_p) or 1
                            enemy.rect.x += (dx_p / d_p) * enemy.speed
                            enemy.rect.y += (dy_p / d_p) * enemy.speed

                # ── Sniper fires fast accurate shot
                if isinstance(enemy, SniperEnemy) and enemy.can_shoot():
                    p = EnemyProjectile(enemy.rect.center, enemy.aim_target, speed=8)
                    all_sprites.add(p); enemy_projectiles_grp.add(p)

                # ══ Boss-themed minion mechanics ══

                # BossMinion shoots slow projectiles
                if isinstance(enemy, BossMinion) and enemy.can_shoot():
                    p = EnemyProjectile(enemy.rect.center, (etx, ety), speed=3)
                    all_sprites.add(p); enemy_projectiles_grp.add(p)

                # PhantomWisp shoots + teleports (update handles tp)
                if isinstance(enemy, PhantomWisp) and enemy.can_shoot():
                    p = EnemyProjectile(enemy.rect.center, (etx, ety), speed=3)
                    all_sprites.add(p); enemy_projectiles_grp.add(p)

                # StormWisp fires cross pattern
                if isinstance(enemy, StormWisp) and enemy.can_ring():
                    for i in range(enemy.ring_count):
                        a = (i / enemy.ring_count) * math.pi * 2
                        tx2 = enemy.rect.centerx + int(math.cos(a) * 300)
                        ty2 = enemy.rect.centery + int(math.sin(a) * 300)
                        p = EnemyProjectile(enemy.rect.center, (tx2, ty2), speed=3)
                        all_sprites.add(p); enemy_projectiles_grp.add(p)

                # VoidLing pulls player gently
                if isinstance(enemy, VoidLing) and not spectating:
                    dx_v2 = enemy.rect.centerx - player_obj.rect.centerx
                    dy_v2 = enemy.rect.centery - player_obj.rect.centery
                    dist_v2 = math.hypot(dx_v2, dy_v2)
                    if 0 < dist_v2 < enemy.pull_radius and not player_obj.dash_invincible:
                        player_obj.rect.x += int((dx_v2 / dist_v2) * enemy.pull_strength)
                        player_obj.rect.y += int((dy_v2 / dist_v2) * enemy.pull_strength)

                # InfernoImp shoots fireballs
                if isinstance(enemy, InfernoImp) and enemy.can_shoot():
                    p = EnemyProjectile(enemy.rect.center, (etx, ety), speed=5)
                    all_sprites.add(p); enemy_projectiles_grp.add(p)

                # FrostShard slows player when nearby
                if isinstance(enemy, FrostShard) and not spectating:
                    dist_fs = math.hypot(enemy.rect.centerx - player_obj.rect.centerx,
                                         enemy.rect.centery - player_obj.rect.centery)
                    if dist_fs < enemy.slow_radius and not player_obj.dash_invincible:
                        player_obj._frost_slowed = True

                # OmegaDrone shoots + pulls
                if isinstance(enemy, OmegaDrone) and enemy.can_shoot():
                    p = EnemyProjectile(enemy.rect.center, (etx, ety), speed=5)
                    all_sprites.add(p); enemy_projectiles_grp.add(p)
                if isinstance(enemy, OmegaDrone) and not spectating:
                    dx_od = enemy.rect.centerx - player_obj.rect.centerx
                    dy_od = enemy.rect.centery - player_obj.rect.centery
                    dist_od = math.hypot(dx_od, dy_od)
                    if 0 < dist_od < enemy.pull_radius and not player_obj.dash_invincible:
                        player_obj.rect.x += int((dx_od / dist_od) * enemy.pull_strength)
                        player_obj.rect.y += int((dy_od / dist_od) * enemy.pull_strength)

            # Apply frost slow to player speed
            if getattr(player_obj, '_frost_slowed', False) and not spectating:
                player_obj.stats["speed"] = max(1, int(player_obj.stats["speed"] * 0.5))

            # ── Proximity mines: update and check player proximity
            mines_grp.update()
            if not spectating and not player_obj.dash_invincible:
                for mine in list(mines_grp):
                    if mine.arm_timer <= 0:
                        dist_m = math.hypot(mine.rect.centerx - player_obj.rect.centerx,
                                            mine.rect.centery - player_obj.rect.centery)
                        if dist_m < mine.proximity:
                            # BOOM
                            if hasattr(player_obj, 'armor') and player_obj.armor > 0:
                                mdmg = max(1, int(mine.damage * (1.0 - player_obj.armor)))
                            else:
                                mdmg = mine.damage
                            # Dodge check
                            dodged = _dodge_chance > 0 and random.random() < _dodge_chance
                            if not dodged:
                                if _shield_active:
                                    _shield_active = False; _shield_timer = 0
                                else:
                                    player_obj.current_health -= mdmg
                                    player_obj.set_hurt(True)
                                    sounds.play_hurt()
                            trigger_shake(6, 4)
                            mine.kill()

            # Detect dash start for sound + ZAP effect
            if not spectating and player_obj.dash_duration == player_obj.dash_duration_max:
                if not getattr(player_obj, '_dash_sound_played', False):
                    sounds.play_dash()
                    trigger_shake(5, 4)
                    player_obj._dash_start_pos = player_obj.rect.center
                    player_obj._dash_sound_played = True
            elif player_obj.dash_duration == 0:
                if getattr(player_obj, '_dash_sound_played', False):
                    # Dash just ended — fire the zap!
                    start_pos = getattr(player_obj, '_dash_start_pos', None)
                    if start_pos:
                        nc = player_obj.NEON_GLOW_COLOR if hasattr(player_obj, 'NEON_GLOW_COLOR') else (100,200,255)
                        vfx.dash_zap(start_pos, player_obj.rect.center, nc)
                        trigger_shake(6, 5)
                player_obj._dash_sound_played = False

            apply_magnet(player_obj, gems_grp)
            apply_gold_magnet(player_obj, gold_grp)
            apply_magnet(player_obj, health_orbs_grp)  # Magnet picks up health orbs too

            # ---- AUTO-FIRE ----
            # Always tick down cooldown first
            if fire_cooldown > 0:
                fire_cooldown -= dt

            if fire_cooldown <= 0 and not spectating and len(bullets_grp) < 500:
                # Get the SINGLE nearest enemy
                targets = get_nearest_enemies(player_obj, enemies_grp, 1)

                if targets:
                    nearest_enemy = targets[0]
                    weapon = player_obj.get_weapon_type()
                    multishot_count = min(10, player_obj.stats["multishot"])  # Hard cap at 10

                    # Diminishing damage for extra multishot bullets
                    # First 3 bullets: full damage. 4-6: 70%. 7-10: 50%
                    def _shot_dmg_mult(shot_idx):
                        if shot_idx < 3: return 1.0
                        if shot_idx < 6: return 0.7
                        return 0.5

                    # Calculate base angle to nearest enemy
                    dx = nearest_enemy.rect.centerx - player_obj.rect.centerx
                    dy = nearest_enemy.rect.centery - player_obj.rect.centery
                    base_angle = math.atan2(dy, dx)

                    # Cone spread angle (in radians) — reduced by accuracy upgrades
                    if multishot_count == 1:
                        cone_spread = 0  # No spread for single shot
                    else:
                        base_cone = 0.3  # ~17 degrees total spread
                        accuracy_mult = max(0.05, 1.0 / player_obj.stats.get("accuracy", 1.0))
                        cone_spread = base_cone * accuracy_mult

                    # Fire multishot bullets in a cone toward nearest enemy
                    for i in range(multishot_count):
                        _dmg_mult = _shot_dmg_mult(i)
                        # Calculate angle offset for this bullet in the cone
                        if multishot_count == 1:
                            angle_offset = 0
                        else:
                            # Spread bullets evenly across the cone
                            t = i / (multishot_count - 1)  # 0.0 to 1.0
                            angle_offset = (t - 0.5) * cone_spread * 2  # Center the spread

                        # Calculate target position with cone spread
                        bullet_angle = base_angle + angle_offset
                        # Use a point along the angle instead of exact enemy position
                        spread_distance = 1000  # Far enough to go off-screen
                        target_x = player_obj.rect.centerx + math.cos(bullet_angle) * spread_distance
                        target_y = player_obj.rect.centery + math.sin(bullet_angle) * spread_distance

                        bsize = min(3.0, player_obj.stats.get("bullet_size", 1.0))
                        if weapon == "beam":
                            # Arcanist beam — chains to enemies!
                            beam_w = int(12 * bsize * (1 + (multishot_count - 1) * 0.4))
                            bounces = player_obj.stats.get("bullet_bounces", 0)

                            # Build beam segments: first goes to screen edge, bounces chain to enemies
                            segments = []
                            hit_enemies_chain = set()
                            bx, by = float(player_obj.rect.centerx), float(player_obj.rect.centery)
                            bdx = math.cos(bullet_angle)
                            bdy = math.sin(bullet_angle)

                            # First segment: straight line to screen edge (the initial shot)
                            beam_len = max(sw, sh) * 2
                            end_x = bx + bdx * beam_len
                            end_y = by + bdy * beam_len
                            segments.append(((int(bx), int(by)), (int(end_x), int(end_y))))

                            # Find enemies hit by first segment, pick closest as chain origin
                            first_hit = None
                            first_hit_dist = float('inf')
                            for enemy in enemies_grp:
                                if isinstance(enemy, PhaseWraith) and enemy.phased_out:
                                    continue
                                eex, eey = enemy.rect.centerx, enemy.rect.centery
                                px_r = eex - bx
                                py_r = eey - by
                                proj = px_r * bdx + py_r * bdy
                                if proj > 0:
                                    perp = abs(px_r * bdy - py_r * bdx)
                                    if perp < beam_w + enemy.rect.width // 2:
                                        if proj < first_hit_dist:
                                            first_hit_dist = proj
                                            first_hit = enemy

                            # Chain bounces: from each hit enemy, find nearest unhit enemy
                            if first_hit and bounces > 0:
                                hit_enemies_chain.add(id(first_hit))
                                chain_x = float(first_hit.rect.centerx)
                                chain_y = float(first_hit.rect.centery)

                                for _b in range(bounces):
                                    # Find nearest unhit enemy
                                    best = None
                                    best_dist = float('inf')
                                    for enemy in enemies_grp:
                                        if id(enemy) in hit_enemies_chain:
                                            continue
                                        if isinstance(enemy, PhaseWraith) and enemy.phased_out:
                                            continue
                                        dx = enemy.rect.centerx - chain_x
                                        dy = enemy.rect.centery - chain_y
                                        d = dx * dx + dy * dy
                                        if d < best_dist:
                                            best_dist = d
                                            best = enemy

                                    if best is None:
                                        break

                                    # Add chain segment
                                    tx, ty = best.rect.centerx, best.rect.centery
                                    segments.append(((int(chain_x), int(chain_y)), (int(tx), int(ty))))
                                    hit_enemies_chain.add(id(best))
                                    chain_x, chain_y = float(tx), float(ty)

                            active_beam = {
                                "segments": segments,
                                "timer": 15,
                                "width": beam_w,
                                "dmg": player_obj.stats["damage"],
                                "angle": bullet_angle,
                            }
                            # Damage all enemies along ALL beam segments
                            for enemy in list(enemies_grp):
                                if isinstance(enemy, PhaseWraith) and enemy.phased_out:
                                    continue
                                ex, ey = enemy.rect.centerx, enemy.rect.centery
                                hit = False
                                for seg_start, seg_end in segments:
                                    # Point-to-segment distance
                                    sx, sy = seg_start
                                    dx_s, dy_s = seg_end[0] - sx, seg_end[1] - sy
                                    seg_len_sq = dx_s*dx_s + dy_s*dy_s
                                    if seg_len_sq < 1: continue
                                    t_proj = max(0, min(1, ((ex-sx)*dx_s + (ey-sy)*dy_s) / seg_len_sq))
                                    closest_x = sx + t_proj * dx_s
                                    closest_y = sy + t_proj * dy_s
                                    dist = math.hypot(ex - closest_x, ey - closest_y)
                                    if dist < beam_w + enemy.rect.width // 2:
                                        hit = True
                                        break
                                if hit:
                                    dmg = player_obj.stats["damage"]
                                    is_crit = False
                                    if hasattr(player_obj, 'crit_chance') and player_obj.crit_chance > 0:
                                        if random.random() < player_obj.crit_chance:
                                            dmg = int(dmg * 2); is_crit = True
                                    dead = enemy.take_damage(dmg)
                                    vfx.hit_spark(enemy.rect.centerx, enemy.rect.centery, (255, 120, 120))
                                    vfx.damage_number(enemy.rect.centerx, enemy.rect.top, dmg, is_crit)
                                    if dead:
                                        sounds.play_hit()
                                        trigger_shake(6, 5)
                                        ec = getattr(enemy, 'color', (255, 80, 80))
                                        if getattr(enemy, 'is_boss', False):
                                            vfx.boss_death_burst(enemy.rect.centerx, enemy.rect.centery, ec)
                                            trigger_shake(15, 12)
                                        else:
                                            vfx.enemy_death_burst(enemy.rect.centerx, enemy.rect.centery, ec)
                                        if isinstance(enemy, SplitterEnemy) and enemy.size == 'large':
                                            for _ in range(2):
                                                mini = SplitterEnemy(player_obj, current_wave, 'medium')
                                                mini.rect.center = enemy.rect.center
                                                mini.get_nearest_player_pos = make_nearest_player_finder(mini)
                                                all_sprites.add(mini); enemies_grp.add(mini)
                                        elif isinstance(enemy, SplitterEnemy) and enemy.size == 'medium':
                                            for _ in range(2):
                                                tiny = SplitterEnemy(player_obj, current_wave, 'small')
                                                tiny.rect.center = enemy.rect.center
                                                tiny.get_nearest_player_pos = make_nearest_player_finder(tiny)
                                                all_sprites.add(tiny); enemies_grp.add(tiny)
                                        if isinstance(enemy, HydraBoss) and getattr(enemy, 'is_hydra_parent', False):
                                            for _ in range(2):
                                                hm = HydraMini(player_obj, current_wave, enemy.rect.center)
                                                hm._net_id = id(hm)
                                                hm.get_nearest_player_pos = make_nearest_player_finder(hm)
                                                all_sprites.add(hm); enemies_grp.add(hm)
                                        if gs.net_mode == "client" and gs.net_client:
                                            gs.net_client.send(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                                        elif gs.net_mode == "host" and gs.net_host:
                                            gs.net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                                        handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                            # Only fire 1 beam regardless of multishot (multishot = width bonus)
                            # Broadcast beam to other players
                            if gs.net_mode in ("host", "client"):
                                beam_data = {
                                    "weapon": "beam",
                                    "segments": [[list(s), list(e)] for s, e in segments],
                                    "width": beam_w,
                                    "timer": 15,
                                }
                                if gs.net_mode == "host" and gs.net_host:
                                    gs.net_host.broadcast(MSG_BULLET_FIRE, beam_data)
                                elif gs.net_mode == "client" and gs.net_client:
                                    gs.net_client.send(MSG_BULLET_FIRE, beam_data)
                            break
                        elif weapon == "laser":
                            b = LaserBeam(player_obj.rect.center, (target_x, target_y),
                                          player_obj.stats["bullet_speed"], player_obj.stats["piercing"],
                                          size=bsize)
                        else:
                            b = Bullet(player_obj.rect.center, (target_x, target_y),
                                       player_obj.stats["bullet_speed"], player_obj.stats["piercing"],
                                       size=bsize, bounces=_bullet_bounces,
                                       color=player_obj.get_bullet_color())
                        if weapon != "beam":
                            b._dmg_mult = _dmg_mult
                            all_sprites.add(b)
                            bullets_grp.add(b)

                        # Broadcast bullet to all other players (beam synced separately above)
                        if weapon != "beam" and gs.net_mode in ("host", "client"):
                            bullet_data = {
                                "weapon": weapon,
                                "bx": player_obj.rect.centerx,
                                "by": player_obj.rect.centery,
                                "tx": target_x,
                                "ty": target_y,
                                "speed": player_obj.stats["bullet_speed"],
                                "piercing": player_obj.stats["piercing"],
                                "damage": player_obj.stats["damage"],
                                "size": bsize,
                                "color": list(player_obj.get_bullet_color()),
                            }
                            if gs.net_mode == "host" and gs.net_host:
                                gs.net_host.broadcast(MSG_BULLET_FIRE, bullet_data)
                            elif gs.net_mode == "client" and gs.net_client:
                                gs.net_client.send(MSG_BULLET_FIRE, bullet_data)

                    fire_cooldown = player_obj.stats["fire_rate"]
                    sounds.play_shoot()

            # ---- COLLISIONS ----

            # Bullets/Lasers vs Enemies
            # ── Orbiter orbs intercept bullets first
            for bullet in list(bullets_grp):
                blocked = False
                for enemy in enemies_grp:
                    if isinstance(enemy, OrbiterEnemy):
                        for ox, oy, idx in enemy.get_orb_positions():
                            if math.hypot(ox - bullet.rect.centerx, oy - bullet.rect.centery) < 14:
                                destroyed = enemy.damage_orb(idx, getattr(bullet, '_net_damage', None) or player_obj.stats["damage"])
                                bullet.kill(); blocked = True; break
                    if blocked: break
                if blocked: continue

            for bullet in list(bullets_grp):
                hit_list = pygame.sprite.spritecollide(bullet, enemies_grp, False)
                for enemy in hit_list:
                    if enemy in bullet.hit_enemies:
                        continue
                    # Phase wraiths are untouchable when phased out
                    if isinstance(enemy, PhaseWraith) and enemy.phased_out:
                        continue
                    # ShadowShade is untouchable when invisible
                    if isinstance(enemy, ShadowShade) and not enemy.visible:
                        continue
                    bullet.hit_enemies.append(enemy)
                    # Use network damage if this bullet came from a remote player
                    dmg = getattr(bullet, '_net_damage', None) or player_obj.stats["damage"]
                    # Diminishing returns for extra multishot bullets
                    dmg = max(1, int(dmg * getattr(bullet, '_dmg_mult', 1.0)))
                    # Crit chance
                    is_crit = False
                    if hasattr(player_obj, 'crit_chance') and player_obj.crit_chance > 0:
                        if not getattr(bullet, '_net_damage', None):  # Only local bullets crit
                            if random.random() < player_obj.crit_chance:
                                dmg = int(dmg * 2)
                                is_crit = True
                    dead = enemy.take_damage(dmg)
                    bullet.hits += 1
                    # VFX: hit spark + damage number
                    vfx.hit_spark(enemy.rect.centerx, enemy.rect.centery)
                    vfx.damage_number(enemy.rect.centerx, enemy.rect.top, dmg, is_crit)
                    if dead:
                        sounds.play_hit()
                        trigger_shake(6, 5)
                        # VFX: death burst
                        ec = getattr(enemy, 'color', (255, 80, 80))
                        if isinstance(enemy, Boss) or getattr(enemy, 'is_boss', False):
                            vfx.boss_death_burst(enemy.rect.centerx, enemy.rect.centery, ec)
                            trigger_shake(15, 12)
                        else:
                            vfx.enemy_death_burst(enemy.rect.centerx, enemy.rect.centery, ec)

                        # Splitter enemy splits into smaller enemies
                        if isinstance(enemy, SplitterEnemy) and enemy.size == 'large':
                            for _ in range(2):
                                mini = SplitterEnemy(player_obj, current_wave, 'medium')
                                mini.rect.center = enemy.rect.center
                                mini.get_nearest_player_pos = make_nearest_player_finder(mini)
                                all_sprites.add(mini); enemies_grp.add(mini)
                        elif isinstance(enemy, SplitterEnemy) and enemy.size == 'medium':
                            for _ in range(2):
                                tiny = SplitterEnemy(player_obj, current_wave, 'small')
                                tiny.rect.center = enemy.rect.center
                                tiny.get_nearest_player_pos = make_nearest_player_finder(tiny)
                                all_sprites.add(tiny); enemies_grp.add(tiny)

                        # Hydra boss splits into 2 mini-bosses
                        if isinstance(enemy, HydraBoss) and getattr(enemy, 'is_hydra_parent', False):
                            for _ in range(2):
                                hm = HydraMini(player_obj, current_wave, enemy.rect.center)
                                hm._net_id = id(hm)
                                hm.get_nearest_player_pos = make_nearest_player_finder(hm)
                                all_sprites.add(hm); enemies_grp.add(hm)

                        # HydraSpawnling splits into 2 tiny blobs
                        if isinstance(enemy, HydraSpawnling) and enemy.size == 'normal':
                            for _ in range(2):
                                tiny = HydraSpawnling(player_obj, current_wave, 'tiny')
                                tiny.rect.centerx = enemy.rect.centerx + random.randint(-15, 15)
                                tiny.rect.centery = enemy.rect.centery + random.randint(-15, 15)
                                tiny._net_id = id(tiny)
                                tiny.get_nearest_player_pos = make_nearest_player_finder(tiny)
                                all_sprites.add(tiny); enemies_grp.add(tiny)

                        # Report kill to host (clients) so host can sync gems/drops
                        if gs.net_mode == "client" and gs.net_client:
                            gs.net_client.send(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        elif gs.net_mode == "host" and gs.net_host:
                            # Host killed enemy directly — broadcast death
                            gs.net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                    if bullet.hits >= bullet.piercing:
                        bullet.kill()
                        break

            # Enemy projectiles vs Player
            if not spectating and not player_obj.dash_invincible:
                proj_hits = pygame.sprite.spritecollide(player_obj, enemy_projectiles_grp, True)
                for proj in proj_hits:
                    # Dodge check
                    if _dodge_chance > 0 and random.random() < _dodge_chance:
                        continue
                    # Shield check
                    if _shield_active:
                        _shield_active = False
                        _shield_timer = 0
                        continue
                    proj_dmg = proj.damage
                    if hasattr(player_obj, 'armor') and player_obj.armor > 0:
                        proj_dmg = max(1, int(proj_dmg * (1.0 - player_obj.armor)))
                    player_obj.current_health -= proj_dmg
                    sounds.play_hurt()
                    trigger_shake(8, 5)
                    vfx.player_hit_burst(player_obj.rect.centerx, player_obj.rect.centery)
                    vfx.damage_number(player_obj.rect.centerx, player_obj.rect.top, proj_dmg)
                    if player_obj.current_health <= 0:
                        # Check for revival
                        if revivals_remaining > 0:
                            revivals_remaining -= 1
                            player_obj.current_health = player_obj.stats["max_health"] // 2
                            trigger_shake(12, 10)
                            now = pygame.time.get_ticks()
                            player_obj.last_hit = now + 2000
                        else:
                            sounds.play_death()

                            # Check if all players are dead
                            all_players_dead = True

                            if gs.net_mode in ("host", "client") and gs.remote_players:
                                for ghost in gs.remote_players.values():
                                    if not hasattr(ghost, 'is_dead') or not ghost.is_dead:
                                        all_players_dead = False
                                        break

                            if all_players_dead or not (gs.net_mode in ("host", "client") and gs.remote_players):
                                # Save highest wave
                                prev_best = settings_module.config.get("highest_wave", 1)
                                if current_wave > prev_best:
                                    settings_module.config["highest_wave"] = current_wave
                                    settings_module.save_config(settings_module.config)
                                # Game over
                                result = show_game_over(player_obj, current_wave)
                                return result
                            else:
                                # Spectate
                                spectating = True
                                if gs.remote_players:
                                    spectate_target_id = next(iter(gs.remote_players))
                                player_obj.kill()

            # Tank ram damage
            if hasattr(player_obj, 'ram_enemy') and player_obj.collision_damage > 0:
                ram_hits = pygame.sprite.spritecollide(player_obj, enemies_grp, False)
                for enemy in ram_hits:
                    dead = player_obj.ram_enemy(enemy)
                    vfx.hit_spark(enemy.rect.centerx, enemy.rect.centery, (100, 150, 255), count=6)
                    if dead:
                        ec = getattr(enemy, 'color', (255, 80, 80))
                        vfx.enemy_death_burst(enemy.rect.centerx, enemy.rect.centery, ec)
                        trigger_shake(6, 5)
                        if gs.net_mode == "client" and gs.net_client:
                            gs.net_client.send(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        elif gs.net_mode == "host" and gs.net_host:
                            gs.net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                    handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)

            # Gems (dead players don't collect)
            if not spectating:
              gem_hits = pygame.sprite.spritecollide(player_obj, gems_grp, True)
              for gem in gem_hits:
                sounds.play_gem()
                vfx.gem_sparkle(gem.rect.centerx, gem.rect.centery)
                _gem_xp = getattr(gem, 'xp_value', 1)
                # Broadcast pickup so other players remove this orb
                _oid = getattr(gem, '_orb_id', 0)
                if _oid and gs.net_mode == "host" and gs.net_host:
                    gs.net_host.broadcast(MSG_ORB_PICKUP, {"id": _oid, "type": "gem"})
                elif _oid and gs.net_mode == "client" and gs.net_client:
                    gs.net_client.send(MSG_ORB_PICKUP, {"id": _oid, "type": "gem"})
                if gs.net_mode in ("host", "client"):
                    # Multiplayer: report gem to host for party XP
                    if gs.net_mode == "host":
                        party_xp += _gem_xp
                        # Check for party level up (host only)
                        if party_xp >= party_xp_to_next:
                            party_level += 1
                            party_xp = 0
                            party_xp_to_next = int(8 + party_level ** 1.5 * 3)
                            is_big = party_level % 5 == 0
                            # Reset pending players set (host + all connected clients)
                            upgrade_pending_players = {0}  # Host is player 0
                            upgrade_pending_players.update(gs.net_host.get_remote_states().keys())
                            # Broadcast party level up to everyone
                            gs.net_host.broadcast(MSG_PARTY_LEVEL_UP, {
                                "level": party_level,
                                "is_big": is_big,
                            })
                            sounds.play_level_up()
                            # Host opens own upgrade menu
                            show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host,
                                              gs.net_client)
                            # Remove self from pending set
                            upgrade_pending_players.discard(0)
                            # If no other players, resume immediately
                            if not upgrade_pending_players:
                                gs.net_host.broadcast(MSG_UPGRADE_RESUME, {})
                            else:
                                gs.net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name": "Party", "level": party_level})
                    elif gs.net_mode == "client":
                        # Send gem pickup to host
                        gs.net_client.send(MSG_GEM_COLLECT, {})
                else:
                    # Singleplayer: local XP
                    xp_gained = _gem_xp
                    if xp_bonus_chance > 0 and random.random() < xp_bonus_chance:
                        xp_gained *= 2  # Double XP!
                    # Apply XP gain multiplier from upgrades
                    xp_gained = max(1, int(xp_gained * player_obj.stats.get("xp_gain", 1.0)))
                    player_obj.current_xp += xp_gained
                    if player_obj.current_xp >= player_obj.xp_to_next_level:
                        player_obj.level += 1
                        player_obj.current_xp = 0
                        player_obj.xp_to_next_level = int(8 + player_obj.level ** 1.5 * 3)
                        sounds.play_level_up()
                        vfx.level_up_burst(player_obj.rect.centerx, player_obj.rect.centery)
                        trigger_shake(8, 6)
                        if player_obj.level % 5 == 0:
                            show_upgrade_menu(True, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host,
                                              gs.net_client)
                        else:
                            show_upgrade_menu(False, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host,
                                              gs.net_client)

            # Gold Coins (dead players don't collect)
            if not spectating:
              coin_hits = pygame.sprite.spritecollide(player_obj, gold_grp, True)
            for coin in coin_hits:
                gold_this_run += coin.value
                add_gold(coin.value)
                sounds.play_gem()
                vfx.gold_sparkle(coin.rect.centerx, coin.rect.centery)
                # In MP: notify host/broadcast gold
                if gs.net_mode == "client" and gs.net_client:
                    gs.net_client.send("gold_pickup", {"value": coin.value})
                elif gs.net_mode == "host" and gs.net_host:
                    # Sync gold to clients
                    gs.net_host.broadcast("gold_sync", {"gold": settings_module.config.get("gold", 0)})

            # Roomba AI + gem collection
            for roomba in roombas_grp:
                roomba.find_target(gems_grp, gold_grp)  # Let roomba pick a target
                collected = roomba.collect_gems(gems_grp)
                for gem in collected:
                    gem.kill()
                    sounds.play_gem()
                    _rgem_xp = getattr(gem, 'xp_value', 1)
                    if gs.net_mode in ("host", "client"):
                        if gs.net_mode == "host":
                            party_xp += _rgem_xp
                            if party_xp >= party_xp_to_next:
                                party_level += 1
                                party_xp = 0
                                party_xp_to_next = int(8 + party_level ** 1.5 * 3)
                                is_big = party_level % 5 == 0
                                upgrade_pending_players = {0}
                                upgrade_pending_players.update(gs.net_host.get_remote_states().keys())
                                gs.net_host.broadcast(MSG_PARTY_LEVEL_UP, {"level": party_level, "is_big": is_big})
                                sounds.play_level_up()
                                show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host, gs.net_client)
                                upgrade_pending_players.discard(0)
                                if not upgrade_pending_players:
                                    gs.net_host.broadcast(MSG_UPGRADE_RESUME, {})
                                else:
                                    gs.net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name": "Party", "level": party_level})
                        elif gs.net_mode == "client":
                            gs.net_client.send(MSG_GEM_COLLECT, {})
                    else:
                        xp_gained = _rgem_xp
                        if xp_bonus_chance > 0 and random.random() < xp_bonus_chance:
                            xp_gained *= 2
                        xp_gained = max(1, int(xp_gained * player_obj.stats.get("xp_gain", 1.0)))
                        player_obj.current_xp += xp_gained
                        if player_obj.current_xp >= player_obj.xp_to_next_level:
                            player_obj.level += 1
                            player_obj.current_xp = 0
                            player_obj.xp_to_next_level = int(8 + player_obj.level ** 1.5 * 3)
                            sounds.play_level_up()
                            is_big = player_obj.level % 5 == 0
                            show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host, gs.net_client)
                # Roomba also picks up gold coins
                for coin in list(gold_grp):
                    dist = math.hypot(coin.rect.centerx - roomba.rect.centerx,
                                      coin.rect.centery - roomba.rect.centery)
                    if dist <= roomba.collect_radius:
                        gold_this_run += coin.value
                        add_gold(coin.value)
                        coin.kill()

            # Saw enemy damage
            for saw in saws_grp:
                for enemy in list(enemies_grp):
                    if isinstance(enemy, PhaseWraith) and enemy.phased_out:
                        continue
                    if isinstance(enemy, ShadowShade) and not enemy.visible:
                        continue
                    if saw.rect.colliderect(enemy.rect) and saw.can_hit_enemy(enemy):
                        saw.hit_enemy(enemy)
                        dead = enemy.take_damage(saw.damage)
                        mid_x = (saw.rect.centerx + enemy.rect.centerx) // 2
                        mid_y = (saw.rect.centery + enemy.rect.centery) // 2
                        vfx.companion_zap(mid_x, mid_y, (255, 220, 100))
                        if dead:
                            sounds.play_hit()
                            trigger_shake(5, 4)
                            ec = getattr(enemy, 'color', (255, 80, 80))
                            vfx.enemy_death_burst(enemy.rect.centerx, enemy.rect.centery, ec)
                            if isinstance(enemy, SplitterEnemy) and enemy.size == 'large':
                                for _ in range(2):
                                    mini = SplitterEnemy(player_obj, current_wave, 'medium')
                                    mini.rect.center = enemy.rect.center
                                    mini.get_nearest_player_pos = make_nearest_player_finder(mini)
                                    all_sprites.add(mini); enemies_grp.add(mini)
                            elif isinstance(enemy, SplitterEnemy) and enemy.size == 'medium':
                                for _ in range(2):
                                    tiny = SplitterEnemy(player_obj, current_wave, 'small')
                                    tiny.rect.center = enemy.rect.center
                                    tiny.get_nearest_player_pos = make_nearest_player_finder(tiny)
                                    all_sprites.add(tiny); enemies_grp.add(tiny)
                            if isinstance(enemy, HydraBoss) and getattr(enemy, 'is_hydra_parent', False):
                                for _ in range(2):
                                    hm = HydraMini(player_obj, current_wave, enemy.rect.center)
                                    hm._net_id = id(hm)
                                    hm.get_nearest_player_pos = make_nearest_player_finder(hm)
                                    all_sprites.add(hm); enemies_grp.add(hm)
                            if isinstance(enemy, HydraSpawnling) and enemy.size == 'normal':
                                for _ in range(2):
                                    tiny2 = HydraSpawnling(player_obj, current_wave, 'tiny')
                                    tiny2.rect.centerx = enemy.rect.centerx + random.randint(-15,15)
                                    tiny2.rect.centery = enemy.rect.centery + random.randint(-15,15)
                                    tiny2._net_id = id(tiny2)
                                    tiny2.get_nearest_player_pos = make_nearest_player_finder(tiny2)
                                    all_sprites.add(tiny2); enemies_grp.add(tiny2)
                            handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)

            # Health Orbs (dead players don't collect)
            if not spectating:
              orb_hits = pygame.sprite.spritecollide(player_obj, health_orbs_grp, True)
              for orb in orb_hits:
                player_obj.heal(orb.heal_amount)

            # Enemies hit Player (dead players are invulnerable)
            if not spectating:
              hit_enemies = pygame.sprite.spritecollide(player_obj, enemies_grp, False)
              # Filter out phased wraiths (intangible) and invisible shades
              hit_enemies = [e for e in hit_enemies if not (isinstance(e, PhaseWraith) and e.phased_out)]
              hit_enemies = [e for e in hit_enemies if not (isinstance(e, ShadowShade) and not e.visible)]
            else:
              hit_enemies = []
            # Charger bull does extra damage while charging
            for e in hit_enemies:
                if isinstance(e, ChargerBull) and e.state == "charging":
                    e.damage = max(e.damage, 35 + current_wave // 3)
            if hit_enemies and not spectating and not player_obj.dash_invincible:
                now = pygame.time.get_ticks()
                if now - player_obj.last_hit > 1000:
                    # Dodge check
                    if _dodge_chance > 0 and random.random() < _dodge_chance:
                        player_obj.last_hit = now
                        # TODO: could add a dodge visual effect here
                    elif _shield_active:
                        # Shield absorbs the hit
                        _shield_active = False
                        _shield_timer = 0
                        player_obj.last_hit = now
                        trigger_shake(3, 2)
                    else:
                        worst_damage = max(e.damage for e in hit_enemies)
                        # Apply armor reduction
                        if hasattr(player_obj, 'armor') and player_obj.armor > 0:
                            worst_damage = max(1, int(worst_damage * (1.0 - player_obj.armor)))
                        player_obj.current_health -= worst_damage
                        player_obj.last_hit = now
                        player_obj.set_hurt(True)
                        sounds.play_hurt()
                        trigger_shake(14, 10)
                        vfx.player_hit_burst(player_obj.rect.centerx, player_obj.rect.centery)
                        vfx.hit_spark(player_obj.rect.centerx, player_obj.rect.centery, (255, 50, 50), count=8)
                        vfx.damage_number(player_obj.rect.centerx, player_obj.rect.top, worst_damage)
                        # Thorns: damage enemies that hit us
                        if _thorns_damage > 0:
                            for e in hit_enemies:
                                e.health -= _thorns_damage
                                if e.health <= 0:
                                    handle_enemy_death(e, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                                    e.kill()
                        if player_obj.current_health <= 0:
                            # Check for revival
                            if revivals_remaining > 0:
                                revivals_remaining -= 1
                                player_obj.current_health = player_obj.stats["max_health"] // 2
                                trigger_shake(12, 10)
                                # Brief invincibility after revive
                                player_obj.last_hit = now + 2000
                            else:
                                sounds.play_death()

                                # Check if all players are dead in multiplayer
                                all_players_dead = True

                                if gs.net_mode in ("host", "client") and gs.remote_players:
                                    # Check if any remote players are still alive
                                    for ghost in gs.remote_players.values():
                                        if not hasattr(ghost, 'is_dead') or not ghost.is_dead:
                                            all_players_dead = False
                                            break

                                if all_players_dead or not (gs.net_mode in ("host", "client") and gs.remote_players):
                                    # Save highest wave
                                    prev_best2 = settings_module.config.get("highest_wave", 1)
                                    if current_wave > prev_best2:
                                        settings_module.config["highest_wave"] = current_wave
                                        settings_module.save_config(settings_module.config)
                                    # Everyone is dead or singleplayer - game over
                                    result = show_game_over(player_obj, current_wave)
                                    return result
                                else:
                                    # Some players still alive - enter spectate mode
                                    spectating = True
                                    spectate_target_id = next(iter(gs.remote_players))
                                    player_obj.kill()  # Remove from sprite groups
                else:
                    flicker = (now // 100) % 2 == 0
                    player_obj.set_hurt(flicker)
            elif not hit_enemies and not spectating:
                player_obj.set_hurt(False)

        # ---- DRAW ----
        surf.fill((5, 5, 15))

        # Update roomba range dynamically from perma stats
        for roomba in roombas_grp:
            roomba.leash_radius = int(350 * _roomba_range_mult)
            roomba.scan_radius = int(250 * _roomba_range_mult)

        # Roomba zap damage: roombas hurt nearby enemies
        if _roomba_damage > 0 and not spectating:
            for roomba in roombas_grp:
                for enemy in enemies_grp:
                    dist = math.hypot(roomba.rect.centerx - enemy.rect.centerx,
                                      roomba.rect.centery - enemy.rect.centery)
                    if dist < 40:
                        # Only zap once per second per enemy
                        now_t = pygame.time.get_ticks()
                        last_zap = getattr(enemy, '_last_roomba_zap', 0)
                        if now_t - last_zap > 1000:
                            enemy.health -= _roomba_damage
                            enemy._last_roomba_zap = now_t
                            mid_x = (roomba.rect.centerx + enemy.rect.centerx) // 2
                            mid_y = (roomba.rect.centery + enemy.rect.centery) // 2
                            vfx.companion_zap(mid_x, mid_y, (0, 255, 255))
                            if enemy.health <= 0:
                                handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                                enemy.kill()

        # Health regeneration
        if _health_regen_rate > 0 and not spectating:
            _health_regen_accum += _health_regen_rate * dt / 60.0  # dt=1 at 60fps, so /60 gives per-second rate
            if _health_regen_accum >= 1.0:
                heal_amt = int(_health_regen_accum)
                _health_regen_accum -= heal_amt
                if player_obj.current_health < player_obj.stats["max_health"]:
                    player_obj.current_health = min(
                        player_obj.stats["max_health"],
                        player_obj.current_health + heal_amt)

        # Shield recharge
        if _shield_level > 0 and not _shield_active:
            _shield_timer += dt
            if _shield_timer >= _shield_recharge_time:
                _shield_active = True
                _shield_timer = 0

        # Screen shake offset
        _sf, _si = get_shake()
        shake_x, shake_y = 0, 0
        if _sf > 0:
            shake_x = random.randint(-_si, _si)
            shake_y = random.randint(-_si, _si)
            consume_shake()

        # We blit everything to a temp surface then offset it
        shake_surf = pygame.Surface((sw, sh))
        shake_surf.fill((5, 5, 15))

        # ---- ANIMATED HEXAGON BACKGROUND ----
        hex_time += 0.02
        for hx, hy, phase in hex_grid:
            pulse = math.sin(hex_time + phase) * 0.5 + 0.5
            alpha = int(8 + pulse * 18)
            color_r = int(0 + pulse * 15)
            color_g = int(5 + pulse * 25)
            color_b = int(20 + pulse * 40)
            points = []
            for k in range(6):
                angle_deg = 60 * k - 30
                angle_rad = math.radians(angle_deg)
                px = hx + hex_radius * math.cos(angle_rad)
                py = hy + hex_radius * math.sin(angle_rad)
                points.append((px, py))
            pygame.draw.polygon(shake_surf, (color_r, color_g, color_b), points, 1)

        # Magnet ring (behind sprites)
        if not spectating:
            player_obj.draw_magnet_ring(shake_surf)

        # Tank ram aura
        if not spectating and hasattr(player_obj, 'draw_ram_aura'):
            player_obj.draw_ram_aura(shake_surf)

        # Dash blink — player flickers invisible, electric afterimages
        if player_obj.dash_duration > 0:
            nc = player_obj.NEON_GLOW_COLOR if hasattr(player_obj, 'NEON_GLOW_COLOR') else (100,200,255)
            dash_trail.append([player_obj.rect.center, 255, 10])
            # Spawn electric sparks along path
            if random.random() < 0.6:
                vfx.bullet_trail(player_obj.rect.centerx + random.randint(-10,10),
                                 player_obj.rect.centery + random.randint(-10,10), nc, 3)
        new_trail = []
        for trail_entry in dash_trail:
            pos, alpha, radius = trail_entry
            if alpha > 0:
                ts = pygame.Surface((radius*2+4, radius*2+4), pygame.SRCALPHA)
                nc = player_obj.NEON_GLOW_COLOR if hasattr(player_obj, 'NEON_GLOW_COLOR') else (100,200,255)
                # Ghostly afterimage
                pygame.draw.circle(ts, (*nc, alpha//3), (radius+2, radius+2), radius+1)
                pygame.draw.circle(ts, (255,255,255, alpha//5), (radius+2, radius+2), max(1, radius//2))
                shake_surf.blit(ts, (pos[0]-radius-2, pos[1]-radius-2))
                trail_entry[1] = max(0, alpha - 40)
                trail_entry[2] = max(1, radius - 1)
                new_trail.append(trail_entry)
        dash_trail[:] = new_trail

        # Draw sprites — player flickers during dash for "blink" effect
        if player_obj.dash_duration > 0 and pygame.time.get_ticks() % 60 < 30:
            # Hide player during dash (blink effect) — draw all except player
            for s in all_sprites:
                if s is not player_obj:
                    shake_surf.blit(s.image, s.rect)
        else:
            all_sprites.draw(shake_surf)

        # ── VFX layer (particles, flashes, zap bolts, damage numbers)
        vfx.spawn_ambient(sw, sh)
        vfx.tick_and_draw(shake_surf)

        # Draw player hat
        if not spectating and hasattr(player_obj, 'draw_hat'):
            player_obj.draw_hat(shake_surf)

        # Paladin heal aura
        if not spectating and hasattr(player_obj, 'draw_heal_aura'):
            player_obj.draw_heal_aura(shake_surf)
            # MP: heal nearby allies
            if gs.net_mode and gs.remote_players:
                from entities.player_paladin import PlayerPaladin
                if isinstance(player_obj, PlayerPaladin):
                    for ghost in gs.remote_players.values():
                        dist_h = math.hypot(ghost.rect.centerx - player_obj.rect.centerx,
                                            ghost.rect.centery - player_obj.rect.centery)
                        if dist_h < player_obj.HEAL_RADIUS:
                            pass  # Would need net msg to actually heal — visual only for now

        # Draw active beam (Arcanist) — supports bouncing segments
        if active_beam and active_beam["timer"] > 0:
            bs = pygame.Surface((sw, sh), pygame.SRCALPHA)
            t_ratio = active_beam["timer"] / 15.0
            bw = int(active_beam["width"] * t_ratio)
            ba = int(200 * t_ratio)
            segments = active_beam.get("segments", [])
            if not segments:
                # Fallback for old format
                segments = [(active_beam.get("start", (0,0)), active_beam.get("end", (0,0)))]
            for seg_start, seg_end in segments:
                pygame.draw.line(bs, (255, 80, 80, int(ba * 0.3)),
                                 seg_start, seg_end, bw + 12)
                pygame.draw.line(bs, (255, 120, 120, int(ba * 0.6)),
                                 seg_start, seg_end, bw + 4)
                pygame.draw.line(bs, (255, 200, 200, ba),
                                 seg_start, seg_end, max(2, bw))
                pygame.draw.line(bs, (255, 255, 255, int(ba * 0.8)),
                                 seg_start, seg_end, max(1, bw // 2))
            shake_surf.blit(bs, (0, 0))
            active_beam["timer"] -= dt
        draw_enemy_health_bars(shake_surf, enemies_grp)

        # ── Draw laser beams and charge indicators
        for enemy in enemies_grp:
            if isinstance(enemy, LaserDrone):
                if enemy.state == "charging":
                    # Draw charge-up line (thin, flickering)
                    dx_l = enemy.beam_target[0] - enemy.rect.centerx
                    dy_l = enemy.beam_target[1] - enemy.rect.centery
                    d_l = math.hypot(dx_l, dy_l)
                    if d_l > 0:
                        end_x = enemy.rect.centerx + int((dx_l/d_l)*400)
                        end_y = enemy.rect.centery + int((dy_l/d_l)*400)
                        a = int(80 * (1 - enemy.charge_timer / enemy.charge_time))
                        ls = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                        pygame.draw.line(ls, (0, 200, 255, a), enemy.rect.center, (end_x, end_y), 1)
                        shake_surf.blit(ls, (0, 0))
                elif enemy.state == "firing":
                    # Draw thick damaging beam
                    dx_l = enemy.beam_target[0] - enemy.rect.centerx
                    dy_l = enemy.beam_target[1] - enemy.rect.centery
                    d_l = math.hypot(dx_l, dy_l)
                    if d_l > 0:
                        end_x = enemy.rect.centerx + int((dx_l/d_l)*600)
                        end_y = enemy.rect.centery + int((dy_l/d_l)*600)
                        ls = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                        # Outer glow
                        pygame.draw.line(ls, (0, 150, 255, 40), enemy.rect.center, (end_x, end_y), 12)
                        pygame.draw.line(ls, (0, 200, 255, 80), enemy.rect.center, (end_x, end_y), 6)
                        # Core
                        pygame.draw.line(ls, (200, 240, 255, 200), enemy.rect.center, (end_x, end_y), 2)
                        shake_surf.blit(ls, (0, 0))

            # ── Leech heal aura indicator
            if isinstance(enemy, LeechPriest):
                aura = pygame.Surface((enemy.heal_radius*2, enemy.heal_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(aura, (180, 50, 255, 15), (enemy.heal_radius, enemy.heal_radius), enemy.heal_radius)
                pygame.draw.circle(aura, (180, 50, 255, 30), (enemy.heal_radius, enemy.heal_radius), enemy.heal_radius, 1)
                shake_surf.blit(aura, (enemy.rect.centerx - enemy.heal_radius,
                                       enemy.rect.centery - enemy.heal_radius))

            # ── Charger bull telegraph line
            if isinstance(enemy, ChargerBull) and enemy.state == "telegraph":
                dx_t = enemy.telegraph_target[0] - enemy.rect.centerx
                dy_t = enemy.telegraph_target[1] - enemy.rect.centery
                d_t = math.hypot(dx_t, dy_t)
                if d_t > 0:
                    end_x = enemy.rect.centerx + int((dx_t/d_t)*500)
                    end_y = enemy.rect.centery + int((dy_t/d_t)*500)
                    prog = 1 - (enemy.telegraph_timer / enemy.telegraph_time)
                    ls = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    a = int(40 + 160 * prog)
                    # Flashing warning line
                    if int(prog * 10) % 2 == 0:
                        pygame.draw.line(ls, (255, 50, 30, a), enemy.rect.center, (end_x, end_y), 2)
                    shake_surf.blit(ls, (0, 0))

            # ── Orbiter shield orbs
            if isinstance(enemy, OrbiterEnemy):
                for ox, oy, idx in enemy.get_orb_positions():
                    orb_s = pygame.Surface((16, 16), pygame.SRCALPHA)
                    hp_ratio = enemy.orb_hp[idx] / max(1, (8 + current_wave // 5))
                    brightness = int(100 + 155 * hp_ratio)
                    pygame.draw.circle(orb_s, (brightness, int(brightness*0.7), 0, 200), (8, 8), 6)
                    pygame.draw.circle(orb_s, (255, 200, 80, 150), (8, 8), 6, 2)
                    shake_surf.blit(orb_s, (ox - 8, oy - 8))

            # ── Sniper laser sight
            if isinstance(enemy, SniperEnemy):
                dx_s = enemy.aim_target[0] - enemy.rect.centerx
                dy_s = enemy.aim_target[1] - enemy.rect.centery
                d_s = math.hypot(dx_s, dy_s)
                if d_s > 0:
                    end_x = enemy.rect.centerx + int((dx_s/d_s)*500)
                    end_y = enemy.rect.centery + int((dy_s/d_s)*500)
                    ls = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    # Thin red laser sight
                    a_s = 30 if enemy.shoot_timer > 20 else int(30 + 100 * (1 - enemy.shoot_timer / 20))
                    pygame.draw.line(ls, (255, 0, 0, a_s), enemy.rect.center, (end_x, end_y), 1)
                    # Red dot on target
                    pygame.draw.circle(ls, (255, 0, 0, a_s + 40), enemy.aim_target, 3)
                    shake_surf.blit(ls, (0, 0))

            # ── Parasite glow on buffed host
            if isinstance(enemy, ParasiteEnemy) and enemy.attached and enemy.host_enemy and enemy.host_enemy.alive():
                glow = pygame.Surface((enemy.host_enemy.rect.w + 12, enemy.host_enemy.rect.h + 12), pygame.SRCALPHA)
                pygame.draw.rect(glow, (200, 0, 200, 35), glow.get_rect(), border_radius=4)
                shake_surf.blit(glow, (enemy.host_enemy.rect.x - 6, enemy.host_enemy.rect.y - 6))

        # ========== NETWORKING ==========
        net_send_timer = getattr(run_game, '_net_timer', 0)

        # Skip network state sync while upgrade menu is open (prevents flicker/catchup)
        _net_paused = bool(gs.upgrade_paused_by)

        if gs.net_mode == "host" and gs.net_host:
            net_send_timer += 1
            if net_send_timer >= 4 and not _net_paused:
                net_send_timer = 0
                _full_timer = getattr(run_game, '_full_state_timer', 0) + 1
                run_game._full_state_timer = _full_timer
                # Fast position-only update (small packet)
                state_data = {
                    "player_id": 0,
                    "x": player_obj.rect.x,
                    "y": player_obj.rect.y,
                    "health": player_obj.current_health,
                    "max_health": player_obj.stats["max_health"],
                    "is_dead": spectating,
                }
                # Full state every ~1 second (60 frames) or first few frames
                if _full_timer % 15 == 0 or _full_timer < 3:
                    state_data["class"] = player_obj.CLASS_KEY
                    state_data["level"] = player_obj.level
                    state_data["username"] = gs.local_username
                    state_data["equipped_hat"] = player_obj.equipped_hat
                gs.net_host.broadcast(MSG_PLAYER_STATE, state_data)

            # Broadcast enemy positions every 8 frames (~7.5fps sync)
            enemy_timer = getattr(run_game, '_enemy_timer', 0)
            enemy_timer += 1
            if enemy_timer >= 8 and not _net_paused:
                enemy_timer = 0
                enemy_states = []
                for e in enemies_grp:
                    edata = {
                        "enemy_id": getattr(e, '_net_id', id(e)),
                        "x": e.rect.x,
                        "y": e.rect.y,
                        "health": e.health,
                        "max_health": e.max_health,
                    }
                    # Send velocity for fast-moving enemies
                    if hasattr(e, 'velocity_x'):
                        edata["vx"] = e.velocity_x
                        edata["vy"] = e.velocity_y
                    enemy_states.append(edata)
                if enemy_states:
                    gs.net_host.broadcast(MSG_ENEMY_UPDATE, {"enemies": enemy_states})

                # Broadcast helper (roomba/saw) positions
                helper_states = []
                for r in roombas_grp:
                    helper_states.append({"type": "roomba", "x": r.rect.centerx, "y": r.rect.centery})
                for s in saws_grp:
                    helper_states.append({"type": "saw", "x": s.rect.centerx, "y": s.rect.centery,
                                          "radius": getattr(s, 'orbit_radius', 50)})
                if helper_states:
                    gs.net_host.broadcast("helper_state", {"pid": 0, "helpers": helper_states})
            run_game._enemy_timer = enemy_timer

            for msg in gs.net_host.get_messages():
                msg_type = msg.get("type", "")
                data = msg.get("data", {})
                from_id = msg.get("_from", -1)

                if msg_type == MSG_BULLET_FIRE:
                    # Spawn remote bullet locally on host screen
                    btype = data.get("weapon", "bullet")
                    bpos = (data.get("bx", 0), data.get("by", 0))
                    tpos = (data.get("tx", 0), data.get("ty", 0))
                    bspd = data.get("speed", 7)
                    bprc = data.get("piercing", 1)
                    bdmg = data.get("damage", 1)
                    bsz = data.get("size", 1.0)
                    if btype == "beam":
                        segs = data.get("segments", [])
                        if segs:
                            active_beam = {
                                "segments": [(tuple(s[0]), tuple(s[1])) for s in segs],
                                "timer": data.get("timer", 15),
                                "width": data.get("width", 12),
                                "dmg": 0, "angle": 0,
                            }
                    elif btype == "laser":
                        rb = LaserBeam(bpos, tpos, bspd, bprc, size=bsz)
                        rb._net_damage = bdmg
                        all_sprites.add(rb)
                        bullets_grp.add(rb)
                    else:
                        rb = Bullet(bpos, tpos, bspd, bprc, size=bsz, color=tuple(data.get("color", [255,255,0])))
                        rb._net_damage = bdmg
                        all_sprites.add(rb)
                        bullets_grp.add(rb)
                    # Client reported killing an enemy — find and kill it by net_id
                    eid = data.get("enemy_id", -1)
                    for e in list(enemies_grp):
                        if getattr(e, '_net_id', None) == eid:
                            handle_enemy_death(e, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                            e.kill()
                            # Broadcast death to all clients so they remove their ghost
                            gs.net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": eid})
                            break

                elif msg_type == "gold_pickup":
                    # Client picked up gold — add to shared gold pool
                    gval = data.get("value", 0)
                    if gval > 0:
                        gold_this_run += gval
                        add_gold(gval)
                        # Sync back to all clients
                        gs.net_host.broadcast("gold_sync", {"gold": settings_module.config.get("gold", 0)})

                elif msg_type == "helper_state":
                    # Client sent their helper positions — store and rebroadcast
                    gs.remote_helpers[from_id] = data.get("helpers", [])
                    gs.net_host.broadcast("helper_state", {"pid": from_id, "helpers": data.get("helpers", [])})

                elif msg_type == MSG_UPGRADE_PAUSE:
                    # Client opened settings/upgrade menu — pause game
                    pname = data.get("player_name", f"Player{from_id}")
                    gs.upgrade_paused_by = {"player_name": pname, "level": data.get("level", "?")}

                elif msg_type == MSG_UPGRADE_RESUME:
                    # Client closed settings/upgrade menu — check if we can resume
                    gs.upgrade_paused_by = None

                elif msg_type == MSG_GEM_COLLECT:
                    # Client picked up a gem — add to party XP
                    party_xp += 1
                    if party_xp >= party_xp_to_next:
                        party_level += 1
                        party_xp = 0
                        party_xp_to_next = int(8 + party_level ** 1.5 * 3)
                        is_big = party_level % 5 == 0
                        # Reset pending players (host + all clients)
                        upgrade_pending_players = {0}
                        upgrade_pending_players.update(gs.net_host.get_remote_states().keys())
                        # Broadcast level up
                        gs.net_host.broadcast(MSG_PARTY_LEVEL_UP, {
                            "level": party_level,
                            "is_big": is_big,
                        })
                        sounds.play_level_up()
                        # Host opens own upgrade menu
                        show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host, gs.net_client)
                        # Remove self from pending
                        upgrade_pending_players.discard(0)
                        # If no other players, resume immediately
                        if not upgrade_pending_players:
                            gs.upgrade_paused_by = None
                            gs.net_host.broadcast(MSG_UPGRADE_RESUME, {})
                        else:
                            gs.upgrade_paused_by = {"player_name": "Party", "level": party_level}
                            gs.net_host.broadcast(MSG_UPGRADE_PAUSE, {"player_name": "Party", "level": party_level})

                elif msg_type == MSG_UPGRADE_DONE:
                    # Client finished picking upgrade
                    upgrade_pending_players.discard(from_id)
                    if not upgrade_pending_players:
                        # Everyone done — resume game
                        gs.upgrade_paused_by = None
                        gs.net_host.broadcast(MSG_UPGRADE_RESUME, {})

                elif msg_type == MSG_ORB_PICKUP:
                    # Client picked up an orb — relay to all other clients and remove locally
                    _pickup_id = data.get("id", 0)
                    if _pickup_id:
                        gs.net_host.broadcast(MSG_ORB_PICKUP, data, exclude=from_id)
                        otype = data.get("type", "gem")
                        target_grp = gems_grp if otype == "gem" else health_orbs_grp
                        for orb in list(target_grp):
                            if getattr(orb, '_orb_id', 0) == _pickup_id:
                                orb.kill()
                                break

                elif msg_type == MSG_REVIVE:
                    # A client wants to revive someone — relay to all and update host state
                    revive_pid = data.get("player_id", -1)
                    gs.net_host.broadcast(MSG_REVIVE, data)
                    # Update ghost on host side
                    if revive_pid in gs.remote_players:
                        gs.remote_players[revive_pid].is_dead = False
                    # Track so they can't be revived again this run
                    if not hasattr(gs, '_was_revived'):
                        gs._was_revived = set()
                    gs._was_revived.add(revive_pid)

            # --- Host: update & broadcast remote player ghosts ---
            usernames = gs.net_host.get_usernames()
            for pid, state in gs.net_host.get_remote_states().items():
                if pid not in gs.remote_players:
                    uname = usernames.get(pid, f"Player{pid}")
                    ghost = RemotePlayerGhost(pid, state.get("class", "default"), username=uname)
                    gs.remote_players[pid] = ghost
                else:
                    uname = usernames.get(pid, gs.remote_players[pid].username)
                    gs.remote_players[pid].username = uname
                gs.remote_players[pid].update_from_state(state)
                if not _net_paused:
                    gs.remote_players[pid].update()

            # --- Host-authoritative wave broadcasting ---
            # Broadcast current wave state every second so clients stay in sync
            wave_bcast_timer = getattr(run_game, '_wave_bcast', 0) + 1
            run_game._wave_bcast = wave_bcast_timer
            if wave_bcast_timer % 60 == 0:
                gs.net_host.broadcast(MSG_WAVE_START, {
                    "wave": current_wave,
                    "active": wave_active,
                    "enemies_remaining": len(enemies_grp),
                    "party_level": party_level,
                    "party_xp": party_xp,
                    "party_xp_to_next": party_xp_to_next,
                })

        elif gs.net_mode == "client" and gs.net_client:
            net_send_timer += 1
            if net_send_timer >= 4 and not _net_paused:
                net_send_timer = 0
                gs.net_client.send_player_state(
                    player_obj.rect.x, player_obj.rect.y,
                    player_obj.current_health, player_obj.CLASS_KEY,
                    player_obj.level, player_obj.stats["max_health"],
                    player_obj.equipped_hat, spectating
                )
                # Send helper positions less frequently (every ~15 ticks)
                _hlp_timer = getattr(run_game, '_helper_timer_c', 0) + 1
                run_game._helper_timer_c = _hlp_timer
                if _hlp_timer % 4 == 0:
                    helper_states = []
                    for r in roombas_grp:
                        helper_states.append({"type": "roomba", "x": r.rect.centerx, "y": r.rect.centery})
                    for s in saws_grp:
                        helper_states.append({"type": "saw", "x": s.rect.centerx, "y": s.rect.centery,
                                              "radius": getattr(s, 'orbit_radius', 50)})
                    if helper_states:
                        gs.net_client.send("helper_state", {"helpers": helper_states})

                # Ping measurement (every ~120 frames = 2 sec at 60fps)
                _ping_timer = getattr(run_game, '_ping_timer', 0) + 1
                run_game._ping_timer = _ping_timer
                if _ping_timer >= 120:
                    run_game._ping_timer = 0
                    import time as _time_mod
                    gs._ping_send_time = _time_mod.perf_counter()
                    gs.net_client.send(MSG_PING, {"time": gs._ping_send_time})

            # Flush any pending sends
            if hasattr(gs.net_client, '_flush_send'):
                gs.net_client._flush_send()

            for msg in gs.net_client.get_messages():
                msg_type = msg.get("type", "")
                data = msg.get("data", {})

                if msg_type == MSG_PLAYER_STATE:
                    pid = data.get("player_id", -1)
                    if pid not in gs.remote_players:
                        uname = data.get("username", f"Player{pid}")
                        ghost = RemotePlayerGhost(pid, data.get("class", "default"), username=uname)
                        gs.remote_players[pid] = ghost
                    gs.remote_players[pid].update_from_state(data)
                    if not _net_paused:
                        gs.remote_players[pid].update()

                elif msg_type == MSG_USERNAME:
                    pid = data.get("player_id", -1)
                    uname = data.get("username", f"Player{pid}")
                    if pid in gs.remote_players:
                        gs.remote_players[pid].username = uname

                elif msg_type == MSG_BULLET_FIRE:
                    # Spawn remote bullet locally on client screen
                    btype = data.get("weapon", "bullet")
                    bpos = (data.get("bx", 0), data.get("by", 0))
                    tpos = (data.get("tx", 0), data.get("ty", 0))
                    bspd = data.get("speed", 7)
                    bprc = data.get("piercing", 1)
                    bdmg = data.get("damage", 1)
                    bsz = data.get("size", 1.0)
                    if btype == "beam":
                        segs = data.get("segments", [])
                        if segs:
                            active_beam = {
                                "segments": [(tuple(s[0]), tuple(s[1])) for s in segs],
                                "timer": data.get("timer", 15),
                                "width": data.get("width", 12),
                                "dmg": 0, "angle": 0,
                            }
                    elif btype == "laser":
                        rb = LaserBeam(bpos, tpos, bspd, bprc, size=bsz)
                        rb._net_damage = bdmg
                        all_sprites.add(rb)
                        bullets_grp.add(rb)
                    else:
                        rb = Bullet(bpos, tpos, bspd, bprc, size=bsz, color=tuple(data.get("color", [255,255,0])))
                        rb._net_damage = bdmg
                        all_sprites.add(rb)
                        bullets_grp.add(rb)

                elif msg_type == MSG_ENEMY_SPAWN:
                    # Host spawned an enemy — create a ghost
                    eid = data.get("enemy_id")
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    is_boss = data.get("is_boss", False)
                    wave = data.get("wave", 1)
                    max_hp = data.get("max_health", 1)
                    hp = data.get("health", 1)
                    etype = data.get("enemy_type", "basic")
                    espeed = data.get("speed", 2)
                    ghost = RemoteEnemyGhost(eid, x, y, is_boss, wave, etype, espeed)
                    ghost.max_health = max_hp
                    ghost.health = hp
                    gs.remote_enemies[eid] = ghost
                    all_sprites.add(ghost)
                    enemies_grp.add(ghost)

                elif msg_type == MSG_ENEMY_UPDATE:
                    # Host sent enemy position updates — skip during pause
                    if not _net_paused:
                        enemy_list = data.get("enemies", [])
                        for edata in enemy_list:
                            eid = edata.get("enemy_id")
                            if eid in gs.remote_enemies:
                                gs.remote_enemies[eid].update_from_state(edata)

                elif msg_type == MSG_ENEMY_DEAD:
                    # Host says enemy died — remove ghost
                    eid = data.get("enemy_id")
                    if eid in gs.remote_enemies:
                        gs.remote_enemies[eid].kill()
                        del gs.remote_enemies[eid]

                elif msg_type == MSG_GEM_SPAWN:
                    # Host spawned gems — create them locally
                    positions = data.get("positions", [])
                    ids = data.get("ids", [])
                    for i, pos in enumerate(positions):
                        gem = ExpGem(pos)
                        if i < len(ids):
                            gem._orb_id = ids[i]
                        all_sprites.add(gem)
                        gems_grp.add(gem)

                elif msg_type == MSG_ORB_SPAWN:
                    # Host spawned health orb — create it locally
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    heal = data.get("heal", 20)
                    orb = HealthOrb((x, y))
                    orb._orb_id = data.get("id", 0)
                    orb.heal_amount = heal
                    all_sprites.add(orb)
                    health_orbs_grp.add(orb)

                elif msg_type == "gold_spawn":
                    # Host spawned gold coin — create locally
                    gx = data.get("x", 0)
                    gy = data.get("y", 0)
                    gv = data.get("value", 1)
                    coin = GoldCoin((gx, gy), gv)
                    all_sprites.add(coin)
                    gold_grp.add(coin)

                elif msg_type == "gold_sync":
                    # Host syncs total gold to client
                    synced_gold = data.get("gold", 0)
                    settings_module.config["gold"] = synced_gold
                    from core.settings import save_config
                    save_config(settings_module.config)

                elif msg_type == MSG_ORB_PICKUP:
                    # Another player picked up an orb — remove it locally
                    _pickup_id = data.get("id", 0)
                    if _pickup_id:
                        otype = data.get("type", "gem")
                        target_grp = gems_grp if otype == "gem" else health_orbs_grp
                        for orb in list(target_grp):
                            if getattr(orb, '_orb_id', 0) == _pickup_id:
                                orb.kill()
                                break

                elif msg_type == MSG_SHAKE:
                    trigger_shake(data.get("f", 5), data.get("i", 4))

                elif msg_type == MSG_PONG:
                    import time as _time_mod
                    send_t = getattr(gs, '_ping_send_time', None)
                    if send_t is not None:
                        gs._last_ping_ms = (_time_mod.perf_counter() - send_t) * 1000

                elif msg_type == MSG_REVIVE:
                    # Someone revived us or another player
                    revive_pid = data.get("player_id", -1)
                    revive_x = data.get("x", sw // 2)
                    revive_y = data.get("y", sh // 2)
                    if revive_pid == gs.net_client.my_id:
                        # We're being revived!
                        spectating = False
                        player_obj.current_health = player_obj.stats["max_health"] // 2
                        player_obj.rect.centerx = revive_x
                        player_obj.rect.centery = revive_y
                        # Re-add to sprite groups (kill() removed us)
                        if not player_obj.alive():
                            all_sprites.add(player_obj)
                        # Brief invincibility after revive
                        player_obj.last_hit = pygame.time.get_ticks() + 2000
                        trigger_shake(10, 8)
                        vfx.level_up_burst(revive_x, revive_y)
                        print(f"[Revive] Revived at ({revive_x}, {revive_y}) with {player_obj.current_health} HP")
                    else:
                        # Another player was revived — update their ghost
                        if revive_pid in gs.remote_players:
                            ghost = gs.remote_players[revive_pid]
                            ghost.is_dead = False

                elif msg_type == "hat_drop":
                    # Host says a hat dropped — add to our collection too
                    hat_id = data.get("hat_id")
                    hat_name = data.get("name", "???")
                    hat_rarity = data.get("rarity", "common")
                    collected = settings_module.config.get("collected_hats", [])
                    if hat_id and hat_id not in collected:
                        collected.append(hat_id)
                        settings_module.config["collected_hats"] = collected
                        from core.settings import save_config
                        save_config(settings_module.config)
                    hat_notifications.append({"name": hat_name, "rarity": hat_rarity, "timer": 300})

                elif msg_type == "helper_state":
                    # Remote player's helper positions
                    pid = data.get("pid", -1)
                    gs.remote_helpers[pid] = data.get("helpers", [])

                elif msg_type == MSG_PARTY_LEVEL_UP:
                    # Party leveled up — open upgrade menu
                    # Update party XP variables (nonlocal to update run_game scope)
                    party_level = data.get("level", 1)
                    party_xp = 0  # Reset after level up
                    party_xp_to_next = int(8 + party_level ** 1.5 * 3)  # Increase threshold
                    is_big = data.get("is_big", False)
                    sounds.play_level_up()
                    show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host, gs.net_client)

                elif msg_type == MSG_UPGRADE_PAUSE:
                    gs.upgrade_paused_by = {
                        "player_name": data.get("player_name", "Party"),
                        "level": data.get("level", 1)
                    }

                elif msg_type == MSG_UPGRADE_RESUME:
                    gs.upgrade_paused_by = None

                elif msg_type == MSG_WAVE_START:
                    # Host told us which wave we're on + party XP state
                    srv_wave = data.get("wave", current_wave)

                    # Update party XP from host
                    if "party_level" in data:
                        party_level = data["party_level"]
                    if "party_xp" in data:
                        party_xp = data["party_xp"]
                    if "party_xp_to_next" in data:
                        party_xp_to_next = data["party_xp_to_next"]

                    if srv_wave != current_wave:
                        # Advance to the host's wave
                        current_wave = srv_wave
                        # Clear existing enemies so we don't double-spawn
                        for e in list(enemies_grp):
                            e.kill()
                        gs.remote_enemies.clear()
                        start_wave(current_wave)

                elif msg_type == MSG_WAVE_COMPLETE:
                    # Host says wave is done
                    wave_active = False
                    wave_cooldown = WAVE_COOLDOWN_TIME

            # --- Client: suppress autonomous wave spawning ---
            # Clients don't spawn enemies independently; they rely on the host's
            # MSG_WAVE_START messages to stay in sync. So we skip the spawning
            # logic block above when in client mode. We still allow enemies that
            # exist locally to update & be killed by local bullets (damage is
            # applied locally and reported back to host via MSG_ENEMY_DEAD).
            # Reset wave_active so client loop doesn't advance waves on its own.
            # (Handled by not re-running the wave spawning block — see comment
            # below the wave spawning section.)

            if not gs.net_client.connected:
                pass

        run_game._net_timer = net_send_timer

        # ========== BLIT GAME WORLD WITH SHAKE OFFSET ==========
        surf.blit(shake_surf, (shake_x, shake_y))

        # ========== DRAW REMOTE PLAYERS ==========
        for pid, ghost in gs.remote_players.items():
            if getattr(ghost, 'is_dead', False):
                continue  # Don't draw dead players
            surf.blit(ghost.image, ghost.rect)
            ghost.draw_label(surf)
            if hasattr(ghost, 'draw_hat'):
                ghost.draw_hat(surf)
            if hasattr(ghost, 'draw_health_bar'):
                ghost.draw_health_bar(surf)

        # ========== DRAW REMOTE HELPERS (roombas/saws) ==========
        for pid, helpers in gs.remote_helpers.items():
            ghost = gs.remote_players.get(pid)
            ghost_color = (57, 255, 20)  # Default green
            if ghost and hasattr(ghost, 'class_key'):
                from entities.remote_ghosts import _SPRITE_MAP
                _, _, _, glow = _SPRITE_MAP.get(ghost.class_key, _SPRITE_MAP["default"])
                ghost_color = glow
            for h in helpers:
                hx, hy = h.get("x", 0), h.get("y", 0)
                if h.get("type") == "roomba":
                    # Small orbiting circle
                    hs = pygame.Surface((18, 18), pygame.SRCALPHA)
                    pygame.draw.circle(hs, (*ghost_color, 140), (9, 9), 8)
                    pygame.draw.circle(hs, (255, 255, 255, 80), (9, 9), 4)
                    surf.blit(hs, (hx - 9, hy - 9))
                elif h.get("type") == "saw":
                    # Spinning saw
                    sr = 12
                    hs2 = pygame.Surface((sr*2+4, sr*2+4), pygame.SRCALPHA)
                    pygame.draw.circle(hs2, (*ghost_color, 120), (sr+2, sr+2), sr, 2)
                    pygame.draw.circle(hs2, (255, 255, 255, 100), (sr+2, sr+2), sr//2)
                    surf.blit(hs2, (hx - sr - 2, hy - sr - 2))

        # ========== UPGRADE PAUSE OVERLAY ==========
        if gs.upgrade_paused_by and not spectating:
            # Semi-transparent overlay
            pause_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 150))
            surf.blit(pause_overlay, (0, 0))

            # Message
            pname = gs.upgrade_paused_by.get("player_name", "Player")
            plevel = gs.upgrade_paused_by.get("level", 1)
            wait_txt = _gs.title_font.render(f"{pname} is choosing upgrade...", True, GOLD)
            surf.blit(wait_txt, (sw // 2 - wait_txt.get_width() // 2, sh // 2 - 80))
            lvl_txt = _gs.small_font.render(f"Level {plevel}", True, GRAY)
            surf.blit(lvl_txt, (sw // 2 - lvl_txt.get_width() // 2, sh // 2 - 30))

            # Debug indicator showing game is paused
            paused_txt = _gs.title_font.render("GAME PAUSED", True, RED)
            surf.blit(paused_txt, (sw // 2 - paused_txt.get_width() // 2, sh // 2 + 20))

        # ========== SPECTATE OVERLAY ==========
        if spectating:
            # Dark vignette
            spec_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            spec_overlay.fill((0, 0, 0, 120))
            surf.blit(spec_overlay, (0, 0))

            # Follow camera label (we can't truly move the camera but highlight who we're watching)
            if spectate_target_id and spectate_target_id in gs.remote_players:
                ghost = gs.remote_players[spectate_target_id]
                # Draw a bright ring around spectated player
                pygame.draw.circle(surf, CYAN, ghost.rect.center, ghost.rect.width + 8, 2)
                name_surf = _gs.menu_font.render(f"Watching: {ghost.username}", True, CYAN)
                surf.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, 50))

            dead_txt = _gs.title_font.render("YOU DIED", True, RED)
            surf.blit(dead_txt, (sw // 2 - dead_txt.get_width() // 2, sh // 2 - 60))
            spec_hint = _gs.small_font.render("Spectating  |  ← → to switch player", True, LIGHT_GRAY)
            surf.blit(spec_hint, (sw // 2 - spec_hint.get_width() // 2, sh // 2 - 20))
            wave_txt = _gs.small_font.render(f"Wave {current_wave}  |  {len(enemies_grp)} enemies remaining", True, GRAY)
            surf.blit(wave_txt, (sw // 2 - wave_txt.get_width() // 2, sh // 2 + 10))
        else:
            # ========== DRAW UI ==========
            draw_ui(surf, player_obj, current_wave, enemies_grp, gs.net_mode, party_level, party_xp, party_xp_to_next,
                    gold_this_run, revivals_remaining)
            draw_boss_health_bar(surf, enemies_grp)

            # FPS / Ping overlay
            if settings_module.config.get("show_fps", False):
                _ping_val = getattr(gs, '_last_ping_ms', None)
                draw_fps_ping(surf, clock.get_fps(), _ping_val if gs.net_mode else None)

            # Dash cooldown bar (bottom-centre) - neon styled
            dash_ratio = player_obj.get_dash_cooldown_ratio()
            bar_w, bar_h = 140, 10
            bar_x = sw // 2 - bar_w // 2
            bar_y = sh - 22
            pygame.draw.rect(surf, (15, 15, 25), (bar_x, bar_y, bar_w, bar_h))
            ready_w = int(bar_w * (1.0 - dash_ratio))
            if dash_ratio == 0:
                bar_color = (0, 255, 255)
                # Glow when ready
                glow_s = pygame.Surface((bar_w + 8, bar_h + 8), pygame.SRCALPHA)
                glow_s.fill((0, 255, 255, 20))
                surf.blit(glow_s, (bar_x - 4, bar_y - 4))
            else:
                bar_color = (70, 130, 180)
            pygame.draw.rect(surf, bar_color, (bar_x, bar_y, ready_w, bar_h))
            # Bright edge
            if ready_w > 2:
                pygame.draw.line(surf, (min(255, bar_color[0] + 80), min(255, bar_color[1] + 80), min(255, bar_color[2] + 80)),
                                 (bar_x + ready_w - 1, bar_y + 1), (bar_x + ready_w - 1, bar_y + bar_h - 2))
            pygame.draw.rect(surf, bar_color, (bar_x, bar_y, bar_w, bar_h), 1)
            _kb = settings_module.config.get("keybinds", {})
            _dash_key_name = pygame.key.name(_kb.get("dash", pygame.K_SPACE)).upper()
            dash_label = _gs.small_font.render(f"DASH [{_dash_key_name}]" if dash_ratio == 0 else "DASH", True,
                                           (0, 255, 255) if dash_ratio == 0 else (80, 80, 100))
            surf.blit(dash_label, (bar_x + bar_w // 2 - dash_label.get_width() // 2, bar_y - 16))

            # Shield indicator
            if _shield_level > 0:
                shield_x = bar_x + bar_w + 15
                shield_y = bar_y
                if _shield_active:
                    pygame.draw.circle(surf, (80, 200, 255), (shield_x + 10, shield_y + 5), 10)
                    pygame.draw.circle(surf, (150, 230, 255), (shield_x + 10, shield_y + 5), 10, 2)
                    sh_label = _gs.small_font.render("⛊", True, (200, 240, 255))
                else:
                    ratio = _shield_timer / max(1, _shield_recharge_time)
                    pygame.draw.circle(surf, (30, 50, 70), (shield_x + 10, shield_y + 5), 10)
                    # Recharge arc
                    if ratio > 0:
                        arc_rect = pygame.Rect(shield_x, shield_y - 5, 20, 20)
                        pygame.draw.arc(surf, (60, 140, 200), arc_rect, math.pi/2, math.pi/2 + ratio * math.pi * 2, 2)
                    sh_label = _gs.small_font.render("⛊", True, (60, 80, 100))
                surf.blit(sh_label, (shield_x + 3, shield_y - 4))

        if wave_banner_timer > 0:
            draw_wave_banner(surf, current_wave)
            wave_banner_timer -= dt

        # Hat drop notifications
        from core.settings import RARITY_COLORS
        ny = sh - 80
        for notif in hat_notifications[:]:
            if notif["timer"] <= 0:
                hat_notifications.remove(notif); continue
            notif["timer"] -= dt
            alpha = min(255, notif["timer"] * 3)
            rc = RARITY_COLORS.get(notif["rarity"], (180,180,190))
            a_fill = max(0, min(255, int(alpha * 0.15)))
            a_border = max(0, min(255, int(alpha * 0.5)))
            # Background
            nbs = pygame.Surface((300, 32), pygame.SRCALPHA)
            nbs.fill((rc[0], rc[1], rc[2], a_fill))
            pygame.draw.rect(nbs, (rc[0], rc[1], rc[2], a_border), (0,0,300,32), 2, border_radius=6)
            surf.blit(nbs, (sw//2 - 150, ny))
            # Text
            ht = _gs.small_font.render(f"NEW HAT: {notif['name']}", True, (rc[0], rc[1], rc[2]))
            rt = _gs.small_font.render(f"[{notif['rarity'].upper()}]", True, (rc[0], rc[1], rc[2]))
            surf.blit(ht, (sw//2 - ht.get_width()//2, ny + 2))
            surf.blit(rt, (sw//2 - rt.get_width()//2, ny + 16))
            ny -= 38

        # ========== DRAW NETWORK INFO ==========
        if gs.net_mode:
            if gs.net_mode == "host":
                count = gs.net_host.get_player_count() if gs.net_host else 1
                net_txt = _gs.small_font.render(f"Hosting | {count} players", True, CYAN)
            else:
                status = "Connected" if (gs.net_client and gs.net_client.connected) else "Disconnected"
                color = GREEN if status == "Connected" else RED
                net_txt = _gs.small_font.render(f"Client | {status}", True, color)
            surf.blit(net_txt, (sw - 200, 105))

        display_mgr.present()
        if settings_module.FPS > 0:
            clock.tick(settings_module.FPS)
        else:
            clock.tick(0)  # Unlimited

    return "main_menu"