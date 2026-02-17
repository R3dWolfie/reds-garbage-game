# enemy.py
import pygame, random, math
from core.settings import *
from core.settings import get_dt
from core.sprite_loader import load_sprite, make_neon_sprite

class Enemy(pygame.sprite.Sprite):
    def __init__(self, player, wave):
        super().__init__()
        self.player = player; self.is_boss = False
        self.image = make_neon_sprite(load_sprite("enemy_basic.png",(30,30),RED,(30,30)),(255,30,60),glow_size=3)
        self.rect = self.image.get_rect()
        self.max_health = 1+(wave//3); self.health = self.max_health
        self.speed = 2+(wave*0.1); self.damage = 10; self._spawn_at_edge()
    @property
    def _dt(self):
        return get_dt()
    @property
    def spd(self):
        """Speed scaled by delta time."""
        return self.speed * get_dt()
    def _spawn_at_edge(self):
        sw,sh=SCREEN_WIDTH,SCREEN_HEIGHT; s=random.choice([0,1,2,3])
        if s==0: self.rect.x=random.randint(0,sw); self.rect.y=-40
        elif s==1: self.rect.x=random.randint(0,sw); self.rect.y=sh+40
        elif s==2: self.rect.x=-40; self.rect.y=random.randint(0,sh)
        else: self.rect.x=sw+40; self.rect.y=random.randint(0,sh)
    def get_xp_drop_count(self): return max(1, 1+self.max_health//5)
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0: self.kill(); return True
        return False
    def _get_target(self):
        if hasattr(self,'get_nearest_player_pos') and self.get_nearest_player_pos: return self.get_nearest_player_pos()
        return self.player.rect.centerx, self.player.rect.centery
    def draw_health_bar(self, surf):
        if self.health >= self.max_health: return
        bw=self.rect.width; bx,by=self.rect.x,self.rect.y-8
        r=max(0,self.health/self.max_health)
        c=(57,255,20) if r>0.5 else (255,255,0) if r>0.25 else (255,30,60)
        pygame.draw.rect(surf,(15,15,25),(bx,by,bw,5))
        pygame.draw.rect(surf,c,(bx,by,int(bw*r),5))
        pygame.draw.rect(surf,c,(bx,by,bw,5),1)
    def update(self):
        tx,ty=self._get_target(); dx=tx-self.rect.centerx; dy=ty-self.rect.centery
        d=math.hypot(dx,dy)
        if d!=0: self.rect.x+=dx/d*self.spd; self.rect.y+=dy/d*self.spd

class ArrowEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.base_image=make_neon_sprite(load_sprite("enemy_arrow.png",(30,15),PURPLE,(30,15)),(180,0,255),glow_size=3)
        self.image=self.base_image.copy(); self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=8+(wave//10); self.health=self.max_health
        self.speed=7+(wave*0.15); self.damage=12; self.bounces_left=4
        cx,cy=SCREEN_WIDTH//2,SCREEN_HEIGHT//2
        dx=cx-self.rect.centerx; dy=cy-self.rect.centery; d=math.hypot(dx,dy) or 1
        self.velocity_x=(dx/d)*self.speed+random.uniform(-0.5,0.5)
        self.velocity_y=(dy/d)*self.speed+random.uniform(-0.5,0.5)
        self._update_rotation()
    def _update_rotation(self):
        a=math.degrees(math.atan2(-self.velocity_y,self.velocity_x)); oc=self.rect.center
        self.image=pygame.transform.rotate(self.base_image,a); self.rect=self.image.get_rect(center=oc)
    def update(self):
        sw,sh=SCREEN_WIDTH,SCREEN_HEIGHT; _d=self._dt
        if self.bounces_left>0:
            self.rect.x+=self.velocity_x*_d; self.rect.y+=self.velocity_y*_d; b=False
            if self.rect.left<=0: self.rect.left=0; self.velocity_x=abs(self.velocity_x); b=True
            elif self.rect.right>=sw: self.rect.right=sw; self.velocity_x=-abs(self.velocity_x); b=True
            if self.rect.top<=0: self.rect.top=0; self.velocity_y=abs(self.velocity_y); b=True
            elif self.rect.bottom>=sh: self.rect.bottom=sh; self.velocity_y=-abs(self.velocity_y); b=True
            if b: self.bounces_left-=1; self._update_rotation()
        else:
            tx,ty=self._get_target(); dx=tx-self.rect.centerx; dy=ty-self.rect.centery; d=math.hypot(dx,dy)
            if d!=0:
                self.velocity_x=(dx/d)*self.speed; self.velocity_y=(dy/d)*self.speed
                self._update_rotation(); self.rect.x+=self.velocity_x*_d; self.rect.y+=self.velocity_y*_d

class TankEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=make_neon_sprite(load_sprite("enemy_tank.png",(45,45),(255,140,0),(45,45)),(255,140,0),glow_size=4)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=80+(wave*3); self.health=self.max_health
        self.speed=1+(wave*0.02); self.damage=5; self.shoot_cooldown=0; self.shoot_delay=90
    def update(self):
        super().update()
        if self.shoot_cooldown>0: self.shoot_cooldown-=self._dt
    def can_shoot(self): return self.shoot_cooldown==0
    def shoot(self,tx=0,ty=0): self.shoot_cooldown=self.shoot_delay; return True
    def get_xp_drop_count(self): return max(3,3+self.max_health//10)

class SplitterEnemy(Enemy):
    def __init__(self, player, wave, size='large'):
        super().__init__(player,wave); self.size=size
        data={'large':((40,40),(50,255,50),4,60+wave*2,1.5+wave*0.08,12),
              'medium':((25,25),(100,255,100),3,30,2.5,8),'small':((15,15),(150,255,150),2,15,3.5,5)}
        sz,col,gl,hp,spd,dmg=data[size]
        self.image=make_neon_sprite(load_sprite("enemy_splitter.png",sz,col,sz),col,glow_size=gl)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=hp; self.health=hp; self.speed=spd; self.damage=dmg
    def get_xp_drop_count(self): return {'large':4,'medium':2,'small':1}[self.size]

class ZigZagEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=make_neon_sprite(load_sprite("enemy_zigzag.png",(28,28),YELLOW,(28,28)),(255,255,0),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=35+(wave//2); self.health=self.max_health
        self.speed=3+(wave*0.08); self.damage=10; self.zz_t=0; self.zz_d=1
    def update(self):
        tx,ty=self._get_target(); dx=tx-self.rect.centerx; dy=ty-self.rect.centery; d=math.hypot(dx,dy)
        if d!=0:
            dx,dy=dx/d,dy/d; self.zz_t+=1
            if self.zz_t>=30: self.zz_t=0; self.zz_d*=-1
            self.rect.x+=(dx+(-dy)*self.zz_d*0.5)*self.spd
            self.rect.y+=(dy+(dx)*self.zz_d*0.5)*self.spd

class TeleportEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        sz=(24,24); img=pygame.Surface(sz,pygame.SRCALPHA)
        pts=[(12,0),(24,12),(12,24),(0,12)]; pygame.draw.polygon(img,(200,100,255),pts); pygame.draw.polygon(img,(255,200,255),pts,2)
        self.image=make_neon_sprite(img,(200,100,255),glow_size=4)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=20+wave; self.health=self.max_health; self.speed=2; self.damage=15
        self.tp_timer=random.randint(60,120)
    def update(self):
        self.tp_timer-=self._dt
        if self.tp_timer<=0:
            tx,ty=self._get_target()
            self.rect.centerx=tx+random.randint(-120,120); self.rect.centery=ty+random.randint(-120,120)
            self.rect.clamp_ip(pygame.Rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)); self.tp_timer=random.randint(80,150)
        else: super().update()

class ShieldEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        sz=(32,32); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(80,180,255),(16,16),14); pygame.draw.circle(img,(150,220,255),(16,16),14,2)
        pygame.draw.circle(img,(200,240,255),(16,16),8)
        self.image=make_neon_sprite(img,(80,180,255),glow_size=4)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=50+wave*2; self.health=self.max_health; self.speed=2.0+wave*0.05; self.damage=12
        self.shield_hp=30+wave; self.shield_max=self.shield_hp; self.shield_regen_timer=0
    def take_damage(self, amount):
        if self.shield_hp>0:
            ab=min(amount,self.shield_hp); self.shield_hp-=ab; amount-=ab; self.shield_regen_timer=180
        if amount>0: self.health-=amount
        if self.health<=0: self.kill(); return True
        return False
    def update(self):
        super().update()
        if self.shield_regen_timer>0: self.shield_regen_timer-=self._dt
        elif self.shield_hp<self.shield_max: self.shield_hp=min(self.shield_max,self.shield_hp+0.3)
    def draw_health_bar(self, surf):
        super().draw_health_bar(surf)
        if self.shield_hp>0:
            bw=self.rect.width; r=self.shield_hp/self.shield_max; by=self.rect.y-14
            pygame.draw.rect(surf,(60,150,255),(self.rect.x,by,int(bw*r),3))
            pygame.draw.rect(surf,(100,180,255),(self.rect.x,by,bw,3),1)

class SwarmEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        sz=(14,14); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(255,150,50),(7,7),6); pygame.draw.circle(img,(255,200,100),(7,7),3)
        self.image=make_neon_sprite(img,(255,150,50),glow_size=2)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=5+wave//5; self.health=self.max_health; self.speed=4.5+wave*0.1; self.damage=5
        self.off_a=random.uniform(0,math.pi*2); self.wob=0
    def update(self):
        tx,ty=self._get_target(); dx=tx-self.rect.centerx; dy=ty-self.rect.centery; d=math.hypot(dx,dy)
        if d!=0:
            dx,dy=dx/d,dy/d; self.wob+=0.15
            self.rect.x+=dx*self.spd+math.sin(self.wob+self.off_a)*1.5
            self.rect.y+=dy*self.spd+math.cos(self.wob+self.off_a)*1.5
    def get_xp_drop_count(self): return 1

class VortexEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        sz=(36,36); img=pygame.Surface(sz,pygame.SRCALPHA)
        for i in range(3): pygame.draw.circle(img,(100+i*50,0,200+i*20),(18,18),16-i*4,2)
        pygame.draw.circle(img,(255,100,255),(18,18),4)
        self.image=make_neon_sprite(img,(180,0,255),glow_size=5)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=100+wave*3; self.health=self.max_health; self.speed=1.0+wave*0.03; self.damage=18
        self.pull_strength=1.5+wave*0.02; self.pull_radius=200
    def get_xp_drop_count(self): return max(4,4+self.max_health//8)

class NecroEnemy(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        sz=(34,34); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(50,200,50),(17,14),12); pygame.draw.rect(img,(50,200,50),(11,20,12,8))
        pygame.draw.circle(img,(0,0,0),(13,12),3); pygame.draw.circle(img,(0,0,0),(21,12),3)
        pygame.draw.rect(img,(0,0,0),(14,22,2,4)); pygame.draw.rect(img,(0,0,0),(18,22,2,4))
        self.image=make_neon_sprite(img,(50,255,50),glow_size=4)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=80+wave*2; self.health=self.max_health; self.speed=1.2+wave*0.03; self.damage=10
        self.summon_timer=180; self.summon_delay=max(90,180-wave*2)
    def update(self):
        super().update(); self.summon_timer-=self._dt
    def can_summon(self):
        if self.summon_timer<=0: self.summon_timer=self.summon_delay; return True
        return False
    def get_xp_drop_count(self): return max(5,5+self.max_health//8)


# ─────────── NEW: SPIRAL SHOOTER (wave 55+) ───────────
class SpiralEnemy(Enemy):
    """Triangle that spirals inward and fires projectiles at the player."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (26, 26); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Triangle shape
        pts = [(13, 0), (26, 22), (0, 22)]
        pygame.draw.polygon(img, (255, 80, 180), pts)
        pygame.draw.polygon(img, (255, 150, 220), pts, 2)
        # Inner triangle
        pygame.draw.polygon(img, (255, 200, 240), [(13, 6), (21, 18), (5, 18)], 1)
        self.image = make_neon_sprite(img, (255, 80, 180), glow_size=3)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 40 + wave; self.health = self.max_health
        self.speed = 2.5 + wave * 0.06; self.damage = 12
        self.spiral_angle = random.uniform(0, math.pi * 2)
        self.spiral_radius = 200
        self.shoot_timer = 0; self.shoot_delay = max(40, 80 - wave)

    def update(self):
        tx, ty = self._get_target()
        # Spiral toward target
        self.spiral_angle += 0.08
        self.spiral_radius = max(20, self.spiral_radius - 0.3)
        goal_x = tx + math.cos(self.spiral_angle) * self.spiral_radius
        goal_y = ty + math.sin(self.spiral_angle) * self.spiral_radius
        dx = goal_x - self.rect.centerx; dy = goal_y - self.rect.centery
        d = math.hypot(dx, dy)
        if d > 0:
            self.rect.x += (dx / d) * self.spd
            self.rect.y += (dy / d) * self.spd
        self.shoot_timer -= self._dt

    def can_shoot(self):
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_delay
            return True
        return False


# ─────────── NEW: MINE LAYER (wave 60+) ───────────
class MineLayerEnemy(Enemy):
    """Hexagon that kites away from the player and drops explosive proximity mines."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (28, 28); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Hexagon shape
        cx, cy = 14, 14
        hex_pts = [(cx + int(10 * math.cos(math.radians(60 * k + 30))),
                     cy + int(10 * math.sin(math.radians(60 * k + 30)))) for k in range(6)]
        pygame.draw.polygon(img, (255, 140, 0), hex_pts)
        pygame.draw.polygon(img, (255, 200, 80), hex_pts, 2)
        # Hazard dot
        pygame.draw.circle(img, (255, 50, 50), (cx, cy), 3)
        self.image = make_neon_sprite(img, (255, 140, 0), glow_size=3)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 35 + wave; self.health = self.max_health
        self.speed = 2.8 + wave * 0.05; self.damage = 8
        self.mine_timer = 90; self.mine_delay = max(60, 120 - wave)
        self.mines_laid = 0; self.max_mines = 3

    def update(self):
        # Run AWAY from the player (kiting)
        tx, ty = self._get_target()
        dx = self.rect.centerx - tx; dy = self.rect.centery - ty
        d = math.hypot(dx, dy)
        if d > 0 and d < 250:
            self.rect.x += (dx / d) * self.spd
            self.rect.y += (dy / d) * self.spd
        elif d >= 250:
            # Strafe perpendicular when far enough
            perp_x = -dy / d; perp_y = dx / d
            self.rect.x += perp_x * self.spd * 0.7
            self.rect.y += perp_y * self.spd * 0.7
        # Keep on screen
        self.rect.clamp_ip(pygame.Rect(10, 10, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20))
        self.mine_timer -= self._dt

    def can_lay_mine(self):
        if self.mine_timer <= 0 and self.mines_laid < self.max_mines:
            self.mine_timer = self.mine_delay
            self.mines_laid += 1
            return True
        return False


class ProximityMine(pygame.sprite.Sprite):
    """Dropped by MineLayerEnemy. Arms after 1s, explodes when player is near."""
    def __init__(self, pos, damage=15):
        super().__init__()
        self.image = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 80, 0), (9, 9), 7)
        pygame.draw.circle(self.image, (255, 200, 50), (9, 9), 7, 2)
        pygame.draw.circle(self.image, (255, 50, 50), (9, 9), 3)
        self.rect = self.image.get_rect(center=pos)
        self.damage = damage; self.arm_timer = 60  # 1 second to arm
        self.proximity = 45; self.lifetime = 600  # 10 seconds then despawn
        self.exploded = False

    def update(self):
        if self.arm_timer > 0:
            self.arm_timer -= self._dt
            # Blink while arming
            if self.arm_timer % 10 < 5:
                self.image.set_alpha(100)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill()


# ─────────── NEW: LASER DRONE (wave 65+) ───────────
class LaserDrone(Enemy):
    """Diamond-shaped drone that stops, charges, then fires a damaging beam."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (24, 36); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Diamond / elongated shape
        pts = [(12, 0), (24, 18), (12, 36), (0, 18)]
        pygame.draw.polygon(img, (0, 200, 255), pts)
        pygame.draw.polygon(img, (100, 230, 255), pts, 2)
        # Center eye
        pygame.draw.circle(img, (255, 255, 255), (12, 18), 4)
        pygame.draw.circle(img, (255, 0, 0), (12, 18), 2)
        self.image = make_neon_sprite(img, (0, 200, 255), glow_size=3)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 55 + wave * 2; self.health = self.max_health
        self.speed = 2.0 + wave * 0.04; self.damage = 8
        # Laser states: moving -> charging -> firing -> cooldown
        self.state = "moving"
        self.charge_timer = 0; self.charge_time = 60  # 1 sec charge
        self.fire_timer = 0; self.fire_time = 30  # 0.5 sec beam
        self.cooldown_timer = 0; self.cooldown_time = 120
        self.beam_target = (0, 0)

    def update(self):
        tx, ty = self._get_target()

        if self.state == "moving":
            dx = tx - self.rect.centerx; dy = ty - self.rect.centery
            d = math.hypot(dx, dy)
            # Move to medium range then stop to charge
            if d < 200:
                self.state = "charging"
                self.charge_timer = self.charge_time
                self.beam_target = (tx, ty)
            elif d > 0:
                self.rect.x += (dx / d) * self.spd
                self.rect.y += (dy / d) * self.spd

        elif self.state == "charging":
            self.charge_timer -= self._dt
            self.beam_target = (tx, ty)  # Track during charge
            if self.charge_timer <= 0:
                self.state = "firing"
                self.fire_timer = self.fire_time

        elif self.state == "firing":
            self.fire_timer -= self._dt
            if self.fire_timer <= 0:
                self.state = "cooldown"
                self.cooldown_timer = self.cooldown_time

        elif self.state == "cooldown":
            self.cooldown_timer -= self._dt
            # Drift slowly
            dx = tx - self.rect.centerx; dy = ty - self.rect.centery
            d = math.hypot(dx, dy)
            if d > 0:
                self.rect.x += (dx / d) * self.spd * 0.3
                self.rect.y += (dy / d) * self.spd * 0.3
            if self.cooldown_timer <= 0:
                self.state = "moving"


# ─────────── NEW: LEECH PRIEST (wave 70+) ───────────
class LeechPriest(Enemy):
    """Star-shaped healer that restores HP to nearby enemies."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (30, 30); img = pygame.Surface(sz, pygame.SRCALPHA)
        # 5-pointed star
        cx, cy = 15, 15
        outer, inner = 13, 6
        pts = []
        for i in range(10):
            a = math.radians(36 * i - 90)
            r = outer if i % 2 == 0 else inner
            pts.append((cx + int(r * math.cos(a)), cy + int(r * math.sin(a))))
        pygame.draw.polygon(img, (180, 50, 255), pts)
        pygame.draw.polygon(img, (220, 150, 255), pts, 2)
        # Healing cross in center
        pygame.draw.rect(img, (255, 255, 255), (cx - 1, cy - 4, 3, 8))
        pygame.draw.rect(img, (255, 255, 255), (cx - 4, cy - 1, 8, 3))
        self.image = make_neon_sprite(img, (180, 50, 255), glow_size=4)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 70 + wave * 2; self.health = self.max_health
        self.speed = 1.5 + wave * 0.03; self.damage = 8
        self.heal_radius = 150; self.heal_amount = 2 + wave // 10
        self.heal_timer = 0; self.heal_delay = 30  # Heal every 0.5s

    def update(self):
        # Stay near other enemies, not directly chasing player
        # Move toward the closest non-leech enemy
        tx, ty = self._get_target()  # fallback
        super().update()
        self.heal_timer -= self._dt

    def can_heal(self):
        if self.heal_timer <= 0:
            self.heal_timer = self.heal_delay
            return True
        return False

    def get_xp_drop_count(self): return max(5, 5 + self.max_health // 6)


# ─────────── NEW: PHASE WRAITH (wave 75+) ───────────
class PhaseWraith(Enemy):
    """Crescent-shaped enemy that phases in/out. Invulnerable while phased out."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (26, 26); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Crescent moon shape
        pygame.draw.circle(img, (120, 200, 255), (13, 13), 11)
        pygame.draw.circle(img, (0, 0, 0, 0), (17, 10), 9)  # Cutout
        # Glowing eye
        pygame.draw.circle(img, (255, 255, 255), (9, 13), 2)
        self.base_image = make_neon_sprite(img, (120, 200, 255), glow_size=4)
        # Ghost/faded version
        self.ghost_image = self.base_image.copy()
        self.ghost_image.set_alpha(50)
        self.image = self.base_image
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 45 + wave; self.health = self.max_health
        self.speed = 3.0 + wave * 0.06; self.damage = 18
        self.phased_out = False
        self.phase_timer = random.randint(60, 120)
        self.phase_duration = 60  # 1 sec phased out
        self.visible_duration = random.randint(90, 150)

    def take_damage(self, amount):
        if self.phased_out:
            return False  # Invulnerable!
        return super().take_damage(amount)

    def update(self):
        self.phase_timer -= self._dt
        if self.phased_out:
            if self.phase_timer <= 0:
                self.phased_out = False
                self.phase_timer = self.visible_duration
                self.image = self.base_image
        else:
            if self.phase_timer <= 0:
                self.phased_out = True
                self.phase_timer = self.phase_duration
                self.image = self.ghost_image
        # Always chase, but faster when phased
        tx, ty = self._get_target()
        dx = tx - self.rect.centerx; dy = ty - self.rect.centery
        d = math.hypot(dx, dy)
        spd = self.speed * (1.5 if self.phased_out else 1.0) * self._dt
        if d > 0:
            self.rect.x += (dx / d) * spd
            self.rect.y += (dy / d) * spd

    def get_xp_drop_count(self): return max(3, 3 + self.max_health // 6)


# ─────────── NEW: CHARGER BULL (wave 80+) ───────────
class ChargerBull(Enemy):
    """Pentagon bull that telegraphs a charge line, then blitzes across the arena."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (32, 28); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Pentagon / bull shape
        pts = [(16, 0), (32, 10), (28, 28), (4, 28), (0, 10)]
        pygame.draw.polygon(img, (220, 50, 30), pts)
        pygame.draw.polygon(img, (255, 120, 80), pts, 2)
        # Horns
        pygame.draw.line(img, (255, 200, 100), (4, 10), (0, 0), 3)
        pygame.draw.line(img, (255, 200, 100), (28, 10), (32, 0), 3)
        # Eye
        pygame.draw.circle(img, (255, 255, 0), (16, 14), 3)
        pygame.draw.circle(img, (0, 0, 0), (16, 14), 1)
        self.image = make_neon_sprite(img, (255, 60, 30), glow_size=3)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 60 + wave; self.health = self.max_health
        self.speed = 1.8 + wave * 0.04; self.damage = 25
        # States: stalking -> telegraph -> charging -> stunned
        self.state = "stalking"
        self.telegraph_timer = 0; self.telegraph_time = 45  # 0.75s warning
        self.charge_dir = (0, 0); self.charge_speed = 14 + wave * 0.15
        self.charge_timer = 0; self.charge_time = 40  # 0.67s charge
        self.stun_timer = 0; self.stun_time = 90  # 1.5s rest
        self.telegraph_target = (0, 0)

    def update(self):
        tx, ty = self._get_target()
        if self.state == "stalking":
            # Approach slowly
            dx = tx - self.rect.centerx; dy = ty - self.rect.centery
            d = math.hypot(dx, dy)
            if d > 0:
                self.rect.x += (dx/d) * self.spd
                self.rect.y += (dy/d) * self.spd
            if d < 250:
                self.state = "telegraph"
                self.telegraph_timer = self.telegraph_time
                self.telegraph_target = (tx, ty)
        elif self.state == "telegraph":
            self.telegraph_timer -= self._dt
            self.telegraph_target = (tx, ty)  # Track during telegraph
            if self.telegraph_timer <= 0:
                dx = self.telegraph_target[0] - self.rect.centerx
                dy = self.telegraph_target[1] - self.rect.centery
                d = math.hypot(dx, dy) or 1
                self.charge_dir = (dx/d, dy/d)
                self.state = "charging"
                self.charge_timer = self.charge_time
        elif self.state == "charging":
            self.rect.x += self.charge_dir[0] * self.charge_speed
            self.rect.y += self.charge_dir[1] * self.charge_speed
            self.charge_timer -= self._dt
            if self.charge_timer <= 0:
                self.state = "stunned"
                self.stun_timer = self.stun_time
        elif self.state == "stunned":
            self.stun_timer -= self._dt
            if self.stun_timer <= 0:
                self.state = "stalking"

    def get_xp_drop_count(self): return max(3, 3 + self.max_health // 6)


# ─────────── NEW: MIMIC GEM (wave 85+) ───────────
class MimicEnemy(Enemy):
    """Disguised as a green XP gem. Reveals and attacks when player approaches."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        # Disguised form — looks like a big juicy gem
        sz = (20, 20)
        self.disguise_img = pygame.Surface(sz, pygame.SRCALPHA)
        # Diamond gem shape
        pts = [(10, 0), (20, 10), (10, 20), (0, 10)]
        pygame.draw.polygon(self.disguise_img, (57, 255, 20), pts)
        pygame.draw.polygon(self.disguise_img, (150, 255, 150), pts, 2)
        pygame.draw.circle(self.disguise_img, (200, 255, 200), (10, 7), 3)
        self.disguise_img = make_neon_sprite(self.disguise_img, (57, 255, 20), glow_size=5)
        # Revealed form — toothy mouth
        self.reveal_img = pygame.Surface((28, 28), pygame.SRCALPHA)
        # Spiky circle
        cx, cy = 14, 14
        for i in range(12):
            a = math.radians(30 * i)
            r_out = 12 if i % 2 == 0 else 8
            x1 = cx + int(r_out * math.cos(a))
            y1 = cy + int(r_out * math.sin(a))
            a2 = math.radians(30 * (i + 1))
            r_out2 = 12 if (i+1) % 2 == 0 else 8
            x2 = cx + int(r_out2 * math.cos(a2))
            y2 = cy + int(r_out2 * math.sin(a2))
            pygame.draw.line(self.reveal_img, (255, 50, 50), (x1, y1), (x2, y2), 2)
        # Angry eyes
        pygame.draw.circle(self.reveal_img, (255, 255, 0), (10, 10), 3)
        pygame.draw.circle(self.reveal_img, (255, 255, 0), (18, 10), 3)
        pygame.draw.circle(self.reveal_img, (0, 0, 0), (10, 10), 1)
        pygame.draw.circle(self.reveal_img, (0, 0, 0), (18, 10), 1)
        self.reveal_img = make_neon_sprite(self.reveal_img, (255, 50, 50), glow_size=4)
        self.image = self.disguise_img
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 30 + wave; self.health = self.max_health
        self.speed = 0; self.damage = 20
        self.revealed = False
        self.reveal_range = 80; self.chase_speed = 5.0 + wave * 0.08

    def update(self):
        tx, ty = self._get_target()
        d = math.hypot(tx - self.rect.centerx, ty - self.rect.centery)
        if not self.revealed:
            # Drift slowly toward center to look natural
            cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            dx = cx - self.rect.centerx; dy = cy - self.rect.centery
            dd = math.hypot(dx, dy)
            if dd > 50:
                self.rect.x += (dx / dd) * 0.3
                self.rect.y += (dy / dd) * 0.3
            if d < self.reveal_range:
                self.revealed = True
                self.image = self.reveal_img
                old_c = self.rect.center
                self.rect = self.image.get_rect(center=old_c)
        else:
            # Aggressive chase
            if d > 0:
                dx = tx - self.rect.centerx; dy = ty - self.rect.centery
                self.rect.x += (dx / d) * self.chase_speed
                self.rect.y += (dy / d) * self.chase_speed

    def get_xp_drop_count(self): return max(2, 2 + self.max_health // 8)


# ─────────── NEW: ORBITER (wave 90+) ───────────
class OrbiterEnemy(Enemy):
    """Has orbiting shield orbs that block incoming bullets."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (30, 30); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Ringed planet shape
        pygame.draw.circle(img, (200, 100, 0), (15, 15), 10)
        pygame.draw.circle(img, (255, 160, 50), (15, 15), 10, 2)
        # Ring
        pygame.draw.ellipse(img, (255, 200, 80), (2, 10, 26, 10), 2)
        pygame.draw.circle(img, (255, 220, 150), (12, 12), 3)
        self.image = make_neon_sprite(img, (255, 160, 50), glow_size=4)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 90 + wave * 2; self.health = self.max_health
        self.speed = 1.8 + wave * 0.04; self.damage = 15
        self.orb_count = 3 + min(3, wave // 30)  # 3-6 orbs
        self.orb_angle = 0; self.orb_radius = 40; self.orb_speed = 0.05
        # Each orb has HP — gets destroyed when hit
        self.orb_hp = [8 + wave // 5] * self.orb_count

    def get_orb_positions(self):
        """Get world positions of each living orb."""
        positions = []
        for i in range(self.orb_count):
            if self.orb_hp[i] > 0:
                a = self.orb_angle + (i / self.orb_count) * math.pi * 2
                ox = self.rect.centerx + int(math.cos(a) * self.orb_radius)
                oy = self.rect.centery + int(math.sin(a) * self.orb_radius)
                positions.append((ox, oy, i))
        return positions

    def damage_orb(self, idx, amount):
        """Damage a specific orb. Returns True if destroyed."""
        self.orb_hp[idx] -= amount
        return self.orb_hp[idx] <= 0

    def update(self):
        super().update()
        self.orb_angle += self.orb_speed

    def get_xp_drop_count(self): return max(5, 5 + self.max_health // 8)


# ─────────── NEW: SNIPER (wave 95+) ───────────
class SniperEnemy(Enemy):
    """Stays at long range, shows laser sight, fires deadly accurate shots."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (20, 30); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Tall thin shape — scope/rifle silhouette
        pygame.draw.rect(img, (180, 0, 0), (7, 0, 6, 30))
        pygame.draw.rect(img, (255, 60, 60), (7, 0, 6, 30), 2)
        # Scope circle
        pygame.draw.circle(img, (255, 0, 0), (10, 5), 5, 2)
        pygame.draw.circle(img, (255, 100, 100), (10, 5), 2)
        # Legs
        pygame.draw.line(img, (180, 0, 0), (3, 30), (10, 22), 2)
        pygame.draw.line(img, (180, 0, 0), (17, 30), (10, 22), 2)
        self.image = make_neon_sprite(img, (255, 0, 0), glow_size=3)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 40 + wave; self.health = self.max_health
        self.speed = 1.5 + wave * 0.03; self.damage = 10
        self.preferred_dist = 350  # Tries to stay far
        self.shoot_timer = 0; self.shoot_delay = max(50, 100 - wave)
        self.aim_target = (0, 0)

    def update(self):
        tx, ty = self._get_target()
        self.aim_target = (tx, ty)
        dx = tx - self.rect.centerx; dy = ty - self.rect.centery
        d = math.hypot(dx, dy)
        if d > 0:
            if d < self.preferred_dist - 50:
                # Too close — retreat
                self.rect.x -= (dx / d) * self.spd * 1.5
                self.rect.y -= (dy / d) * self.spd * 1.5
            elif d > self.preferred_dist + 100:
                # Too far — approach
                self.rect.x += (dx / d) * self.spd
                self.rect.y += (dy / d) * self.spd
            else:
                # Strafe perpendicular
                self.rect.x += (-dy / d) * self.spd * 0.5
                self.rect.y += (dx / d) * self.spd * 0.5
        self.rect.clamp_ip(pygame.Rect(5, 5, SCREEN_WIDTH-10, SCREEN_HEIGHT-10))
        self.shoot_timer -= self._dt

    def can_shoot(self):
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_delay
            return True
        return False

    def get_xp_drop_count(self): return max(3, 3 + self.max_health // 6)


# ─────────── NEW: PARASITE (wave 100+) ───────────
class ParasiteEnemy(Enemy):
    """Tiny creature that latches onto another enemy, buffing it massively."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz = (12, 12); img = pygame.Surface(sz, pygame.SRCALPHA)
        # Tick/parasite shape — small spiky blob
        pygame.draw.circle(img, (200, 0, 200), (6, 6), 5)
        # Little legs
        for a in range(0, 360, 45):
            rad = math.radians(a)
            x1 = 6 + int(4 * math.cos(rad))
            y1 = 6 + int(4 * math.sin(rad))
            x2 = 6 + int(6 * math.cos(rad))
            y2 = 6 + int(6 * math.sin(rad))
            pygame.draw.line(img, (255, 100, 255), (x1, y1), (x2, y2), 1)
        pygame.draw.circle(img, (255, 200, 255), (6, 4), 2)
        self.image = make_neon_sprite(img, (200, 0, 200), glow_size=3)
        self.rect = self.image.get_rect(); self._spawn_at_edge()
        self.max_health = 15 + wave // 3; self.health = self.max_health
        self.speed = 4.0 + wave * 0.05; self.damage = 3
        self.host_enemy = None  # The enemy we're riding
        self.attached = False
        self.buff_speed = 2.0  # Speed multiplier for host
        self.buff_damage = 1.5  # Damage multiplier for host
        self._original_host_speed = 0
        self._original_host_damage = 0

    def find_host(self, enemies_grp):
        """Find nearest non-parasite, non-boss enemy to latch onto."""
        best = None; best_d = 999999
        for e in enemies_grp:
            if e is self or isinstance(e, (ParasiteEnemy, Boss)) or getattr(e, 'is_boss', False):
                continue
            if getattr(e, '_has_parasite', False):
                continue
            d = math.hypot(e.rect.centerx - self.rect.centerx, e.rect.centery - self.rect.centery)
            if d < best_d:
                best_d = d; best = e
        return best

    def attach(self, host):
        self.host_enemy = host; self.attached = True
        host._has_parasite = True
        self._original_host_speed = host.speed
        self._original_host_damage = host.damage
        host.speed *= self.buff_speed
        host.damage = int(host.damage * self.buff_damage)

    def detach(self):
        if self.host_enemy and self.host_enemy.alive():
            self.host_enemy.speed = self._original_host_speed
            self.host_enemy.damage = self._original_host_damage
            self.host_enemy._has_parasite = False
        self.host_enemy = None; self.attached = False

    def take_damage(self, amount):
        dead = super().take_damage(amount)
        if dead:
            self.detach()
        return dead

    def update(self):
        if self.attached and self.host_enemy:
            if not self.host_enemy.alive():
                self.detach()
            else:
                # Ride on top of host
                self.rect.center = (self.host_enemy.rect.centerx,
                                     self.host_enemy.rect.top - 4)
                return
        # Not attached — chase toward nearest enemy to latch
        # (Handled in game loop for access to enemies_grp)
        # Fallback: chase player
        tx, ty = self._get_target()
        dx = tx - self.rect.centerx; dy = ty - self.rect.centery
        d = math.hypot(dx, dy)
        if d > 0:
            self.rect.x += (dx / d) * self.spd
            self.rect.y += (dy / d) * self.spd

    def get_xp_drop_count(self): return 1


# ═══════════ BOSS-THEMED MINIONS (appear wave after boss) ═══════════

class BossMinion(Enemy):
    """Wave 11+ — mini boss. Tough, shoots slow projectiles."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(24,24); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(180,0,255),(12,12),10)
        pygame.draw.circle(img,(220,80,255),(12,12),10,2)
        pygame.draw.circle(img,(255,180,255),(12,8),3)
        self.image=make_neon_sprite(img,(180,0,255),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=30+wave*2; self.health=self.max_health
        self.speed=2.0+wave*0.04; self.damage=12
        self.shoot_cooldown=0; self.shoot_delay=max(50,100-wave)
    def update(self):
        super().update()
        if self.shoot_cooldown>0: self.shoot_cooldown-=self._dt
    def can_shoot(self):
        if self.shoot_cooldown<=0: self.shoot_cooldown=self.shoot_delay; return True
        return False
    def shoot(self,tx=0,ty=0): pass

class HydraSpawnling(Enemy):
    """Wave 21+ — splits into 2 tiny blobs on death."""
    def __init__(self, player, wave, size='normal'):
        super().__init__(player, wave)
        self.size = size
        if size == 'normal':
            sz=(20,20); c=(0,200,80)
            self.max_health=25+wave; self.speed=2.5+wave*0.05; self.damage=10
        else:
            sz=(12,12); c=(80,255,120)
            self.max_health=10+wave//2; self.speed=3.5+wave*0.06; self.damage=6
        img=pygame.Surface(sz,pygame.SRCALPHA)
        r=sz[0]//2
        pygame.draw.circle(img,c,(r,r),r-1)
        pygame.draw.circle(img,(200,255,200),(r,r),r-1,2)
        self.image=make_neon_sprite(img,(57,255,20),glow_size=2)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.health=self.max_health

class PhantomWisp(Enemy):
    """Wave 31+ — teleports occasionally, shoots one projectile."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(18,18); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(160,80,220),(9,9),7,2)
        pygame.draw.circle(img,(200,150,255),(9,6),3)
        self.image=make_neon_sprite(img,(160,80,220),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=20+wave; self.health=self.max_health
        self.speed=2.2+wave*0.04; self.damage=10
        self.tp_timer=random.randint(100,180)
        self.shoot_cooldown=0; self.shoot_delay=max(60,120-wave)
    def update(self):
        super().update()
        self.tp_timer-=self._dt; self.shoot_cooldown-=self._dt
        if self.tp_timer<=0:
            tx,ty=self._get_target()
            self.rect.centerx=tx+random.randint(-120,120)
            self.rect.centery=ty+random.randint(-120,120)
            self.rect.clamp_ip(pygame.Rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT))
            self.tp_timer=random.randint(100,180)
    def can_shoot(self):
        if self.shoot_cooldown<=0: self.shoot_cooldown=self.shoot_delay; return True
        return False
    def shoot(self,tx=0,ty=0): pass

class FortressGuard(Enemy):
    """Wave 41+ — very tanky with a shield, slow."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(28,28); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.rect(img,(100,100,140),(2,2,24,24),border_radius=4)
        pygame.draw.rect(img,(150,150,220),(2,2,24,24),2,border_radius=4)
        # Shield cross
        pygame.draw.line(img,(200,200,255),(14,4),(14,24),2)
        pygame.draw.line(img,(200,200,255),(4,14),(24,14),2)
        self.image=make_neon_sprite(img,(150,150,220),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=80+wave*3; self.health=self.max_health
        self.speed=0.8+wave*0.02; self.damage=18
        self.shield_hp=40+wave; self.shield_max=40+wave
    def take_damage(self, amount):
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)
            self.shield_hp -= absorbed
            amount -= absorbed
        if amount > 0:
            return super().take_damage(amount)
        return False

class StormWisp(Enemy):
    """Wave 51+ — fast, periodically fires 4 projectiles in a cross."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(16,16); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(50,150,255),(8,8),6)
        # Lightning bolts
        for a in [0,90,180,270]:
            rad=math.radians(a)
            pygame.draw.line(img,(150,220,255),(8+int(3*math.cos(rad)),8+int(3*math.sin(rad))),
                             (8+int(7*math.cos(rad)),8+int(7*math.sin(rad))),1)
        self.image=make_neon_sprite(img,(0,200,255),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=25+wave; self.health=self.max_health
        self.speed=3.5+wave*0.06; self.damage=8
        self.ring_timer=0; self.ring_delay=max(60,120-wave); self.ring_count=4
    def update(self):
        super().update(); self.ring_timer-=1
    def can_ring(self):
        if self.ring_timer<=0: self.ring_timer=self.ring_delay; return True
        return False

class VoidLing(Enemy):
    """Wave 61+ — small void creature that gently pulls the player."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(18,18); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(60,0,80),(9,9),7)
        pygame.draw.circle(img,(120,0,200),(9,9),7,2)
        pygame.draw.circle(img,(200,100,255),(9,9),3)
        self.image=make_neon_sprite(img,(120,0,200),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=30+wave; self.health=self.max_health
        self.speed=2.0+wave*0.04; self.damage=12
        self.pull_strength=0.8+wave*0.01; self.pull_radius=120

class InfernoImp(Enemy):
    """Wave 71+ — fast fire imp, shoots fireballs."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(18,22); img=pygame.Surface(sz,pygame.SRCALPHA)
        # Flame shape
        pts=[(9,0),(16,10),(14,22),(4,22),(2,10)]
        pygame.draw.polygon(img,(255,80,0),pts)
        pygame.draw.polygon(img,(255,180,50),pts,2)
        pygame.draw.circle(img,(255,255,100),(9,12),3)
        self.image=make_neon_sprite(img,(255,100,0),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=25+wave; self.health=self.max_health
        self.speed=3.5+wave*0.06; self.damage=14
        self.shoot_cooldown=0; self.shoot_delay=max(40,80-wave)
    def update(self):
        super().update()
        if self.shoot_cooldown>0: self.shoot_cooldown-=self._dt
    def can_shoot(self):
        if self.shoot_cooldown<=0: self.shoot_cooldown=self.shoot_delay; return True
        return False
    def shoot(self,tx=0,ty=0): pass

class FrostShard(Enemy):
    """Wave 81+ — icy crystal that slows the player when nearby."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(20,20); img=pygame.Surface(sz,pygame.SRCALPHA)
        # Diamond / crystal shape
        pts=[(10,0),(20,10),(10,20),(0,10)]
        pygame.draw.polygon(img,(100,180,255),pts)
        pygame.draw.polygon(img,(180,220,255),pts,2)
        pygame.draw.circle(img,(220,240,255),(10,10),3)
        self.image=make_neon_sprite(img,(100,200,255),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=35+wave; self.health=self.max_health
        self.speed=2.0+wave*0.04; self.damage=10
        self.slow_radius=100; self.slow_factor=0.6

class ShadowShade(Enemy):
    """Wave 91+ — nearly invisible, appears briefly to strike then fades."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(22,22); img=pygame.Surface(sz,pygame.SRCALPHA)
        pygame.draw.circle(img,(40,40,60),(11,11),9)
        pygame.draw.circle(img,(80,80,120),(11,11),9,2)
        # Eyes
        pygame.draw.circle(img,(200,200,255),(8,9),2)
        pygame.draw.circle(img,(200,200,255),(14,9),2)
        self.base_image=make_neon_sprite(img,(80,80,120),glow_size=3)
        self.ghost_image=self.base_image.copy(); self.ghost_image.set_alpha(25)
        self.strike_image=self.base_image.copy()
        self.image=self.ghost_image
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=30+wave; self.health=self.max_health
        self.speed=3.0+wave*0.05; self.damage=22
        self.visible=False; self.vis_timer=0; self.invis_time=120; self.vis_time=40
    def take_damage(self, amount):
        if not self.visible: return False
        return super().take_damage(amount)
    def update(self):
        tx,ty=self._get_target()
        dx=tx-self.rect.centerx; dy=ty-self.rect.centery; d=math.hypot(dx,dy)
        spd=self.speed*(1.3 if not self.visible else 1.0)*self._dt
        if d>0: self.rect.x+=(dx/d)*spd; self.rect.y+=(dy/d)*spd
        self.vis_timer-=self._dt
        if self.visible:
            if self.vis_timer<=0: self.visible=False; self.vis_timer=self.invis_time; self.image=self.ghost_image
        else:
            if self.vis_timer<=0 or d<60:
                self.visible=True; self.vis_timer=self.vis_time; self.image=self.strike_image

class OmegaDrone(Enemy):
    """Wave 101+ — mini omega. Shoots + has small pull aura."""
    def __init__(self, player, wave):
        super().__init__(player, wave)
        sz=(22,22); img=pygame.Surface(sz,pygame.SRCALPHA)
        # Rainbow ring
        colors=[(255,0,0),(255,255,0),(0,255,0),(0,255,255),(0,0,255),(255,0,255)]
        for i,c in enumerate(colors):
            pygame.draw.arc(img,c,(2,2,18,18),math.radians(60*i),math.radians(60*(i+1)),2)
        pygame.draw.circle(img,(255,255,255),(11,11),4)
        self.image=make_neon_sprite(img,(200,150,255),glow_size=3)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=50+wave*2; self.health=self.max_health
        self.speed=2.5+wave*0.05; self.damage=15
        self.pull_strength=0.6; self.pull_radius=100
        self.shoot_cooldown=0; self.shoot_delay=max(40,80-wave)
    def update(self):
        super().update()
        if self.shoot_cooldown>0: self.shoot_cooldown-=self._dt
    def can_shoot(self):
        if self.shoot_cooldown<=0: self.shoot_cooldown=self.shoot_delay; return True
        return False
    def shoot(self,tx=0,ty=0): pass


# ═══════════════════ BOSSES ═══════════════════
def _make_boss_sprite(size, color, glow_color, glow_sz=6):
    img=pygame.Surface(size,pygame.SRCALPHA); cx,cy=size[0]//2,size[1]//2; r=min(cx,cy)-2
    pygame.draw.circle(img,color,(cx,cy),r); pygame.draw.circle(img,glow_color,(cx,cy),r,3)
    pygame.draw.circle(img,(255,255,255),(cx-r//3,cy-r//4),r//5)
    pygame.draw.circle(img,(255,255,255),(cx+r//3,cy-r//4),r//5)
    pygame.draw.circle(img,(0,0,0),(cx-r//3,cy-r//4),r//8)
    pygame.draw.circle(img,(0,0,0),(cx+r//3,cy-r//4),r//8)
    return make_neon_sprite(img,glow_color,glow_size=glow_sz)

class Boss(Enemy):
    def __init__(self, player, wave):
        super().__init__(player,wave); self.is_boss=True
        self.image=_make_boss_sprite((80,80),PURPLE,(180,0,255),6)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        _tier = wave // 10
        base_hp = 80 + (wave * 12)  # Much more HP
        self.max_health = int(base_hp * (1.0 + _tier * 0.8)); self.health=self.max_health
        self.speed=1.5+(wave*0.05); self.damage=int(35 * (1.0 + _tier * 0.4)); self.shoot_cooldown=0; self.shoot_delay=50
    def update(self):
        super().update()
        if self.shoot_cooldown>0: self.shoot_cooldown-=self._dt
    def can_shoot(self): return self.shoot_cooldown==0
    def shoot(self,tx=0,ty=0): self.shoot_cooldown=self.shoot_delay; return True
    def get_xp_drop_count(self): return max(10,10+self.max_health//5)
    def draw_health_bar(self, surf):
        bw=self.rect.width+20; bx=self.rect.centerx-bw//2; by=self.rect.y-12
        r=max(0,self.health/self.max_health)
        c=(57,255,20) if r>0.5 else (255,255,0) if r>0.25 else (255,30,60)
        pygame.draw.rect(surf,(15,15,25),(bx,by,bw,8)); pygame.draw.rect(surf,c,(bx,by,int(bw*r),8))
        pygame.draw.rect(surf,(180,0,255),(bx,by,bw,8),1)

class HydraBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((90,90),(0,180,80),(57,255,20),7)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=900+wave*24; self.health=self.max_health; self.speed=1.8; self.damage=30; self.shoot_delay=80
        self.is_hydra_parent=True

class HydraMini(Boss):
    def __init__(self, player, wave, pos):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((50,50),(0,200,100),(100,255,120),4)
        self.rect=self.image.get_rect(); self.rect.center=pos
        self.max_health=360+wave*9; self.health=self.max_health; self.speed=2.5; self.damage=15; self.shoot_delay=60
        self.is_hydra_parent=False

class PhantomBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((85,85),(120,50,200),(200,100,255),7)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=1500+wave*30; self.health=self.max_health; self.speed=1.0; self.damage=33; self.shoot_delay=45
        self.tp_timer=120; self.spread_count=5
    def update(self):
        super().update(); self.tp_timer-=self._dt
        if self.tp_timer<=0:
            tx,ty=self._get_target()
            self.rect.centerx=tx+random.randint(-200,200); self.rect.centery=ty+random.randint(-200,200)
            self.rect.clamp_ip(pygame.Rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)); self.tp_timer=random.randint(90,150)

class FortressBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((100,100),(100,100,140),(150,150,220),8)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=3000+wave*45; self.health=self.max_health; self.speed=0.6; self.damage=45; self.shoot_delay=50
        self.spawn_timer=180; self.spawn_delay=150
    def update(self): super().update(); self.spawn_timer-=1
    def can_spawn_minion(self):
        if self.spawn_timer<=0: self.spawn_timer=self.spawn_delay; return True
        return False

class StormBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((85,85),(50,150,255),(0,200,255),7)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=2400+wave*36; self.health=self.max_health; self.speed=2.5; self.damage=38; self.shoot_delay=30
        self.ring_timer=0; self.ring_delay=120; self.ring_count=12
    def update(self): super().update(); self.ring_timer-=1
    def can_ring(self):
        if self.ring_timer<=0: self.ring_timer=self.ring_delay; return True
        return False

class VoidBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((95,95),(40,0,60),(120,0,200),8)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=3600+wave*45; self.health=self.max_health; self.speed=1.0; self.damage=45
        self.pull_strength=3.0; self.pull_radius=300; self.shoot_delay=40
        self.ring_timer=0; self.ring_delay=90; self.ring_count=16
    def update(self): super().update(); self.ring_timer-=1
    def can_ring(self):
        if self.ring_timer<=0: self.ring_timer=self.ring_delay; return True
        return False

class InfernoBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((85,85),(200,60,0),(255,100,0),7)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=4500+wave*54; self.health=self.max_health; self.speed=2.0; self.damage=38; self.shoot_delay=15
        self.trail_timer=0
    def update(self): super().update(); self.trail_timer+=1

class FrostBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        self.image=_make_boss_sprite((90,90),(100,180,255),(150,220,255),7)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=5400+wave*60; self.health=self.max_health; self.speed=1.2; self.damage=33; self.shoot_delay=35
        self.slow_radius=250; self.slow_factor=0.5; self.spread_count=8
        self.ring_timer=0; self.ring_delay=100; self.ring_count=10
    def update(self): super().update(); self.ring_timer-=1
    def can_ring(self):
        if self.ring_timer<=0: self.ring_timer=self.ring_delay; return True
        return False

class ShadowBoss(Boss):
    def __init__(self, player, wave, is_clone=False):
        super().__init__(player,wave)
        col=(60,60,80) if is_clone else (30,30,50); gcol=(100,100,150) if is_clone else (80,80,120)
        self.image=_make_boss_sprite((80,80),col,gcol,6)
        if is_clone: self.image.set_alpha(160)
        self.rect=self.image.get_rect(); self._spawn_at_edge(); self.is_clone=is_clone
        self.max_health=(600 if is_clone else 2000)+wave*20; self.health=self.max_health
        self.speed=2.0 if is_clone else 1.5; self.damage=20; self.shoot_delay=40
        self.clone_timer=300; self.clone_delay=300; self.max_clones=3
    def update(self):
        super().update()
        if not self.is_clone: self.clone_timer-=1
    def can_clone(self):
        if not self.is_clone and self.clone_timer<=0: self.clone_timer=self.clone_delay; return True
        return False

class OmegaBoss(Boss):
    def __init__(self, player, wave):
        super().__init__(player,wave)
        sz=(110,110); img=pygame.Surface(sz,pygame.SRCALPHA); cx,cy=55,55
        colors=[(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,255,255),(0,0,255),(148,0,211)]
        for i,c in enumerate(colors): pygame.draw.circle(img,(*c,40),(cx,cy),50-i*5,3)
        pygame.draw.circle(img,(255,255,255),(cx,cy),15)
        pygame.draw.circle(img,(0,0,0),(cx-6,cy-3),4); pygame.draw.circle(img,(0,0,0),(cx+6,cy-3),4)
        self.image=make_neon_sprite(img,(255,200,255),glow_size=10)
        self.rect=self.image.get_rect(); self._spawn_at_edge()
        self.max_health=15000+wave*90; self.health=self.max_health; self.speed=1.8; self.damage=60; self.shoot_delay=20
        self.tp_timer=200; self.ring_timer=0; self.ring_delay=60; self.ring_count=20
        self.spawn_timer=250; self.spawn_delay=200; self.pull_strength=2.0; self.pull_radius=350
    def update(self):
        super().update(); self.tp_timer-=self._dt; self.ring_timer-=1; self.spawn_timer-=1
        if self.tp_timer<=0:
            tx,ty=self._get_target()
            self.rect.centerx=tx+random.randint(-250,250); self.rect.centery=ty+random.randint(-250,250)
            self.rect.clamp_ip(pygame.Rect(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)); self.tp_timer=random.randint(150,250)
    def can_ring(self):
        if self.ring_timer<=0: self.ring_timer=self.ring_delay; return True
        return False
    def can_spawn_minion(self):
        if self.spawn_timer<=0: self.spawn_timer=self.spawn_delay; return True
        return False

def create_boss_for_wave(player, wave):
    m={20:HydraBoss,30:PhantomBoss,40:FortressBoss,50:StormBoss,
       60:VoidBoss,70:InfernoBoss,80:FrostBoss,90:ShadowBoss,100:OmegaBoss}
    return m.get(wave,Boss)(player,wave)