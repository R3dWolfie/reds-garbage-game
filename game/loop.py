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
from core.game_state import (
    display_mgr, clock, sounds, gs, PLAYER_CLASSES,
    trigger_shake, get_shake, consume_shake,
    font, small_font, title_font, boss_font, menu_font, header_font,
    GAME_NAME, VERSION
)
from game.helpers import (
    get_nearest_enemies, handle_enemy_death, apply_magnet,
    apply_gold_magnet, get_perma_stats, add_gold
)
from ui.hud import draw_ui, draw_boss_health_bar, draw_wave_banner, draw_enemy_health_bars
from ui.upgrade_menu import show_upgrade_menu
from ui.menus import show_pause_menu, show_game_over
from entities.remote_ghosts import RemoteEnemyGhost, RemotePlayerGhost

def run_game(class_key, starting_wave=1):

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
        player_obj.stats["fire_rate"] = max(3, int(player_obj.stats["fire_rate"] * _fire_rate_mult))

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
    SPAWN_DELAY = 30
    wave_active = False
    wave_cooldown = 0
    WAVE_COOLDOWN_TIME = 120
    wave_banner_timer = 0
    fire_cooldown = 0

    # Party XP (shared in multiplayer, only tracked on host)
    party_level = 1
    party_xp = 0
    party_xp_to_next = 5
    upgrade_pending_players = set()  # Set of player IDs waiting to pick upgrades

    def start_wave(wave_num):
        nonlocal enemies_to_spawn, enemies_spawned, wave_active, spawn_timer, wave_banner_timer
        base_count = 5 + (wave_num * 2)
        # +10% enemies every 10 levels
        scale = 1.0 + (wave_num // 10) * 0.10
        enemies_to_spawn = int(base_count * scale)
        enemies_spawned = 0
        wave_active = True
        spawn_timer = 0
        wave_banner_timer = 120
        if wave_num % 10 == 0:
            sounds.play_boss_spawn()
            trigger_shake(12, 8)
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

    start_wave(current_wave)

    # Dash trail visual: list of (pos, alpha, frame) tuples
    dash_trail = []
    # Spectate state (multiplayer only)
    spectating = False
    spectate_target_id = None

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

    while True:
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
                        action = show_pause_menu()
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
            # DEBUG: Show we're paused
            if getattr(run_game, '_pause_debug_counter', 0) % 60 == 0:  # Print every second
                print(f"[{gs.net_mode or 'SP'}] PAUSED: gs.upgrade_paused_by = {gs.upgrade_paused_by}")
            run_game._pause_debug_counter = getattr(run_game, '_pause_debug_counter', 0) + 1

        if not gs.upgrade_paused_by:
            if gs.net_mode != "client":
                if wave_active:
                    if enemies_spawned < enemies_to_spawn:
                        spawn_timer += 1
                        if spawn_timer >= SPAWN_DELAY:
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
                                for _ in range(random.randint(3, 5)):
                                    se = SwarmEnemy(player_obj, current_wave)
                                    se._net_id = id(se)
                                    se.get_nearest_player_pos = make_nearest_player_finder(se)
                                    all_sprites.add(se); enemies_grp.add(se)
                                e = None  # Already spawned
                            elif enemy_type in enemy_creators:
                                e = enemy_creators[enemy_type]()
                            else:
                                e = Enemy(player_obj, current_wave)

                            if e is not None:
                                e._net_id = id(e)
                                e.get_nearest_player_pos = make_nearest_player_finder(e)
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
                                })
                    else:
                        if len(enemies_grp) == 0:
                            wave_active = False
                            wave_cooldown = WAVE_COOLDOWN_TIME
                            # Tell clients the wave is over
                            if gs.net_mode == "host" and gs.net_host:
                                gs.net_host.broadcast(MSG_WAVE_COMPLETE, {"wave": current_wave})
                else:
                    wave_cooldown -= 1
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

            # Detect dash start for sound + trail seed
            if not spectating and player_obj.dash_duration == player_obj.dash_duration_max:
                if not getattr(player_obj, '_dash_sound_played', False):
                    sounds.play_dash()
                    trigger_shake(3, 3)
                    dash_trail.append([player_obj.rect.center, 200, 8])
                    player_obj._dash_sound_played = True
            elif player_obj.dash_duration == 0:
                player_obj._dash_sound_played = False

            apply_magnet(player_obj, gems_grp)
            apply_gold_magnet(player_obj, gold_grp)

            # ---- AUTO-FIRE ----
            if fire_cooldown <= 0 and not spectating:
                # Get the SINGLE nearest enemy
                targets = get_nearest_enemies(player_obj, enemies_grp, 1)

                if targets:
                    nearest_enemy = targets[0]
                    weapon = player_obj.get_weapon_type()
                    multishot_count = player_obj.stats["multishot"]

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

                        bsize = player_obj.stats.get("bullet_size", 1.0)
                        if weapon == "laser":
                            b = LaserBeam(player_obj.rect.center, (target_x, target_y),
                                          player_obj.stats["bullet_speed"], player_obj.stats["piercing"],
                                          size=bsize)
                        else:
                            b = Bullet(player_obj.rect.center, (target_x, target_y),
                                       player_obj.stats["bullet_speed"], player_obj.stats["piercing"],
                                       size=bsize, bounces=_bullet_bounces)
                        all_sprites.add(b)
                        bullets_grp.add(b)

                        # Broadcast bullet to all other players
                        if gs.net_mode in ("host", "client"):
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
                            }
                            if gs.net_mode == "host" and gs.net_host:
                                gs.net_host.broadcast(MSG_BULLET_FIRE, bullet_data)
                            elif gs.net_mode == "client" and gs.net_client:
                                gs.net_client.send(MSG_BULLET_FIRE, bullet_data)

                    fire_cooldown = player_obj.stats["fire_rate"]
                    sounds.play_shoot()
            else:
                fire_cooldown -= 1

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
                    # Crit chance
                    is_crit = False
                    if hasattr(player_obj, 'crit_chance') and player_obj.crit_chance > 0:
                        if not getattr(bullet, '_net_damage', None):  # Only local bullets crit
                            if random.random() < player_obj.crit_chance:
                                dmg = int(dmg * 2)
                                is_crit = True
                    dead = enemy.take_damage(dmg)
                    bullet.hits += 1
                    if dead:
                        sounds.play_hit()
                        trigger_shake(4, 4)

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
                    trigger_shake(6, 3)
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
                    if dead:
                        if gs.net_mode == "client" and gs.net_client:
                            gs.net_client.send(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                        elif gs.net_mode == "host" and gs.net_host:
                            gs.net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": getattr(enemy, '_net_id', -1)})
                    handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)

            # Gems
            gem_hits = pygame.sprite.spritecollide(player_obj, gems_grp, True)
            for gem in gem_hits:
                sounds.play_gem()
                if gs.net_mode in ("host", "client"):
                    # Multiplayer: report gem to host for party XP
                    if gs.net_mode == "host":
                        party_xp += 1
                        # Check for party level up (host only)
                        if party_xp >= party_xp_to_next:
                            party_level += 1
                            party_xp = 0
                            party_xp_to_next = int(party_xp_to_next * 1.5)
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
                    xp_gained = 1
                    if xp_bonus_chance > 0 and random.random() < xp_bonus_chance:
                        xp_gained = 2  # Double XP!
                    # Apply XP gain multiplier from upgrades
                    xp_gained = max(1, int(xp_gained * player_obj.stats.get("xp_gain", 1.0)))
                    player_obj.current_xp += xp_gained
                    if player_obj.current_xp >= player_obj.xp_to_next_level:
                        player_obj.level += 1
                        player_obj.current_xp = 0
                        player_obj.xp_to_next_level = int(player_obj.xp_to_next_level * 1.5)
                        sounds.play_level_up()
                        if player_obj.level % 5 == 0:
                            show_upgrade_menu(True, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host,
                                              gs.net_client)
                        else:
                            show_upgrade_menu(False, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host,
                                              gs.net_client)

            # Gold Coins
            coin_hits = pygame.sprite.spritecollide(player_obj, gold_grp, True)
            for coin in coin_hits:
                gold_this_run += coin.value
                add_gold(coin.value)
                sounds.play_gem()  # Reuse gem sound for now

            # Roomba AI + gem collection
            for roomba in roombas_grp:
                roomba.find_target(gems_grp, gold_grp)  # Let roomba pick a target
                collected = roomba.collect_gems(gems_grp)
                for gem in collected:
                    gem.kill()
                    sounds.play_gem()
                    if gs.net_mode in ("host", "client"):
                        if gs.net_mode == "host":
                            party_xp += 1
                            if party_xp >= party_xp_to_next:
                                party_level += 1
                                party_xp = 0
                                party_xp_to_next = int(party_xp_to_next * 1.5)
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
                        xp_gained = 1
                        if xp_bonus_chance > 0 and random.random() < xp_bonus_chance:
                            xp_gained = 2
                        xp_gained = max(1, int(xp_gained * player_obj.stats.get("xp_gain", 1.0)))
                        player_obj.current_xp += xp_gained
                        if player_obj.current_xp >= player_obj.xp_to_next_level:
                            player_obj.level += 1
                            player_obj.current_xp = 0
                            player_obj.xp_to_next_level = int(player_obj.xp_to_next_level * 1.5)
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
                        if dead:
                            sounds.play_hit()
                            trigger_shake(3, 3)
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

            # Health Orbs
            orb_hits = pygame.sprite.spritecollide(player_obj, health_orbs_grp, True)
            for orb in orb_hits:
                player_obj.heal(orb.heal_amount)

            # Enemies hit Player
            hit_enemies = pygame.sprite.spritecollide(player_obj, enemies_grp, False)
            # Filter out phased wraiths (intangible) and invisible shades
            hit_enemies = [e for e in hit_enemies if not (isinstance(e, PhaseWraith) and e.phased_out)]
            hit_enemies = [e for e in hit_enemies if not (isinstance(e, ShadowShade) and not e.visible)]
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
                        trigger_shake(8, 6)
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
                            if enemy.health <= 0:
                                handle_enemy_death(enemy, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                                enemy.kill()

        # Health regeneration
        if _health_regen_rate > 0 and not spectating:
            _health_regen_accum += _health_regen_rate / FPS
            if _health_regen_accum >= 1.0:
                heal_amt = int(_health_regen_accum)
                _health_regen_accum -= heal_amt
                if player_obj.current_health < player_obj.stats["max_health"]:
                    player_obj.current_health = min(
                        player_obj.stats["max_health"],
                        player_obj.current_health + heal_amt)

        # Shield recharge
        if _shield_level > 0 and not _shield_active:
            _shield_timer += 1
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

        # Dash trail
        if player_obj.dash_duration > 0 or dash_trail:
            dash_trail.append([player_obj.rect.center, 220, 8])
        new_trail = []
        for trail_entry in dash_trail:
            pos, alpha, radius = trail_entry
            if alpha > 0:
                ts = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                # Outer glow
                pygame.draw.circle(ts, (0, 200, 255, alpha // 3), (radius + 2, radius + 2), radius + 2)
                # Inner bright
                pygame.draw.circle(ts, (100, 220, 255, alpha), (radius + 2, radius + 2), radius)
                shake_surf.blit(ts, (pos[0] - radius - 2, pos[1] - radius - 2))
                trail_entry[1] = max(0, alpha - 30)
                trail_entry[2] = max(1, radius - 1)
                new_trail.append(trail_entry)
        dash_trail[:] = new_trail

        all_sprites.draw(shake_surf)
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

        if gs.net_mode == "host" and gs.net_host:
            net_send_timer += 1
            if net_send_timer >= 3:
                net_send_timer = 0
                gs.net_host.broadcast(MSG_PLAYER_STATE, {
                    "player_id": 0,
                    "x": player_obj.rect.x,
                    "y": player_obj.rect.y,
                    "health": player_obj.current_health,
                    "class": player_obj.CLASS_KEY,
                    "level": player_obj.level,
                    "username": gs.local_username,
                })

            # Broadcast enemy positions every 5 frames (15fps sync)
            enemy_timer = getattr(run_game, '_enemy_timer', 0)
            enemy_timer += 1
            if enemy_timer >= 5:
                enemy_timer = 0
                enemy_states = []
                for e in enemies_grp:
                    enemy_states.append({
                        "enemy_id": getattr(e, '_net_id', id(e)),
                        "x": e.rect.x,
                        "y": e.rect.y,
                        "health": e.health,
                        "max_health": e.max_health,
                    })
                if enemy_states:
                    gs.net_host.broadcast(MSG_ENEMY_UPDATE, {"enemies": enemy_states})
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
                    if btype == "laser":
                        rb = LaserBeam(bpos, tpos, bspd, bprc, size=bsz)
                    else:
                        rb = Bullet(bpos, tpos, bspd, bprc, size=bsz)
                    rb._net_damage = bdmg
                    all_sprites.add(rb)
                    bullets_grp.add(rb)

                elif msg_type == MSG_ENEMY_DEAD:
                    # Client reported killing an enemy — find and kill it by net_id
                    eid = data.get("enemy_id", -1)
                    for e in list(enemies_grp):
                        if getattr(e, '_net_id', None) == eid:
                            handle_enemy_death(e, all_sprites, gems_grp, health_orbs_grp, gs.net_mode, gs.net_host, gold_grp)
                            e.kill()
                            # Broadcast death to all clients so they remove their ghost
                            gs.net_host.broadcast(MSG_ENEMY_DEAD, {"enemy_id": eid})
                            break

                elif msg_type == MSG_GEM_COLLECT:
                    # Client picked up a gem — add to party XP
                    party_xp += 1
                    if party_xp >= party_xp_to_next:
                        party_level += 1
                        party_xp = 0
                        party_xp_to_next = int(party_xp_to_next * 1.5)
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
            if net_send_timer >= 3:
                net_send_timer = 0
                gs.net_client.send_player_state(
                    player_obj.rect.x, player_obj.rect.y,
                    player_obj.current_health, player_obj.CLASS_KEY,
                    player_obj.level
                )

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
                    if btype == "laser":
                        rb = LaserBeam(bpos, tpos, bspd, bprc, size=bsz)
                    else:
                        rb = Bullet(bpos, tpos, bspd, bprc, size=bsz)
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
                    ghost = RemoteEnemyGhost(eid, x, y, is_boss, wave)
                    ghost.max_health = max_hp
                    ghost.health = hp
                    gs.remote_enemies[eid] = ghost
                    all_sprites.add(ghost)
                    enemies_grp.add(ghost)

                elif msg_type == MSG_ENEMY_UPDATE:
                    # Host sent enemy position updates
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
                    for pos in positions:
                        gem = ExpGem(pos)
                        all_sprites.add(gem)
                        gems_grp.add(gem)

                elif msg_type == MSG_ORB_SPAWN:
                    # Host spawned health orb — create it locally
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    heal = data.get("heal", 20)
                    orb = HealthOrb((x, y))
                    orb.heal_amount = heal
                    all_sprites.add(orb)
                    health_orbs_grp.add(orb)

                elif msg_type == MSG_PARTY_LEVEL_UP:
                    # Party leveled up — open upgrade menu
                    # Update party XP variables (nonlocal to update run_game scope)
                    party_level = data.get("level", 1)
                    party_xp = 0  # Reset after level up
                    party_xp_to_next = int(party_xp_to_next * 1.5)  # Increase threshold
                    is_big = data.get("is_big", False)
                    sounds.play_level_up()
                    show_upgrade_menu(is_big, player_obj, all_sprites, enemies_grp, gs.net_mode, gs.net_host, gs.net_client)

                elif msg_type == MSG_UPGRADE_PAUSE:
                    # Upgrade pause (party is choosing)
                    print(f"[Client] Received MSG_UPGRADE_PAUSE: {data}")  # DEBUG
                    gs.upgrade_paused_by = {
                        "player_name": data.get("player_name", "Party"),
                        "level": data.get("level", 1)
                    }
                    print(f"[Client] Set gs.upgrade_paused_by = {gs.upgrade_paused_by}")  # DEBUG

                elif msg_type == MSG_UPGRADE_RESUME:
                    # All players finished choosing
                    print(f"[Client] Received MSG_UPGRADE_RESUME")  # DEBUG
                    gs.upgrade_paused_by = None
                    print(f"[Client] Cleared gs.upgrade_paused_by")  # DEBUG

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
            surf.blit(ghost.image, ghost.rect)
            ghost.draw_label(surf)

        # ========== UPGRADE PAUSE OVERLAY ==========
        if gs.upgrade_paused_by and not spectating:
            # Semi-transparent overlay
            pause_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 150))
            surf.blit(pause_overlay, (0, 0))

            # Message
            pname = gs.upgrade_paused_by.get("player_name", "Player")
            plevel = gs.upgrade_paused_by.get("level", 1)
            wait_txt = title_font.render(f"{pname} is choosing upgrade...", True, GOLD)
            surf.blit(wait_txt, (sw // 2 - wait_txt.get_width() // 2, sh // 2 - 80))
            lvl_txt = small_font.render(f"Level {plevel}", True, GRAY)
            surf.blit(lvl_txt, (sw // 2 - lvl_txt.get_width() // 2, sh // 2 - 30))

            # Debug indicator showing game is paused
            paused_txt = title_font.render("GAME PAUSED", True, RED)
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
                name_surf = menu_font.render(f"Watching: {ghost.username}", True, CYAN)
                surf.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, 50))

            dead_txt = title_font.render("YOU DIED", True, RED)
            surf.blit(dead_txt, (sw // 2 - dead_txt.get_width() // 2, sh // 2 - 60))
            spec_hint = small_font.render("Spectating  |  ← → to switch player", True, LIGHT_GRAY)
            surf.blit(spec_hint, (sw // 2 - spec_hint.get_width() // 2, sh // 2 - 20))
            wave_txt = small_font.render(f"Wave {current_wave}  |  {len(enemies_grp)} enemies remaining", True, GRAY)
            surf.blit(wave_txt, (sw // 2 - wave_txt.get_width() // 2, sh // 2 + 10))
        else:
            # ========== DRAW UI ==========
            draw_ui(surf, player_obj, current_wave, enemies_grp, gs.net_mode, party_level, party_xp, party_xp_to_next,
                    gold_this_run, revivals_remaining)
            draw_boss_health_bar(surf, enemies_grp)

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
            dash_label = small_font.render("DASH [HOLD]" if dash_ratio == 0 else "DASH", True,
                                           (0, 255, 255) if dash_ratio == 0 else (80, 80, 100))
            surf.blit(dash_label, (bar_x + bar_w // 2 - dash_label.get_width() // 2, bar_y - 16))

            # Shield indicator
            if _shield_level > 0:
                shield_x = bar_x + bar_w + 15
                shield_y = bar_y
                if _shield_active:
                    pygame.draw.circle(surf, (80, 200, 255), (shield_x + 10, shield_y + 5), 10)
                    pygame.draw.circle(surf, (150, 230, 255), (shield_x + 10, shield_y + 5), 10, 2)
                    sh_label = small_font.render("⛊", True, (200, 240, 255))
                else:
                    ratio = _shield_timer / max(1, _shield_recharge_time)
                    pygame.draw.circle(surf, (30, 50, 70), (shield_x + 10, shield_y + 5), 10)
                    # Recharge arc
                    if ratio > 0:
                        arc_rect = pygame.Rect(shield_x, shield_y - 5, 20, 20)
                        pygame.draw.arc(surf, (60, 140, 200), arc_rect, math.pi/2, math.pi/2 + ratio * math.pi * 2, 2)
                    sh_label = small_font.render("⛊", True, (60, 80, 100))
                surf.blit(sh_label, (shield_x + 3, shield_y - 4))

        if wave_banner_timer > 0:
            draw_wave_banner(surf, current_wave)
            wave_banner_timer -= 1

        # ========== DRAW NETWORK INFO ==========
        if gs.net_mode:
            if gs.net_mode == "host":
                count = gs.net_host.get_player_count() if gs.net_host else 1
                net_txt = small_font.render(f"Hosting | {count} players", True, CYAN)
            else:
                status = "Connected" if (gs.net_client and gs.net_client.connected) else "Disconnected"
                color = GREEN if status == "Connected" else RED
                net_txt = small_font.render(f"Client | {status}", True, color)
            surf.blit(net_txt, (sw - 200, 105))

        pygame.display.flip()
        clock.tick(FPS)

    return "main_menu"