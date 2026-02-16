# game_helpers.py
"""Gameplay utility functions: magnet, enemy death, gold, perma stats."""

import math
import random
import core.settings as settings_module
from core.settings import *
from entities.objects import ExpGem, HealthOrb, GoldCoin
from core.game_state import MSG_GEM_SPAWN, MSG_ORB_SPAWN

# Hat drop notifications (list of {"name", "rarity", "timer"} dicts)
hat_notifications = []


def _try_hat_drop(enemy_obj, net_mode=None, net_host=None):
    """Roll for hat drop from killed enemy."""
    from core.settings import HAT_DEFS, HAT_DROP_CHANCES, HAT_BOSS_DROP_CHANCES, save_config
    is_boss = getattr(enemy_obj, 'is_boss', False)
    wave = getattr(enemy_obj, 'wave', 0)
    collected = settings_module.config.get("collected_hats", [])
    chances = HAT_BOSS_DROP_CHANCES if is_boss else HAT_DROP_CHANCES

    for hat in HAT_DEFS:
        if hat["id"] == "none":
            continue
        if hat["id"] in collected:
            continue  # Already own this hat
        # Source check
        src = hat.get("source", "any")
        if src.startswith("boss_"):
            req_wave = int(src.split("_")[1])
            if not is_boss or wave != req_wave:
                continue
        elif src == "boss" and not is_boss:
            continue
        # Roll
        chance = chances.get(hat["rarity"], 0)
        if chance > 0 and random.random() < chance:
            # Drop!
            collected.append(hat["id"])
            settings_module.config["collected_hats"] = collected
            save_config(settings_module.config)
            hat_notifications.append({"name": hat["name"], "rarity": hat["rarity"], "timer": 300})
            # Broadcast hat drop to all players
            if net_mode == "host" and net_host:
                net_host.broadcast("hat_drop", {"hat_id": hat["id"], "name": hat["name"], "rarity": hat["rarity"]})
            return  # Only one hat per kill


def get_nearest_enemies(player_obj, enemy_group, count):
    enemy_list = []
    for e in enemy_group:
        dist = math.hypot(e.rect.centerx - player_obj.rect.centerx,
                          e.rect.centery - player_obj.rect.centery)
        enemy_list.append((dist, e))
    enemy_list.sort(key=lambda x: x[0])
    return [e for _, e in enemy_list[:count]]


def handle_enemy_death(enemy_obj, all_spr, gem_grp, orb_grp, net_mode=None, net_host=None, gold_grp=None):
    xp_count = enemy_obj.get_xp_drop_count()
    gem_positions = []
    for i in range(xp_count):
        offset = (enemy_obj.rect.centerx + random.randint(-20, 20),
                  enemy_obj.rect.centery + random.randint(-20, 20))
        gem = ExpGem(offset)
        all_spr.add(gem)
        gem_grp.add(gem)
        gem_positions.append(offset)

    # Broadcast gem spawns to clients
    if net_mode == "host" and net_host and gem_positions:
        net_host.broadcast(MSG_GEM_SPAWN, {"positions": gem_positions})

    if random.random() < HEALTH_ORB_DROP_CHANCE:
        orb = HealthOrb(enemy_obj.rect.center)
        all_spr.add(orb)
        orb_grp.add(orb)
        if net_mode == "host" and net_host:
            net_host.broadcast(MSG_ORB_SPAWN, {
                "x": enemy_obj.rect.centerx,
                "y": enemy_obj.rect.centery,
                "heal": orb.heal_amount
            })

    # Gold coin drops
    if gold_grp is not None:
        perma = settings_module.config.get("perma_upgrades", {})
        gold_rush_lvl = perma.get("gold_rush", 0)
        lucky_bonus = perma.get("lucky_drops", 0) * 0.08
        drop_chance = GOLD_DROP_CHANCE + (gold_rush_lvl * 0.08) + lucky_bonus
        is_boss = getattr(enemy_obj, 'is_boss', False)
        if is_boss:
            drop_chance = GOLD_DROP_CHANCE_BOSS
        if random.random() < drop_chance:
            if is_boss:
                value = GOLD_BOSS_VALUE
            else:
                value = random.randint(GOLD_VALUE_MIN, GOLD_VALUE_MAX)
            coin = GoldCoin(
                (enemy_obj.rect.centerx + random.randint(-15, 15),
                 enemy_obj.rect.centery + random.randint(-15, 15)),
                value
            )
            all_spr.add(coin)
            gold_grp.add(coin)

            # Broadcast gold coin to clients
            if net_mode == "host" and net_host:
                net_host.broadcast("gold_spawn", {
                    "x": coin.rect.centerx,
                    "y": coin.rect.centery,
                    "value": value,
                })

        # Lucky drops: extra XP gems
        if lucky_bonus > 0 and random.random() < lucky_bonus:
            bonus_gem = ExpGem((enemy_obj.rect.centerx + random.randint(-15, 15),
                                enemy_obj.rect.centery + random.randint(-15, 15)))
            all_spr.add(bonus_gem)
            gem_grp.add(bonus_gem)

    # Hat drops
    _try_hat_drop(enemy_obj, net_mode, net_host)


def apply_magnet(player_obj, gem_grp):
    """Pull nearby XP gems toward the player."""
    radius = player_obj.get_magnet_radius()
    if radius <= 0:
        return
    px, py = player_obj.rect.center
    for gem in gem_grp:
        dist = math.hypot(gem.rect.centerx - px, gem.rect.centery - py)
        if dist <= radius:
            pull_speed = max(3, 8 - (dist / radius) * 5)
            gem.move_toward((px, py), pull_speed)


def apply_gold_magnet(player_obj, gold_grp):
    """Pull nearby gold coins toward the player."""
    perma = settings_module.config.get("perma_upgrades", {})
    base_radius = 60
    gold_mag_lvl = perma.get("gold_magnet", 0)
    radius = base_radius + (gold_mag_lvl * 40)
    px, py = player_obj.rect.center
    for coin in gold_grp:
        dist = math.hypot(coin.rect.centerx - px, coin.rect.centery - py)
        if dist <= radius:
            pull_speed = max(3, 7 - (dist / radius) * 4)
            coin.move_toward((px, py), pull_speed)


def get_perma_stats():
    """Get computed perma upgrade stats from config."""
    perma = settings_module.config.get("perma_upgrades", {})
    return {
        "roomba_count": perma.get("roomba_count", 0),
        "roomba_speed": 0.02 + (perma.get("roomba_speed", 0) * 0.005),
        "saw_count": perma.get("saw_count", 0),
        "saw_damage": 3 + (perma.get("saw_damage", 0) * 2),
        "saw_speed": 0.03 + (perma.get("saw_speed", 0) * 0.006),
        "saw_size_mult": 1.0 + (perma.get("saw_size", 0) * 0.2),
        "crit_chance": perma.get("crit_chance", 0) * 0.05,
        "base_magnet": perma.get("base_magnet", 0) * 30,
        "armor": perma.get("armor", 0) * 0.05,
        "xp_bonus": perma.get("xp_bonus", 0) * 0.10,
        "starting_hp": perma.get("starting_hp", 0) * 15,
        "revivals": perma.get("revival", 0),
        "roomba_range": 1.0 + (perma.get("roomba_range", 0) * 0.4),
        "roomba_damage": perma.get("roomba_damage", 0) * 3,
        "dash_cooldown_reduction": perma.get("dash_power", 0) * 4,
        "dash_duration_bonus": perma.get("dash_power", 0) * 1,
        "health_regen": perma.get("health_regen", 0) * 0.5,
        "dodge_chance": perma.get("dodge_chance", 0) * 0.04,
        "thorns_damage": perma.get("thorns", 0) * 5,
        "move_speed_bonus": perma.get("move_speed", 0),
        "fire_rate_mult": max(0.2, 1.0 - (perma.get("fire_rate_boost", 0) * 0.08)),
        "bullet_bounces": perma.get("bullet_ricochet", 0),
        "shield_recharge": max(3, 18 - (perma.get("shield", 0) * 3)),
        "shield_level": perma.get("shield", 0),
        "lucky_drop_bonus": perma.get("lucky_drops", 0) * 0.08,
    }


def add_gold(amount):
    """Add gold to persistent storage and save."""
    settings_module.config["gold"] = settings_module.config.get("gold", 0) + amount
    settings_module.save_config(settings_module.config)


def spend_gold(amount):
    """Spend gold. Returns True if successful."""
    current = settings_module.config.get("gold", 0)
    if current >= amount:
        settings_module.config["gold"] = current - amount
        settings_module.save_config(settings_module.config)
        return True
    return False