import pygame
import numpy as np
import random, math, os
import keyboard as k
from attrdict import AttrDict
import math
import pickle

from abc import ABC, abstractmethod

pygame.init()
pygame.display.set_mode((1, 1))  # Minimal dummy window


def darken(color, scale=0.8):
    return tuple(c*scale for c in color)

def polygon(center, radius, n, flip=1):
    radius = radius/math.cos(math.pi/n)
    cx,cy = center
    points = []
    for i in range(n):
        angle = 2*math.pi * (i+0.5)/n
        x = radius * math.cos(angle) * flip
        y = radius * math.sin(angle)
            
        points.append((x+cx, y+cy))
    return points

def cast(value: str):
    value = value.strip()

    # Try boolean first
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False

    # Try integer
    try:
        return int(value)
    except ValueError:
        return value  # Return original string if no match
        
pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # allow many sounds

assets_folder = "assets/sounds"
sound_files = [f for f in os.listdir(assets_folder) if f.endswith((".ogg"))]
sounds = {}
sound_to_idx = {}
idx_to_sound = {}
idx = 0
for file in sound_files:
    f = file
    file = file.split("/")[-1].split(".")[0]
    n = 0
    for n in range(len(file)):
        if file[n].isdigit():
            break
    
    if not file[n].isdigit():
        file = file + "0"
        n += 1
    sound, num = file[:n], file[n:]
    if sound not in sounds:
        sounds[sound] = []
        sound_to_idx[sound] = idx
        idx_to_sound[idx] = sound
        idx += 1
    sounds[sound].append(pygame.mixer.Sound(os.path.join(assets_folder, f)))

class SoundUtils:

    sounds = sounds
    sound_to_idx = sound_to_idx
    idx_to_sound = idx_to_sound

    @staticmethod
    def encodeSoundID(sound):
        return SoundUtils.sound_to_idx[sound]

    @staticmethod
    def decodeSoundID(sound_id):
        sound = SoundUtils.idx_to_sound[sound_id]
        return random.choice(SoundUtils.sounds[sound])

    @staticmethod
    def playSound(sound_id, dist, scale):
        sound = SoundUtils.decodeSoundID(sound_id)
        channel = sound.play()
        if channel:  # if a free channel was available
            volume = scale * max(0, min(1, 1 - 0.5*dist/300))
            channel.set_volume(volume)

        

cache_folder = "assets_cache"

image_files = [f for f in os.listdir(cache_folder) if f.endswith((".png", ".jpg", ".jpeg"))]
keys = [tuple(cast(v) for v in info[:-4].split('_')) for info in image_files]

sprites = {
    "raider": pygame.image.load("assets/raider.png"),
    "defender": pygame.image.load("assets/defender.png"),
    "sword": pygame.image.load("assets/sword.png"),
    "bow": pygame.image.load("assets/bow.png"),
    "axe": pygame.image.load("assets/axe.png"),
    "arrow": pygame.image.load("assets/arrow.png"),
}
for key, path in zip(keys, image_files):
    surf = pygame.image.load(os.path.join(cache_folder, path)).convert()
    surf.set_colorkey((0,0,0))
    sprites[key] = surf


class StaticDisplays:

    sprites = sprites

    @staticmethod
    def display(surface, pos, info):
        match info[0]:
            case -1:
                StaticDisplays.Player_staticDisplay(surface, pos, info)
            case 0:
                StaticDisplays.Heal_staticDisplay(surface, pos, info)
            case 1:
                StaticDisplays.Arrow_staticDisplay(surface, pos, info)
            case 2:
                StaticDisplays.ChargedArrow_staticDisplay(surface, pos, info)
            case 3:
                StaticDisplays.Bullet_staticDisplay(surface, pos, info)
            case 4:
                StaticDisplays.Frag_staticDisplay(surface, pos, info)
            case 5:
                StaticDisplays.Explosion_staticDisplay(surface, pos, info)
            case 6:
                StaticDisplays.Turret_staticDisplay(surface, pos, info)
            case 7:
                StaticDisplays.drawSprite(surface, "bush", pos, info[3], info[5])
            case 8:
                StaticDisplays.drawSprite(surface, "tree", pos, info[3], info[5])
            case 9:
                StaticDisplays.drawSprite(surface, "stone", pos, info[3], info[5])
            case 10:
                StaticDisplays.WoodWall_staticDisplay(surface, pos, info)
            case 11:
                StaticDisplays.StoneWall_staticDisplay(surface, pos, info)
            case 12:
                t = "spike2" if info[6] > 200 else "spike1"
                StaticDisplays.drawSprite(surface, t, pos, info[3], info[5])
            case 13:
                StaticDisplays.Base_staticDisplay(surface, pos, info)
    
    def drawSprite(surface, sprite, pos, health, hit):
        if health == -1:
            sprite_surface = StaticDisplays.sprites[(sprite, hit)]
        else:
            sprite_surface = StaticDisplays.sprites[(sprite, health, hit)]
        rect = sprite_surface.get_rect(center=pos)
        surface.blit(sprite_surface, rect)

    
    @staticmethod
    def Player_staticDisplay(surface, pos, info):
        x, y = pos
        # (type, x, y, health, angle, hit, r, g, b)
        _, _, _, health, angle, hit, r, g, b, active, attack_tick, frames, _, _ = info
        if health <= 0:
            return
        color = (r, g, b)
        dx, dy = 14*math.cos(angle), 14*math.sin(angle)

        windup = -40
        strike = 140
        rest = 0
        anticipation = 2
        attack_offset = 0

        match active:
            case 1:
                if attack_tick:
                    if attack_tick <= frames[2]:
                        scale = (frames[2] - attack_tick) / frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif attack_tick <= frames[1]+anticipation:
                        scale = (frames[1]+anticipation - attack_tick) / (frames[1]+anticipation-frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (frames[0] - attack_tick) / (frames[0]-frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                rotated_image = pygame.transform.rotate(StaticDisplays.sprites["sword"], -(angle)/math.pi*180-attack_offset)
                if frames[2] < attack_tick < frames[1]+anticipation:
                    rotated_image.fill((100, 100, 100, 0), special_flags=pygame.BLEND_RGBA_ADD)
                image_rect = rotated_image.get_rect()
                image_rect.center = pos
                surface.blit(rotated_image, image_rect)
            case 2:
                rotated_image = pygame.transform.rotate(StaticDisplays.sprites["bow"], -(angle)/math.pi*180)
                image_rect = rotated_image.get_rect()
                image_rect.center = pos
                surface.blit(rotated_image, image_rect)
                pygame.draw.circle(surface, (120, 80, 60), pos, 7.5)
            case 3:
                if attack_tick:
                    if attack_tick <= frames[2]:
                        scale = (frames[2] - attack_tick) / frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif attack_tick <= frames[1]+anticipation:
                        scale = (frames[1]+anticipation - attack_tick) / (frames[1]+anticipation-frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (frames[0] - attack_tick) / (frames[0]-frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                rotated_image = pygame.transform.rotate(StaticDisplays.sprites["axe"], -(angle)/math.pi*180-attack_offset)
                if frames[2] < attack_tick < frames[1]+anticipation:
                    rotated_image.fill((100, 100, 100, 0), special_flags=pygame.BLEND_RGBA_ADD)
                image_rect = rotated_image.get_rect()
                image_rect.center = pos
                surface.blit(rotated_image, image_rect)
            case 4:
                pygame.draw.circle(surface, (70,70,70), pos, 7.5)
            case 5:
                dist = 15 + 1.4*20 + 10
                dx, dy = dist*math.cos(angle), dist*math.sin(angle)
                pos2 = pos[0]+dx, pos[1]+dy
                StaticDisplays.WoodWall_staticDisplay(surface, pos2, (10,0,0,0,0,0,0,0,0))
            case 6:
                dist = 15 + 1.4*30 + 10
                dx, dy = dist*math.cos(angle), dist*math.sin(angle)
                pos2 = pos[0]+dx, pos[1]+dy
                StaticDisplays.StoneWall_staticDisplay(surface, pos2, (11,0,0,0,0,0,*color))
            case 7:
                dist = 15 + 1.4*17 + 10
                dx, dy = dist*math.cos(angle), dist*math.sin(angle)
                pos2 = pos[0]+dx, pos[1]+dy
                StaticDisplays.Spike_staticDisplay(surface, pos2, (12,0,0,0,0,0,*color))
            case 8:
                dist = 15 + 1.4*20 + 10
                dx, dy = dist*math.cos(angle), dist*math.sin(angle)
                pos2 = pos[0]+dx, pos[1]+dy
                StaticDisplays.Turret_staticDisplay(surface, pos2, (10,0,0,0,angle,0,*color))
            case 9:
                pygame.draw.circle(surface, (180, 120, 90), pos, 7.5)
        
        offset = 60 / 180 * math.pi
        attack_offset = attack_offset / 180 * math.pi
        dx2, dy2 = 14*math.cos(angle+offset+attack_offset), 14*math.sin(angle+offset+attack_offset)
        dx3, dy3 = 14*math.cos(angle-offset+attack_offset), 14*math.sin(angle-offset+attack_offset)

        border_color = darken(color)

        pygame.draw.circle(surface, [border_color, (255,255,255)][hit], np.add(pos, (dx2,dy2)), 7.5)
        pygame.draw.circle(surface, [border_color, (255,255,255)][hit], np.add(pos, (dx3,dy3)), 7.5)
        pygame.draw.circle(surface, [color, (255,255,255)][hit], np.add(pos, (dx2,dy2)), 6)
        pygame.draw.circle(surface, [color, (255,255,255)][hit], np.add(pos, (dx3,dy3)), 6)

        pygame.draw.circle(surface, [border_color, (255,255,255)][hit], pos, 15)
        pygame.draw.circle(surface, [color, (255,255,255)][hit], pos, 13.5)
    

    @staticmethod
    def Turret_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        color = (r, g, b)
        grey = (70, 70, 70)
        brown = (120, 80, 60)
        lightgrey = (130, 130, 130)
        border_color = darken(brown, 0.85)
        size = 20

        base_c = (255,255,255) if hit else brown
        inner_c = (255,255,255) if hit else lightgrey
        dark_g = darken(grey, 1.2)
        dark_g2 = darken(grey, 1.7)

        pygame.draw.circle(surface, [border_color, (255,255,255)][hit], (x,y), size)
        pygame.draw.circle(surface, [brown, (255,255,255)][hit], (x,y), size-3)

        d1 = (0.5*size*math.cos(angle+math.pi/2), 0.5*size*math.sin(angle+math.pi/2))
        d2 = (0.5*size*math.cos(angle-math.pi/2), 0.5*size*math.sin(angle-math.pi/2))
        p1 = (x,y)
        p2 = (x + 1.35*size*math.cos(angle), y + 1.35*size*math.sin(angle))
        coords = (np.add(p1,d1), np.add(p1,d2), np.add(p2,d2), np.add(p2,d1))
        pygame.draw.polygon(surface, [darken(grey), (255,255,255)][hit], coords)

        d1 = (0.4*size*math.cos(angle+math.pi/2), 0.4*size*math.sin(angle+math.pi/2))
        d2 = (0.4*size*math.cos(angle-math.pi/2), 0.4*size*math.sin(angle-math.pi/2))
        p2 = (x + 1.2*size*math.cos(angle), y + 1.2*size*math.sin(angle))
        coords = (np.add(p1,d1), np.add(p1,d2), np.add(p2,d2), np.add(p2,d1))
        pygame.draw.polygon(surface, [grey, (255,255,255)][hit], coords)
        pygame.draw.circle(surface, [dark_g, (255,255,255)][hit], (x,y), size/2+3)
        pygame.draw.circle(surface, [dark_g2, (255,255,255)][hit], (x,y), size/2)
        pygame.draw.circle(surface, [color, (255,255,255)][hit], (x,y), size/2-4)

    @staticmethod
    def Spike_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        color = (r, g, b)
        brown = (120, 80, 60)
        lightgrey = (130, 130, 130)
        size = 17

        def draw_triangle(flip):
            pygame.draw.polygon(surface, darken(lightgrey, 0.9), polygon((x,y), size-2, 3, flip))
            pygame.draw.polygon(surface, lightgrey, polygon((x,y), size-5, 3, flip))

        draw_triangle(1)
        draw_triangle(-1)
        pygame.draw.circle(surface, darken(brown, 0.94), (x,y), size+1.5)
        pygame.draw.circle(surface, darken(brown, 1.1), (x,y), size-1.5)
        pygame.draw.circle(surface, [color, (255,255,255)][hit], (x,y), size-9)

    @staticmethod
    def WoodWall_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        brown = (120, 80, 60)
        dark_brown = darken(brown, 0.87)
        white = (255,255,255)
        size = 20
        pygame.draw.polygon(surface, white if hit else dark_brown, polygon((x,y), size, 8))
        pygame.draw.polygon(surface, white if hit else brown, polygon((x,y), size-5, 8))

    @staticmethod
    def StoneWall_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        grey = (70,70,70)
        white = (255,255,255)
        color = (r,g,b)
        dark_grey = darken(grey, 0.95)
        mid_grey = darken(grey, 1.2)
        size = 30
        pygame.draw.polygon(surface, white if hit else dark_grey, polygon((x,y), size, 8))
        pygame.draw.polygon(surface, white if hit else color, polygon((x,y), size-5, 8))
        pygame.draw.polygon(surface, white if hit else mid_grey, polygon((x,y), size-9, 8))

    @staticmethod
    def Base_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        lightergrey = (180,180,180)
        white = (255,255,255)
        size = 40
        scale = max(info[3],0) / 100
        if scale:
            pygame.draw.circle(surface, (160, 185, 220), (x,y), size+8)
            pygame.draw.polygon(surface, white, polygon((x,y), scale*size+3, 8))
            pygame.draw.polygon(surface, [lightergrey, white][hit], polygon((x,y), scale*size, 8))
        else:
            pygame.draw.circle(surface, (170, 170, 170), (x,y), 48)

    @staticmethod
    def Arrow_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        rotated_image = pygame.transform.rotate(StaticDisplays.sprites["arrow"], -(angle)/math.pi*180)
        image_rect = rotated_image.get_rect()
        image_rect.center = pos
        surface.blit(rotated_image, image_rect)

    @staticmethod
    def ChargedArrow_staticDisplay(surface, pos, info):
        x, y = pos
        # identical visually to Arrow for simplicity
        StaticDisplays.Arrow_staticDisplay(surface, pos, info)

    @staticmethod
    def Bullet_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        lightgrey = (130,130,130)
        size = 10
        pygame.draw.circle(surface, darken(lightgrey, 0.85), (x,y), size)
        pygame.draw.circle(surface, lightgrey, (x,y), size-4)

    @staticmethod
    def Frag_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        white = (255,255,255)
        pygame.draw.circle(surface, white, (x,y), 12)

    @staticmethod
    def Explosion_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        white_alpha = (255,255,255,180)
        size = 80
        s = pygame.Surface((size*2,size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, white_alpha, (size,size), size)
        surface.blit(s, (x-size,y-size))

    @staticmethod
    def Heal_staticDisplay(surface, pos, info):
        x, y = pos
        _, _, _, health, angle, hit, r, g, b = info
        mutedlightred = (190,145,100)
        pygame.draw.circle(surface, mutedlightred, (x,y), 35)


class DUMMYPLAYER():
    def __init__(self):
        self.food = 0
        self.wood = 0
        self.stone = 0
        self.team = -1
    
    def changeHealth(self, v): pass
    def changeFood(self, v): pass
    def changeWood(self, v): pass
    def changeStone(self, v): pass

class Player():
    def __init__(self, env, pos, team, id_):
        self.costs = AttrDict({
            "arrow": 2,
            "frag": 10,
            "woodwall": 10,
            "stonewall": 20,
            "spike": (12, 12),
            "turret": (45, 30),
            "heal": 15,
        })

        self.id_ = id_
        self.name = f"Player {id_}"
        self.env = env
        self.pos = list(pos)
        self.team = team
        self.angle = 0
        self.size = 15
        self.color = self.env.colors[f"team{self.team}"]

        self.health = 20
        self.attack_tick = 0
        self.attack_frames = None
        self.attacking = False
        self.attack_size = 20
        self.frames = [0,0,0]
        
        self.speed = 4
        self.slow_speed = 2
        self.slow_duration = 15
        self.slow_tick = 0
        self.knockback_dir = (0,0)
        self.knockback_duration = 3
        self.knockback_tick = 0

        self.active = 1
        self.active_attack = -1

        self.axe_resource_bonus = 0.5
        self.axe_wall_bonus = 1
        

        self.food = 100
        self.wood = 200
        self.stone = 200

        self.hit = False
        self.consec_held = 0
        self.buffer = False

        self.last_active = 1

        self.hit_objects = set()
        self.kills = 0
        self.resetEvents()

    def resetEvents(self):
        self.events = AttrDict({
            "change_food": 0,
            "change_wood": 0,
            "change_stone": 0,
            "change_health": 0,
            "change_health_enemy_player": 0,
            "damage_dealt_enemy_structure": 0,
            "change_health_team_player": 0,
            "damage_dealt_team_structure": 0,
            "killed_enemy_player": 0,
            "died": 0,
            "self_damage_dealt_base": 0,
            "damage_dealt_base": 0,
        })
    
    def changeHealth(self, health):
        if health < 0:
            self.env.addSound("playerhurt", self.pos, 0.2)
        self.events.change_health += health
        self.health += health

    def changeFood(self, food):
        self.events.change_food += food
        self.food += food

    def changeWood(self, wood):
        self.events.change_wood += wood
        self.wood += wood

    def changeStone(self, stone):
        self.events.change_stone += stone
        self.stone += stone

    def step(self, ax, ay, active, action, angle):
        '''
        0: don't switch
        1: sword
        2: bow
        3: hammer
        4: frag
        5: wood wall
        6: stone wall
        7: spike
        8: turret
        9: heal
        '''
        self.objects = self.env.grid.getNearbyObjects(self.pos)
        
        if active:
            if active == 9 and self.active != 9:
                self.last_active = self.active 
            self.active = active
        self.angle = (self.angle + angle) % (2*math.pi)

        if self.buffer:
            action = 0
            self.buffer = False

        if action:
            self.consec_held += 1
            match self.active:
                case 1:
                    if self.active_attack == -1:
                        self.active_attack = 1
                        self.startAttack(damage=4, frames=(15,10,7))
                case 2:
                    if self.active_attack == -1 and self.wood >= self.costs.arrow:
                        self.changeWood(-self.costs.arrow)
                        self.active_attack = 2
                        self.startAttack(damage=4, frames=(25,18,17))
                case 3:
                    if self.active_attack == -1:
                        self.active_attack = 3
                        self.startAttack(damage=6, frames=(25,17,14))
                case 4:
                    if self.active_attack == -1 and self.stone >= self.costs.frag:
                        self.changeStone(-self.costs.frag)
                        self.active_attack = 4
                        self.startAttack(damage=5, frames=(12,11,10))
                case 5:
                    if self.wood >= self.costs.woodwall:
                        valid = self.place(WoodWall(self.env, (-1, -1), self.team))
                        if valid:
                            self.changeWood(-self.costs.woodwall)
                case 6:
                    if self.stone >= self.costs.stonewall:
                        valid = self.place(StoneWall(self.env, (-1, -1), self.team))
                        if valid:
                            self.changeStone(-self.costs.stonewall)
                case 7:
                    if self.wood >= self.costs.spike[0] and self.stone >= self.costs.spike[1]:
                        valid = self.place(Spike(self.env, (-1, -1), self.team, self))
                        if valid:
                            self.changeWood(-self.costs.spike[0])
                            self.changeStone(-self.costs.spike[1])
                case 8:
                    if self.wood >= self.costs.turret[0] and self.stone >= self.costs.turret[1]:
                        valid = self.place(Turret(self.env, (-1, -1), self.angle, self.team, self))
                        if valid:
                            self.changeWood(-self.costs.turret[0])
                            self.changeStone(-self.costs.turret[1])
                case 9:
                    if self.food >= self.costs.heal:
                        self.place(Heal(self.env, (-1, -1), self))
                        self.changeFood(-self.costs.heal)
                        self.active = self.last_active
                        action = 0
                        self.buffer = True                        
        else:
            self.consec_held = 0

        speed = [self.slow_speed, self.speed][self.slow_tick == 0]
        dx, dy = ax*speed, ay*speed
        self.pos = (self.pos[0]+self.knockback_dir[0]+dx, self.pos[1]+self.knockback_dir[1]+dy)
        self.updateMove()
        if self.slow_tick:
            self.slow_tick -= 1
        if self.knockback_tick:
            self.knockback_tick -= 1
        else:
            self.knockback_dir = (0,0)

        if self.attack_tick:
            self.attack_tick -= 1
        else:
            self.active_attack = -1

        if self.attack_tick \
           and self.frames[2] < self.attack_tick <= self.frames[1]:
            self.attacking = True
            self.attack()
        else:
            self.attacking = False
            self.hit_objects = set()
        

    def startAttack(self, damage, frames):
        self.damage = damage
        self.frames = frames
        self.attack_tick = frames[0]

    def attack(self):
        dx, dy = self.size*math.cos(self.angle), self.size*math.sin(self.angle)

        if self.active_attack in (1,3):
            p1 = np.add(self.pos, (dx,dy))
            p2 = np.add(self.pos, (2*dx,2*dy))
            p3 = np.add(self.pos, (3*dx,3*dy))
            for obj in self.objects + self.env.dynamic_objects:
                if isinstance(obj, Player) and obj.team == self.team:
                    continue
                if obj not in self.hit_objects and \
                   (isinstance(obj, StaticObject) or (type(obj) in (Turret,)) or (type(obj) in {Player, Base} and obj.team != self.team)) and \
                   (math.dist(obj.pos, p1) <= obj.size + self.attack_size or \
                   math.dist(obj.pos, p1) <= obj.size + self.attack_size or \
                   math.dist(obj.pos, p3) <= obj.size + self.attack_size):
                    if self.active_attack == 3: # axe has damage bonuses against objects
                        if type(obj) in self.env.resources: 
                            obj.recieveHit(self, self.damage * (1+self.axe_resource_bonus), self)
                        elif type(obj) in self.env.walls:
                            obj.recieveHit(self, self.damage * (1+self.axe_wall_bonus), self)
                        else:
                            obj.recieveHit(self, self.damage, self)
                    else:
                        obj.recieveHit(self, self.damage, self)
                    self.hit_objects.add(obj)

        if self.active_attack == 2:
            if self.consec_held >= 7 and self.wood >= 4:
                obj = ChargedArrow(self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
                self.changeWood(-4)
            else:
                obj = Arrow(self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
            self.place(obj)
        if self.active_attack == 4:
            obj = Frag(self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
            self.place(obj)
        
        if self.attack_tick == self.frames[1]:
            match self.active:
                case 1:
                    self.env.addSound("lightattack", self.pos, 0.2)
                case 2:
                    self.env.addSound("bowshoot", self.pos, 0.35)
                case 3:
                    self.env.addSound("heavyattack", self.pos, 0.2)
                case 4:
                    self.env.addSound("frag", self.pos, 0.4)

    
    def recieveHit(self, obj, damage, player):
        if self.health <= 0:
            return 
        self.hit = True
        damage = min(self.health, damage)
        self.changeHealth(-damage)

        if player.team == -1: pass
        elif self.team == player.team:
            player.events.change_health_team_player -= damage
        else:
            player.events.change_health_enemy_player -= damage

        if self.health <= 0:
            self.health = 0
            if self.team != player.team and player.team != -1:
                player.events.killed_enemy_player += 1
                player.changeFood(20 + self.food//6)
                player.changeWood(20 + self.wood//6)
                player.changeStone(20 + self.stone//6)
                player.kills += 1
            self.events.dead = 1
            self.env.removeDynamicObject(self)
            self.env.addSound("playerdie", self.pos, 0.8)

        if player.team != -1:
            knockback = 3
            dx, dy = self.pos[0]-obj.pos[0], self.pos[1]-obj.pos[1]
            mag = max(0.5, math.sqrt(dx*dx + dy*dy))
            dx, dy = dx * knockback / mag, dy * knockback / mag
            self.pos = (self.pos[0]+dx, self.pos[1]+dy)

            self.slow_tick = self.slow_duration
            self.knockback_dir = (dx, dy)
            self.knockback_tick = self.knockback_duration


    def place(self, obj, place=True):
        dist = self.size + 1.4*obj.size + 10
        dx, dy = dist*math.cos(self.angle), dist*math.sin(self.angle)
        obj.pos = np.add(self.pos, (dx,dy))

        if not place:
            return False

        if type(obj) in {WoodWall, StoneWall, Turret, Spike}:
            for obj2 in self.objects + self.env.dynamic_objects:
                if type(obj2) not in self.env.resources | self.env.walls | {Turret}:
                    continue
                if math.dist(obj.pos, obj2.pos) <= obj.size + obj2.size - 0.5:
                    return False


        if type(obj) in {Arrow, ChargedArrow, Frag, Turret, Spike}:
            self.env.addDynamicObject(obj)
            if isinstance(obj, Spike):
                self.env.addSound("turretplace", obj.pos, 0.6)
            if isinstance(obj, Turret):
                self.env.addSound("turretplace", obj.pos, 0.6)
        elif type(obj) in {WoodWall, StoneWall}:
            self.env.addObject(obj)
            if isinstance(obj, WoodWall):
                self.env.addSound("woodplace", obj.pos, 0.6)
            if isinstance(obj, StoneWall):
                self.env.addSound("stoneplace", obj.pos, 0.6)
        elif type(obj) in {Heal}:
            dist = self.size + 1.4*obj.size
            dx, dy = dist*math.cos(self.angle), dist*math.sin(self.angle)
            obj.pos = np.add(self.pos, (0.5*dx,0.5*dy))
            self.env.addEffect(obj)
        else:
            print(type(obj))

        return True

    def updateMove(self):
        for obj in self.objects + self.env.dynamic_objects:
            if obj is self:
                continue
            if type(obj) not in {Player, Turret} | self.env.resources | self.env.walls:
                continue
            if (d:=math.dist(obj.pos, self.pos)) <= obj.size + self.size - 0.5:
                d = max(0.1, d)
                mag = d
                d /= obj.size
                dx, dy = self.pos[0]-obj.pos[0], self.pos[1]-obj.pos[1]
                f = min(8/mag, 8/(mag*d*d))
                dx, dy = f*dx, f*dy
                newpos = (self.pos[0]+dx, self.pos[1]+dy)
                self.pos = newpos
        
        buffer = 100
        dx, dy = 0, 0
        if self.pos[0] < buffer:
            dx += 5
        if self.pos[0] > self.env.map_size[0] - buffer - 1:
            dx -= 5
        if self.pos[1] < buffer:
            dy += 5
        if self.pos[1] > self.env.map_size[1] - buffer - 1:
            dy -= 5
        self.pos = (self.pos[0]+dx, self.pos[1]+dy)

    def resetState(self):
        self.resetEvents()
        self.hit = False

    def display(self):
        dx, dy = 14*math.cos(self.angle), 14*math.sin(self.angle)

        windup = -40
        strike = 140
        rest = 0
        anticipation = 2
        attack_offset = 0

        match self.active:
            case 1:
                if self.attack_tick:
                    if self.attack_tick <= self.frames[2]:
                        scale = (self.frames[2] - self.attack_tick) / self.frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif self.attack_tick <= self.frames[1]+anticipation:
                        scale = (self.frames[1]+anticipation - self.attack_tick) / (self.frames[1]+anticipation-self.frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (self.frames[0] - self.attack_tick) / (self.frames[0]-self.frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                rotated_image = pygame.transform.rotate(self.env.sprites.sword, -(self.angle)/math.pi*180-attack_offset)
                if self.frames[2] < self.attack_tick < self.frames[1]+anticipation:
                    rotated_image.fill((100, 100, 100, 0), special_flags=pygame.BLEND_RGBA_ADD)
                image_rect = rotated_image.get_rect()
                image_rect.center = self.pos
                self.env.surface.blit(rotated_image, image_rect)
                #pygame.draw.circle(self.env.surface, self.env.colors.white, self.pos, self.size/2)
            case 2:
                rotated_image = pygame.transform.rotate(self.env.sprites.bow, -(self.angle)/math.pi*180)
                image_rect = rotated_image.get_rect()
                image_rect.center = self.pos
                self.env.surface.blit(rotated_image, image_rect)
                pygame.draw.circle(self.env.surface, self.env.colors.brown, self.pos, self.size/2)
            case 3:
                if self.attack_tick:
                    if self.attack_tick <= self.frames[2]:
                        scale = (self.frames[2] - self.attack_tick) / self.frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif self.attack_tick <= self.frames[1]+anticipation:
                        scale = (self.frames[1]+anticipation - self.attack_tick) / (self.frames[1]+anticipation-self.frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (self.frames[0] - self.attack_tick) / (self.frames[0]-self.frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                rotated_image = pygame.transform.rotate(self.env.sprites.axe, -(self.angle)/math.pi*180-attack_offset)
                if self.frames[2] < self.attack_tick < self.frames[1]+anticipation:
                    rotated_image.fill((100, 100, 100, 0), special_flags=pygame.BLEND_RGBA_ADD)
                image_rect = rotated_image.get_rect()
                image_rect.center = self.pos
                self.env.surface.blit(rotated_image, image_rect)
                #pygame.draw.circle(self.env.surface, self.env.colors.lightgrey, self.pos, self.size/2)
            case 4:
                pygame.draw.circle(self.env.surface, self.env.colors.grey, self.pos, self.size/2)
            case 5:
                obj = WoodWall(self.env, (-1, -1), self.team)
                self.place(obj, place=False)
                obj.display()
            case 6:
                obj = StoneWall(self.env, (-1, -1), self.team)
                self.place(obj, place=False)
                obj.display()
            case 7:
                obj = Spike(self.env, (-1, -1), self.team, self)
                self.place(obj, place=False)
                obj.display()
            case 8:
                obj = Turret(self.env, (-1, -1), self.angle, self.team, self)
                self.place(obj, place=False)
                obj.display()
            case 9:
                pygame.draw.circle(self.env.surface, self.env.colors.mutedlightred, self.pos, self.size/2)
        
        offset = 60 / 180 * math.pi
        attack_offset = attack_offset / 180 * math.pi
        dx2, dy2 = 14*math.cos(self.angle+offset+attack_offset), 14*math.sin(self.angle+offset+attack_offset)
        dx3, dy3 = 14*math.cos(self.angle-offset+attack_offset), 14*math.sin(self.angle-offset+attack_offset)

        border_color = darken(self.color)

        pygame.draw.circle(self.env.surface, [border_color, self.env.colors.white][self.hit], np.add(self.pos, (dx2,dy2)), self.size/2)
        pygame.draw.circle(self.env.surface, [border_color, self.env.colors.white][self.hit], np.add(self.pos, (dx3,dy3)), self.size/2)
        pygame.draw.circle(self.env.surface, [self.color, self.env.colors.white][self.hit], np.add(self.pos, (dx2,dy2)), self.size/2-1.5)
        pygame.draw.circle(self.env.surface, [self.color, self.env.colors.white][self.hit], np.add(self.pos, (dx3,dy3)), self.size/2-1.5)
        #sprite = self.env.sprites.defender if self.team == 1 else self.env.sprites.raider
        #rotated_image = pygame.transform.rotate(sprite, -(self.angle)/math.pi*180-attack_offset)
        #if self.frames[2] < self.attack_tick < self.frames[1]+anticipation:
        #    rotated_image.fill((100, 100, 100, 0), special_flags=pygame.BLEND_RGBA_ADD)
        #image_rect = rotated_image.get_rect()
        #image_rect.center = self.pos
        #self.env.surface.blit(rotated_image, image_rect)
        pygame.draw.circle(self.env.surface, [border_color, self.env.colors.white][self.hit], self.pos, self.size)
        pygame.draw.circle(self.env.surface, [self.color, self.env.colors.white][self.hit], self.pos, self.size-1.5)

        #if self.attacking and self.active_attack in (1,3):
        #    pygame.draw.circle(self.env.surface, self.env.colors.white, np.add(self.pos, (dx,dy)), self.attack_size)
        #    pygame.draw.circle(self.env.surface, self.env.colors.white, np.add(self.pos, (2*dx,2*dy)), self.attack_size)
        #    pygame.draw.circle(self.env.surface, self.env.colors.white, np.add(self.pos, (3*dx,3*dy)), self.attack_size)
                    
    def getInfo(self):
        return AttrDict({
            "id_": self.id_,
            "name": self.name,
            "type": "player",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "team": self.team,
            "health": self.health,
            "food": self.food,
            "wood": self.wood,
            "stone": self.stone,
            "active": self.active,
            "attacking": bool(self.attack_tick),
            "attack_state": [-1, [0, 1][self.frames[2] < self.attack_tick <= self.frames[1]]][bool(self.attack_tick)]
        })

    def __str__(self):
        return (f'''
health: {self.health}
food: {self.food}
wood: {self.wood}
stone: {self.stone}
''')
        
class StaticObject():
    def __init__(self, env, pos, size, health, team=-1):
        self.env = env
        self.pos = tuple(pos)
        self.size = size
        self.scale = 1
        self.health = health
        self.team = team

        self.hit = False
    
    def recieveHit(self, obj, damage, player):
        if isinstance(obj, Player):
            self.hit = True
            damage = min(self.health, damage//3)
            self.health -= damage
            self.recieveHitPlayer(obj, damage)
        elif isinstance(obj, Explosion):
            self.hit = True
            damage = min(self.health, damage)
            self.health -= damage
            self.recieveHitPlayer(self.env.dummy_player, 0)
        else:
            self.recieveHitObject(obj)
        
        if self.team != -1:
            if self.team == player.team:
                player.events.damage_dealt_team_structure += damage
            else:
                player.events.damage_dealt_enemy_structure += damage
        
        if self.health <= 0:
            self.env.removeObject(self)
    
    def recieveHitPlayer(self, player, damage): pass

    def recieveHitObject(self, obj): pass

    def resetState(self):
        self.hit = False

    def display(self):
        # call AFTER inherited object display()
        pass

class Effect():
    def __init__(self, env, pos, player):
        self.env = env
        self.pos = pos
        self.player = player

        self.size = 40
        self.effect_speed = 20
        self.effect_tick = 0
        self.lifetime = 80
    
    def step(self):
        if self.effect_tick == 0:
            for obj in self.env.dynamic_objects:
                if not isinstance(obj, Player):
                    continue
                else:
                    if math.dist(obj.pos, self.pos) <= self.size:
                        self.effectPlayer(obj)
            self.effect_tick = self.effect_speed
        else:
            self.effect_tick -= 1
        
        self.lifetime -= 1
        if self.lifetime == 0:
            self.env.removeEffect(self)
        
    def effectPlayer(self, player): pass
    def display(self): pass

class Heal(Effect):
    def __init__(self, env, pos, player):
        super().__init__(env, pos, player)
        self.healing = 2
    
    def effectPlayer(self, player):
        healing = min(player.health + self.healing, 25) - player.health
        player.changeHealth(healing)
        self.player.events.change_health_team_player += healing
        
    def display(self):
        #pygame.draw.circle(env.surface, env.colors.mutedred, self.pos, self.size)
        pygame.draw.circle(self.env.surface, self.env.colors.mutedlightred, self.pos, self.size-5)
    
    def getInfo(self):
        return AttrDict({
            "type": "heal",
            "position": self.pos,
            "size": self.size,
            "lifetime": self.lifetime,
        })

class Projectile():
    def __init__(self, env, pos, angle, team, player):
        self.env = env
        self.pos = pos
        self.angle = angle
        self.team = team
        self.player = player

        self.lifetime = 60
        self.subframes = 8
    
    def step(self):
        subframes = self.subframes
        if self.lifetime == 0:
            self.env.removeDynamicObject(self)
            return
        self.lifetime -= 1

        self.objects = self.env.grid.getNearbyObjects(self.pos) + self.env.dynamic_objects

        dx, dy = self.speed*math.cos(self.angle)/subframes, self.speed*math.sin(self.angle)/subframes
        for frame in range(subframes):
            self.pos = (self.pos[0]+dx, self.pos[1]+dy)
            if not self.env.grid.withinBounds(self.pos):
                self.env.removeDynamicObject(self)
                return
            for obj in self.objects:
                if ((isinstance(obj, StaticObject) and (type(obj) not in (Base, StoneWall, Spike))) or (type(obj) in {Player, Turret, Base, Spike, StoneWall} and obj.team != self.team)) \
                    and math.dist(obj.pos, self.pos) <= obj.size + self.size - 0.5:
                    if isinstance(obj, Spike):
                        continue
                    obj.recieveHit(self, self.damage, self.player)
                    self.env.removeDynamicObject(self)
                    self.collision(obj)
                    return
    
    def collision(self, obj):
        pass

    def resetState(self):
        pass

    def recieveHit(self, obj, damage):
        pass
    
    def display(self):
        pygame.draw.circle(self.env.surface, self.env.colors.white, self.pos, self.size)

class Arrow(Projectile):
    def __init__(self, env, pos, angle, team, player):
        super().__init__(env, pos, angle, team, player)
        self.damage = 3
        self.speed = 25
        self.size = 5

        self.lifetime = 30

    def collision(self, obj):
        if isinstance(obj, Player):
            self.env.addSound("arrowhitplayer", self.pos, 0.3)
        else:
            self.env.addSound("arrowhit", self.pos, 0.3)

    def display(self):
        rotated_image = pygame.transform.rotate(self.env.sprites.arrow, -(self.angle)/math.pi*180)
        image_rect = rotated_image.get_rect()
        image_rect.center = self.pos
        self.env.surface.blit(rotated_image, image_rect)
        #pygame.draw.circle(self.env.surface, self.env.colors.white, self.pos, self.size)
    
    def getInfo(self):
        return AttrDict({
            "type": "arrow",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "team": self.team,
            "lifetime": self.lifetime,
        })

class ChargedArrow(Projectile):
    def __init__(self, env, pos, angle, team, player):
        super().__init__(env, pos, angle, team, player)
        self.damage = 3
        self.speed = 45
        self.size = 5

        self.lifetime = 30
        self.subframes = 20

    def collision(self, obj):
        if isinstance(obj, Player):
            self.env.addSound("arrowhitplayer", self.pos, 0.3)
        else:
            self.env.addSound("arrowhit", self.pos, 0.3)

    def display(self):
        rotated_image = pygame.transform.rotate(self.env.sprites.arrow, -(self.angle)/math.pi*180)
        image_rect = rotated_image.get_rect()
        image_rect.center = self.pos
        self.env.surface.blit(rotated_image, image_rect)
        #pygame.draw.circle(self.env.surface, self.env.colors.white, self.pos, self.size)
    
    def getInfo(self):
        return AttrDict({
            "type": "chargedarrow",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "team": self.team,
            "lifetime": self.lifetime,
        })

class Bullet(Projectile):
    def __init__(self, env, pos, angle, team, player):
        super().__init__(env, pos, angle, team, player)
        self.damage = 5
        self.speed = 15
        self.size = 10

    def collision(self, obj):
        self.env.addSound("bullethit", self.pos, 0.5)

    def display(self):
        pygame.draw.circle(self.env.surface, darken(self.env.colors.lightgrey, 0.85), self.pos, self.size)
        pygame.draw.circle(self.env.surface, self.env.colors.lightgrey, self.pos, self.size-4)
    
    def getInfo(self):
        return AttrDict({
            "type": "bullet",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "team": self.team,
            "lifetime": self.lifetime,
        })

class Frag():
    def __init__(self, env, pos, angle, team, player):
        self.env = env
        self.pos = pos
        self.angle = angle
        self.team = team
        self.player = player

        self.lifetime = 40

        self.damage = 8
        self.speed = 15
        self.friction = 0.93
        self.size = 12
    
    def step(self, subframes=4):
        if self.lifetime == 0:
            self.env.removeDynamicObject(self)
            self.env.addDynamicObject(Explosion(self.env, self.pos, self.team, self.player))
            return 
        self.lifetime -= 1

        self.objects = self.env.grid.getNearbyObjects(self.pos) + self.env.dynamic_objects

        dx, dy = self.speed*math.cos(self.angle)/subframes, self.speed*math.sin(self.angle)/subframes
        for frame in range(subframes):
            if (not self.env.grid.withinBounds(np.add(self.pos, (dx,dy)))):
                self.speed = 0
                return
            self.pos = (self.pos[0]+dx, self.pos[1]+dy)
            for obj in self.objects:
                if ((isinstance(obj, StaticObject) and type(obj) not in {Base, StoneWall, Spike, Turret}) or (type(obj) not in {Player} and obj.team != self.team)) \
                    and math.dist(obj.pos, self.pos) <= obj.size + self.size - 0.5:
                    if isinstance(obj, Projectile):
                        continue
                    self.speed = 0
                    return
        
        self.speed *= self.friction

    def resetState(self):
        pass

    def display(self):
        pygame.draw.circle(self.env.surface, self.env.colors.white, self.pos, self.size)
    
    def getInfo(self):
        return AttrDict({
            "type": "frag",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "lifetime": self.lifetime,
        })

class Explosion():
    def __init__(self, env, pos, team, player):
        self.env = env
        self.pos = pos
        self.team = team
        self.player = player

        self.damage = 8
        self.size = 80

        self.lifetime = 1
    
    def step(self):
        if self.lifetime == 0:
            self.env.addSound("explosion", self.pos, 0.5)
            self.env.removeDynamicObject(self)
            return
        self.lifetime -= 1

        self.objects = self.env.grid.getNearbyObjects(self.pos) + self.env.dynamic_objects
        for obj in self.objects:
            if (math.dist(obj.pos, self.pos) <= obj.size + self.size - 0.5):
                if type(obj) in {Player, Turret, Spike, Base}:
                    obj.recieveHit(self, self.damage, self.player)
                elif type(obj) in self.env.resources:
                    obj.recieveHit(self, self.damage*2, self.player)
                elif type(obj) in {WoodWall, StoneWall}:
                    obj.recieveHit(self, self.damage*4, self.player)
    
    def resetState(self):
        pass

    def display(self):
        pygame.draw.circle(self.env.surface, self.env.colors.white+(180,), self.pos, self.size)
    
    def getInfo(self):
        return AttrDict({
            "type": "explosion",
            "position": self.pos,
            "size": self.size,
        })

class Turret():
    def __init__(self, env, pos, angle, team, player):
        self.env = env
        self.pos = pos
        self.team = team
        self.player = player
        self.angle = angle
        self.color = self.player.color

        self.health = 25
        self.damage = 5
        self.reload_speed = 50
        self.attack_tick = 30
        self.range = 400
        self.size = 20

        self.hit = False
    
    def step(self):
        self.objects = self.env.grid.getNearbyObjects(self.pos)

        closest_player = None
        closest_distance = math.inf
        for player in self.env.getPlayers():
            if player.health <= 0: continue
            if player.team != self.team and math.dist(player.pos, self.pos) < closest_distance:
                closest_player = player
                closest_distance = math.dist(player.pos, self.pos)

        if closest_distance > self.range:
            closest_player = None
        
        if closest_player is None: 
            closest_obj = None
            for obj in self.env.dynamic_objects:
                if not isinstance(obj, Turret): continue
                if obj.team != self.team and math.dist(obj.pos, self.pos) < closest_distance:
                    closest_obj = obj
                    closest_distance = math.dist(obj.pos, self.pos)
        else:
            closest_obj = closest_player

        if closest_obj is None: return

        x2, y2 = closest_obj.pos
        dx, dy = x2-self.pos[0], y2-self.pos[1]

        self.angle = math.atan2(dy, dx)
        if self.attack_tick == 0:
            self.attack()
        else:
            self.attack_tick -= 1

    def recieveHit(self, obj, damage, player):
        self.hit = True
        damage = min(self.health, damage)
        self.health -= damage

        if self.team == player.team:
            player.events.damage_dealt_team_structure += damage
        else:   
            player.events.damage_dealt_enemy_structure += damage
        
        if self.health <= 0:
            if isinstance(obj, Player):
                obj.changeWood(30)
                obj.changeStone(15)
            self.env.removeDynamicObject(self)
            self.env.addSound("stonedie", self.pos, 0.5)
        self.env.addSound("structurehit", self.pos, 0.6)
    
    def attack(self):
        dx, dy = 20*math.cos(self.angle), 20*math.sin(self.angle)
        obj = Bullet(self.env, np.add(self.pos, (dx, dy)), self.angle, self.team, self.player)
        self.env.addDynamicObject(obj)
        self.attack_tick = self.reload_speed
        self.env.addSound("turretfire", self.pos, 0.4)

    def resetState(self):
        self.hit = False

    def display(self):
        pygame.draw.circle(self.env.surface, [darken(self.env.colors.brown, scale=0.85), self.env.colors.white][self.hit], self.pos, self.size)
        pygame.draw.circle(self.env.surface, [self.env.colors.brown, self.env.colors.white][self.hit], self.pos, self.size-3)

        d1 = (0.5*self.size*math.cos(self.angle+math.pi/2), 0.5*self.size*math.sin(self.angle+math.pi/2))
        d2 = (0.5*self.size*math.cos(self.angle-math.pi/2), 0.5*self.size*math.sin(self.angle-math.pi/2))
        p1 = self.pos
        p2 = self.pos[0] + 1.35*self.size*math.cos(self.angle), self.pos[1] + 1.35*self.size*math.sin(self.angle)
        coords = (
            np.add(p1,d1),
            np.add(p1,d2),
            np.add(p2,d2),
            np.add(p2,d1)
        )
        pygame.draw.polygon(self.env.surface, [darken(self.env.colors.grey), self.env.colors.white][self.hit], coords)
        d1 = (0.4*self.size*math.cos(self.angle+math.pi/2), 0.4*self.size*math.sin(self.angle+math.pi/2))
        d2 = (0.4*self.size*math.cos(self.angle-math.pi/2), 0.4*self.size*math.sin(self.angle-math.pi/2))
        p1 = self.pos
        p2 = self.pos[0] + 1.2*self.size*math.cos(self.angle), self.pos[1] + 1.2*self.size*math.sin(self.angle)
        coords = (
            np.add(p1,d1),
            np.add(p1,d2),
            np.add(p2,d2),
            np.add(p2,d1)
        )
        pygame.draw.polygon(self.env.surface, [self.env.colors.grey, self.env.colors.white][self.hit], coords)
        pygame.draw.circle(self.env.surface, [darken(self.env.colors.grey, scale=1.2), self.env.colors.white][self.hit], self.pos, self.size/2+3)
        pygame.draw.circle(self.env.surface, [darken(self.env.colors.grey, scale=1.7), self.env.colors.white][self.hit], self.pos, self.size/2)
        pygame.draw.circle(self.env.surface, [self.player.color, self.env.colors.white][self.hit], self.pos, self.size/2-4)
    
    def getInfo(self):
        return AttrDict({
            "type": "turret",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "team": self.team,
            "health": self.health,
            "reload": self.attack_tick,
        })

class Bush(StaticObject):
    def __init__(self, env, pos):
        super().__init__(env, pos, 20, 15)

    def recieveHitPlayer(self, player, damage):
        player.changeFood(damage)
        self.size = 20 - 10 * (1-self.health/20)
        self.scale = self.size/20
        self.env.addSound("bushhit", self.pos, 1)

    def display(self):
        self.env.drawSprite("bush", self.pos, self.health, self.hit)
    
    def getInfo(self):
        return AttrDict({
            "type": "bush",
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })

class Tree(StaticObject):
    def __init__(self, env, pos):
        super().__init__(env, pos, 30, 20)

    def recieveHitPlayer(self, player, damage):
        player.changeWood(damage)
        self.size = 30 - 10 * (1-self.health/20)
        self.scale = self.size/30
        self.env.addSound("woodhit", self.pos, 0.8)
        self.env.addSound("bushhit", self.pos, 0.4)

    def display(self):
        self.env.drawSprite("tree", self.pos, self.health, self.hit)
    
    def getInfo(self):
        return AttrDict({
            "type": "tree",
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })

class Stone(StaticObject):
    def __init__(self, env, pos):
        super().__init__(env, pos, 40, 50)

    def recieveHitPlayer(self, player, damage):
        player.changeStone(damage)
        self.size = 40 - 20 * (1-self.health/50)
        self.env.addSound("stonehit", self.pos, 1)

    def display(self):
        self.env.drawSprite("stone", self.pos, self.health, self.hit)
    
    def getInfo(self):
        return AttrDict({
            "type": "stone",
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })

class WoodWall(StaticObject):
    def __init__(self, env, pos, team):
        super().__init__(env, pos, 20, 25)
        self.team = team

        self.darken_brown = darken(self.env.colors.brown, scale=0.87)
        self.brown = self.env.colors.brown
        self.white = self.env.colors.white

    def recieveHitPlayer(self, player, damage):
        self.health += damage//3 - damage
        self.env.addSound("woodhit", self.pos, 0.4)
        if self.health <= 0:
            player.changeWood(5)
            self.env.addSound("wooddie", self.pos, 0.3)
    
    def recieveHitObject(self, obj):
        if isinstance(obj, Bullet):
            self.hit = True
            self.health -= 2
        
        if self.health < 0:
            self.env.addSound("wooddie", self.pos, 0.3)

    def display(self):
        pygame.draw.polygon(self.env.surface, self.white if self.hit else self.darken_brown, polygon(self.pos, self.size, 8))
        pygame.draw.polygon(self.env.surface, self.white if self.hit else self.brown, polygon(self.pos, self.size-5, 8))
        super().display()
    
    def getInfo(self):
        return AttrDict({
            "type": "woodwall",
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })

class StoneWall(StaticObject):
    def __init__(self, env, pos, team):
        super().__init__(env, pos, 30, 75)
        self.team = team
        self.color = self.env.colors[f"team{self.team}"]
        self.darken_grey = darken(self.env.colors.grey, scale=0.95)
        self.grey = darken(self.env.colors.grey, scale=1.2)
        self.white = self.env.colors.white

    def recieveHitPlayer(self, player, damage):
        self.health += damage//3 - damage
        self.env.addSound("stoneplace", self.pos, 0.6)
        if self.health <= 0:
            player.changeStone(8)
            self.env.addSound("stonedie", self.pos, 0.5)
    
    def recieveHitObject(self, obj):
        if isinstance(obj, Bullet):
            self.hit = True
            self.health -= 2
        if self.health < 0:
            self.env.addSound("stonedie", self.pos, 0.5)

    def display(self):
        pygame.draw.polygon(self.env.surface, self.env.colors.white if self.hit else self.darken_grey, polygon(self.pos, self.size, 8))
        pygame.draw.polygon(self.env.surface, self.env.colors.white if self.hit else self.color, polygon(self.pos, self.size-5, 8))
        pygame.draw.polygon(self.env.surface, self.env.colors.white if self.hit else self.grey, polygon(self.pos, self.size-9, 8))
        super().display()
    
    def getInfo(self):
        return AttrDict({
            "type": "stonewall",
            "team": self.team,
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })
    
class Spike(StaticObject):
    def __init__(self, env, pos, team, player):
        super().__init__(env, pos, 17, 35)
        self.team = team
        self.player = player
        self.damage = 3
        self.color = self.env.colors[f"team{self.team}"]
        self.count = 0

    def recieveHitPlayer(self, player, damage):
        self.health += damage//3 - damage
        if self.health <= 0:
            player.changeWood(4)
            player.changeStone(4)
            self.env.removeDynamicObject(self)
            self.env.addSound("wooddie", self.pos, 0.3)
        self.env.addSound("structurehit", self.pos, 0.6)
    
    def recieveHitObject(self, obj):
        if isinstance(obj, Bullet):
            self.hit = True
            self.health -= 2
        if self.health <= 0:
            self.env.removeDynamicObject(self)
            self.env.addSound("wooddie", self.pos, 0.3)
    
    def step(self):
        self.count -= 1
        if self.count <= 0:
            for player in self.env.getPlayers():
                if player.team != self.team and math.dist(player.pos, self.pos) < player.size + self.size + 2:
                    player.recieveHit(self, self.damage, self.player)
            self.count = 5

    def display(self):
        self.env.drawSprite(f"spike{self.team}", self.pos, -1, self.hit)
    
    def getInfo(self):
        return AttrDict({
            "type": "spike",
            "team": self.team,
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })

class Base(StaticObject):
    def __init__(self, env, pos, team):
        super().__init__(env, pos, 40, 100)
        self.team = team
        self.regen = 2
    
    def recieveHit(self, obj, damage, player):
        if self.health <= 0:
            return
        
        if isinstance(obj, Player) and obj.team == self.team:
            return

        self.hit = True
        damage = min(self.health, damage)
        self.health -= damage

        if player.team == self.team:
            player.events.self_damage_dealt_base -= damage
        else:
            player.events.self_damage_dealt_base += damage

        for p in self.env.getPlayers():
            if p.team == self.team:
                p.events.damage_dealt_base -= damage
            else:
                p.events.damage_dealt_base += damage
        
        self.env.addSound("structurehit", self.pos, 0.6)
        self.env.addSound("basehit", self.pos, 0.4)
        self.env.addSound("basedie", self.pos, 0.3)
        
        if self.health <= 0:
            self.env.removeDynamicObject(self)
            self.env.addSound("basedie", self.pos, 0.8)
    
    def step(self):
        if self.health > 0:
            self.health = min(100, self.health + 0.01)

    def display(self):
        scale = max(self.health, 0) / 100
        if scale:
            pygame.draw.circle(self.env.surface, (160, 185, 220), self.pos, 48)
            pygame.draw.polygon(self.env.surface, self.env.colors.white, polygon(self.pos, self.size*scale+3, 8))
            pygame.draw.polygon(self.env.surface, [self.env.colors.lightergrey, self.env.colors.white][self.hit], polygon(self.pos, self.size*scale, 8))
        else:
            pygame.draw.circle(self.env.surface, (170, 170, 170), self.pos, 48)
        super().display()
    
    def getInfo(self):
        return AttrDict({
            "type": "base",
            "position": self.pos,
            "size": self.size,
            "health": self.health,
        })
    


class GridCell():
    def __init__(self, idx, gridsize):
        self.idx = idx
        self.x, self.y = idx[0]*gridsize, idx[1]*gridsize
        self.gridsize = gridsize
        self.objects = []

    def withinBounds(self, pos):
        x2, y2 = pos
        return self.x <= x2 < self.x+self.gridsize and self.y <= y2 < self.y+self.gridsize

    def addObject(self, obj):
        self.objects.append(obj)

    def removeObject(self, obj):
        # start search from back
        for i in range(len(self.objects)-1, -1, -1):
            if self.objects[i] == obj:
                del self.objects[i]
                return
        raise ValueError(f"{obj} not in gridcell {self.idx}")
        

class Grid():
    def __init__(self, env, gridsize):
        self.env = env
        self.gridsize = gridsize

        self.grid = {
            (x,y) : GridCell((x,y), gridsize) for
             x in range(math.ceil(self.env.map_size[0]/gridsize)) for
             y in range(math.ceil(self.env.map_size[1]/gridsize))
        }

        self.DUMMYCELL = GridCell((-1, -1), gridsize)

    def withinBounds(self, pos):
        x, y = pos
        return (0 <= x <= self.env.map_size[0]-1) and (0 <= y <= self.env.map_size[1]-1)
        
    def getNeighboringCells(self, idx, size=1):
        x,y = idx
        neighboring_cells = []
        for dx in range(-size, size+1):
            for dy in range(-size, size+1):
                cell_idx = (x+dx, y+dy)
                if cell_idx in self.grid:
                    cell = self.grid[cell_idx]
                else:
                    cell = self.DUMMYCELL
                neighboring_cells.append(cell)

        return tuple(neighboring_cells)

    def getNearbyObjects(self, pos, size=1):
        idx = pos[0]//self.gridsize, pos[1]//self.gridsize
        return sum((cell.objects for cell in self.getNeighboringCells(idx, size)), start=[])

    def addObject(self, obj):
        pos = obj.pos
        x,y = pos[0]//self.gridsize, pos[1]//self.gridsize
        self.grid[(x,y)].addObject(obj)

    def removeObject(self, obj):
        pos = obj.pos
        x,y = pos[0]//self.gridsize, pos[1]//self.gridsize
        self.grid[(x,y)].removeObject(obj)


class Camera():
    def __init__(self, env):
        self.env = env
        self.pos = env.center
        self.scale = env.map_size[0]/2
        
        x,y = self.pos
        s = self.scale
        self.frame_rect = pygame.Rect(x-s, y-s, 2*s, 2*s)

    def getFrame(self, surface):
        center = self.frame_rect.center
        self.frame_rect.width = 2*self.scale
        self.frame_rect.height = 2*self.scale
        self.frame_rect.center = center

        frame = pygame.Surface(self.frame_rect.size)
        frame.fill((self.env.colors.grey))
        
        world_rect = surface.get_rect()
        overlap = self.frame_rect.clip(world_rect)

        if overlap.width > 0 and overlap.height > 0:
            x = overlap.x - self.frame_rect.x
            y = overlap.y - self.frame_rect.y
            frame.blit(surface, (x,y), overlap)
            
        return frame
        

class RaiderEnvironment():
    def __init__(self):
        self.colors = AttrDict({
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "orange": (170, 120, 55),
            "brown": (120, 80, 60),
            "lightbrown": (210, 170, 130),
            "green": (100, 170, 70),
            "darkgreen": (92, 135, 52),
            "grey": (70, 70, 70),
            "lightgrey": (130, 130, 130),
            "lightergrey": (180, 180, 180),
            "mutedred": (180, 120, 90),
            "mutedlightred": (190, 145, 100),
            "team2": (240, 140, 80),
            "team1": (140, 190, 240),
        })

        self.resources = {Bush, Tree, Stone}
        self.walls = {WoodWall, StoneWall, Spike}
        
        self.map_size = [2000, 2000]
        self.center = [self.map_size[0]//2, self.map_size[1]//2]
        self.screen_size = 800, 800
        self.screen_center = [self.screen_size[0]//2, self.screen_size[1]//2]
        self.sounds = []

        self.max_storm_size = math.sqrt(2) * (self.map_size[0] // 2)
        self.min_storm_size = math.sqrt(2) * (self.map_size[0] // 2) / 2 

        self.camera = Camera(self)
        self.dummy_player = DUMMYPLAYER()

        self.surface = pygame.Surface(self.map_size, pygame.SRCALPHA)
        self.background_surface = pygame.Surface(self.map_size, pygame.SRCALPHA)
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.t = 0

        self.metadata = AttrDict({
            "colors": self.colors,
            "map_size": self.map_size,
            "center": self.center,
            "screen_size": self.screen_size,
            "screen_center": self.screen_center,
            "time": self.t,
            "storm_size": self.max_storm_size,
        })

        self.initializeSprites()

        self.players = {}
        self.reset()

    def getPlayers(self):
        return tuple(self.players.values())

    def addPlayer(self, id_, team):
        team = 1 if team=="defender" else 2
        player = Player(self, (-1,-1), team, id_)
        if team == 1:
            self.setSpawnLoc(self.map_size[0]*0.12, player)
        else:
            self.setSpawnLoc(self.map_size[0]*0.4, player)
        self.players[id_] = player
        self.dynamic_objects.append(player)

    def removePlayer(self, id_):
        player = self.players[id_]
        if player in self.dynamic_objects:
            self.dynamic_objects.remove(player)
        del self.players[id_]

    def initializeSprites(self):
        self.sprites = AttrDict({
            "raider": pygame.image.load("assets/raider.png"),
            "defender": pygame.image.load("assets/defender.png"),
            "sword": pygame.image.load("assets/sword.png"),
            "bow": pygame.image.load("assets/bow.png"),
            "axe": pygame.image.load("assets/axe.png"),
            "arrow": pygame.image.load("assets/arrow.png"),
        })

        image_size = (100, 100)
        center = (50, 50)

        # draw bush
        bush_instance = Bush(self, (0,0))
        self.bush_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        points = polygon(center, bush_instance.size-5, 6)
        for i in range(6):
            pygame.draw.circle(self.bush_surface, darken(self.colors.darkgreen, 0.89), points[i], 18)
        points = polygon(center, bush_instance.size-10, 6)
        for i in range(6):
            pygame.draw.circle(self.bush_surface, darken(self.colors.darkgreen, 1.02), points[i], 16)
        points = polygon(center, bush_instance.size*0.4+1, 3)
        for i in range(3):
            pygame.draw.circle(self.bush_surface, darken(self.colors.mutedred, 0.9), points[i], 9*(bush_instance.size/20)**0.8)

        self.generateHealthLookups('bush', self.bush_surface, bush_instance)

        # draw tree
        tree_instance = Tree(self, (0,0))
        self.tree_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        pygame.draw.polygon(self.tree_surface, self.colors.darkgreen, (p1:=polygon(center, tree_instance.size*.75, 3)), width=13)
        pygame.draw.polygon(self.tree_surface, self.colors.darkgreen, (p2:=polygon(center, tree_instance.size*.75, 3, flip=-1)), width=13)
        for p in p1+p2:
            pygame.draw.circle(self.tree_surface, self.colors.darkgreen, p, 7)
        pygame.draw.polygon(self.tree_surface, darken(self.colors.darkgreen, scale=1.1), polygon(center, tree_instance.size*.75-2, 3))
        pygame.draw.polygon(self.tree_surface, darken(self.colors.darkgreen, scale=1.1), polygon(center, tree_instance.size*.75-2, 3, flip=-1))

        self.generateHealthLookups('tree', self.tree_surface, tree_instance)

        # draw stone
        stone_instance = Stone(self, (0,0))
        self.stone_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        pygame.draw.polygon(self.stone_surface, darken(self.colors.lightgrey, scale=0.9), polygon(center, stone_instance.size, 8))
        pygame.draw.polygon(self.stone_surface, self.colors.lightgrey, polygon(center, stone_instance.size-8, 7))
        pygame.draw.polygon(self.stone_surface, darken(self.colors.lightgrey, scale=1.15), polygon(center, stone_instance.size/2, 6))

        self.generateHealthLookups('stone', self.stone_surface, stone_instance)

        spike_instance = Spike(self, (0,0), 1, self.dummy_player)
        self.spike_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        for team,color in zip(["spike1", "spike2"], [self.colors.team1, self.colors.team2]):
            size = spike_instance.size
            pygame.draw.polygon(self.spike_surface, darken(self.colors.lightgrey, scale=0.9), polygon(center, size-2, 3, 1))
            pygame.draw.polygon(self.spike_surface, darken(self.colors.lightgrey, scale=0.9), polygon(center, size-2, 3, -1))
            pygame.draw.polygon(self.spike_surface, self.colors.lightgrey, polygon(center, size-5, 3, 1))
            pygame.draw.polygon(self.spike_surface, self.colors.lightgrey, polygon(center, size-5, 3, -1))
            pygame.draw.circle(self.spike_surface, darken(self.colors.brown, scale=0.94), center, size+1.5)
            pygame.draw.circle(self.spike_surface, darken(self.colors.brown, scale=1.1), center, size-1.5)
            pygame.draw.circle(self.spike_surface, color, center, size-9)

            opaque = self.spike_surface.convert()
            opaque.set_colorkey((0, 0, 0))
            self.sprites[(team, False)] = opaque
            opaque = self.spike_surface.convert()
            opaque.set_colorkey((0, 0, 0))
            self.fill_visible_pixels(opaque)
            self.sprites[(team, True)] = opaque
        
        for name, surf in self.sprites.items():
            if isinstance(name, tuple):
                pygame.image.save(surf, f"assets_cache/{'_'.join(str(s) for s in name)}.png")

    
    def generateHealthLookups(self, type, surface, instance):
        image_size = (100, 100)
        center = (50, 50)
        s = instance.health

        self.sprites[type] = {}
        for i in range(instance.health):
            scale = (s - s*0.4 * (1-i/s)) / s
            scaled_image = pygame.transform.scale(surface, (int(image_size[0]*scale), int(image_size[1]*scale)))
            scaled_image_rect = scaled_image.get_rect(center=center)
            canvas = pygame.Surface(image_size, pygame.SRCALPHA)
            canvas.blit(scaled_image, scaled_image_rect)
            opaque = canvas.convert()

            opaque = canvas.convert()
            opaque.set_colorkey((0, 0, 0))
            self.sprites[(type, i+1, False)] = opaque
            opaque = canvas.convert()
            opaque.set_colorkey((0, 0, 0))
            self.fill_visible_pixels(opaque)
            self.sprites[(type, i+1, True)] = opaque

    def fill_visible_pixels(self, surface, fill_color=(255, 255, 255)):
        colorkey = surface.get_colorkey()
        if colorkey is None:
            raise ValueError("Surface must have a colorkey set")

        surface.lock()
        width, height = surface.get_size()

        for x in range(width):
            for y in range(height):
                if surface.get_at((x, y))[:3] != colorkey[:3]:
                    surface.set_at((x, y), fill_color)
        surface.unlock()
    
    def drawSprite(self, sprite, pos, health, hit):
        if health == -1:
            sprite_surface = self.sprites[(sprite, hit)]
        else:
            sprite_surface = self.sprites[(sprite, health, hit)]
        rect = sprite_surface.get_rect(center=pos)
        self.surface.blit(sprite_surface, rect)

    def reset(self):
        self.grid = Grid(self, 200)
        self.base = Base(self, (self.map_size[0]/2, self.map_size[1]/2), 1)
        self.storm_size = self.max_storm_size
        self.t = 0

        self.metadata.time = self.t
        self.metadata.storm_size = self.storm_size

        self.objects = []
        self.addDeposits()
        self.effects = []
        self.sounds = []
        
        for id_, player in self.players.items():
            team = player.team
            player = Player(self, (-1,-1), team, id_)
            player.food, player.wood, player.stone = (50, 120, 120) if team==1 else (80, 50, 50)
            self.setSpawnLoc(self.map_size[0] * [0.12, 0.4][team-1], player)
            self.players[id_] = player
        
        self.dynamic_objects = [player for player in self.players.values()]
        self.addDynamicObject(self.base)

        observations = {}
        info = {"team_observations": {"defender": {}, "raider": {}} }
        for id_, player in self.players.items():
            team = "defender" if player.team==1 else "raider"
            obs = self.getInputs(id_)
            info["team_observations"][team][id_] = obs
            observations[id_] = obs
        info = AttrDict(info)
        return observations, info
    
    def getTeamCounts(self):
        teams = [0,0]
        for id_, player in self.players.items():
            team = player.team
            teams[team-1] += 1
        return teams
    
    def addSound(self, sound, pos, scale):
        self.sounds.append((SoundUtils.encodeSoundID(sound), *pos, scale))

    def addDeposits(self, bushes=(70,6), trees=(100,8), stones=(40,4)):        
        for _ in range(stones[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Stone(self, (x,y)))

        for _ in range(bushes[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Bush(self, (x,y)))
            
        for _ in range(trees[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Tree(self, (x,y)))

        for _ in range(stones[1]):
            x, y = self.getSpawnLoc2(200)
            self.addObject(Stone(self, (x,y)))

        for _ in range(bushes[1]):
            x, y = self.getSpawnLoc2(200)
            self.addObject(Bush(self, (x,y)))
            
        for _ in range(trees[1]):
            x, y = self.getSpawnLoc2(200)
            self.addObject(Tree(self, (x,y)))

    def setSpawnLoc(self, r, obj=None):
        check = False
        count = 15
        while not check and count:
            theta = random.random()*2*math.pi
            if obj is None:
                return r*math.cos(theta) + self.map_size[0]/2, r*math.sin(theta) + self.map_size[1]/2
            obj.pos = (r*math.cos(theta) + self.map_size[0]/2, r*math.sin(theta) + self.map_size[1]/2)
            check = True
            for obj2 in self.objects:
                if math.dist(obj.pos, obj2.pos) <= obj.size + obj2.size - 0.5:
                    check = False
            count -= 1
        
    def getSpawnLoc2(self, r):
        theta = random.random()*2*math.pi
        r = r * math.sqrt(random.random())
        return r * math.cos(theta) + self.center[0], r * math.sin(theta) + self.center[1]

    def getSpawnLoc(self):
        x, y = self.map_size[0]/2, self.map_size[1]/2
        while (x > 0.25*self.map_size[0] and x < 0.75*self.map_size[0] and \
               y > 0.25*self.map_size[1] and y < 0.75*self.map_size[1]):
            x, y = random.randint(50, self.map_size[0]-50), random.randint(50, self.map_size[1]-50)
        return x, y

    def addObject(self, obj):
        self.objects.append(obj)
        self.grid.addObject(obj)

    def removeObject(self, obj):
        if obj not in self.objects:
            return
        self.objects.remove(obj)
        self.grid.removeObject(obj)
    
    def addDynamicObject(self, obj):
        self.dynamic_objects.append(obj)
    
    def removeDynamicObject(self, obj):
        if obj not in self.dynamic_objects:
            return
        self.dynamic_objects.remove(obj)
    
    def addEffect(self, obj):
        self.effects.append(obj)
    
    def removeEffect(self, obj):
        self.effects.remove(obj)

    def step(self, actions, display=False):
        self.t += 1
        self.storm_size = max(0, min(1, (self.t - 180*20) / (300*20 - 180*20))) * (self.min_storm_size - self.max_storm_size) + self.max_storm_size
        self.metadata.time = self.t
        self.metadata.storm_size = self.storm_size
        self.sounds = []

        for obj in self.objects + self.dynamic_objects:
            obj.resetState()

        for n, action in actions.items():
            if self.players[n].health <= 0: continue
            # check to see if actions are valid
            ax, ay, active, action_, angle = action
            assert (0 <= ax <= 2) and (int(ax) == ax), f"Invalid Action[0]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= ay <= 2) and (int(ay) == ay), f"Invalid Action[1]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= active <= 9) and (int(active) == active), f"Invalid Action[2]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= action_ <= 1) and (int(action_) == action_), f"Invalid Action[3]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= angle <= 4) and (int(angle) == angle), f"Invalid Action[4]: {ax}, {ay}, {active}, {action_}, {angle}"
            dx = action[0] - 1
            dy = action[1] - 1
            active = action[2]
            attack = action[3]
            angle = 0.0981747704247 * (action[4]-2) * (abs(action[4]-2))
            self.players[n].step(dx, dy, active, attack, angle)

        for obj in self.dynamic_objects:
            if isinstance(obj, Player):
                continue
            obj.step()
        
        for obj in self.effects:
            obj.step()

        if self.t % 20 == 0:
            for player in self.getPlayers():
                if math.dist(player.pos, self.center) > self.storm_size:
                    player.recieveHit(self.dummy_player, 5, self.dummy_player)


        pygame.event.pump()
        self.surface.fill(self.colors.green)

        for obj in self.effects:
            obj.display()
        
        self.base.display()

        for obj in self.objects:
            if isinstance(obj, Tree):
                continue
            obj.display()
        for obj in self.dynamic_objects:
            if isinstance(obj, Player) or isinstance(obj, Base):
                continue
            obj.display() 
        for obj in self.getPlayers():
            if obj.health <= 0: 
                continue
            obj.display()
        for obj in self.objects:
            if not isinstance(obj, Tree):
                continue
            obj.display()

        mask = pygame.Surface(self.map_size, pygame.SRCALPHA)
        mask.fill((255, 0, 0, 120))  # semi-transparent red
        pygame.draw.circle(mask, (0, 0, 0, 0), self.center, int(self.storm_size))  # transparent center
        self.surface.blit(mask, (0, 0))

        for player in self.getPlayers():
            if player.health <= 0:
                continue
            bar_width = 40
            health_ratio = player.health / 20
            pygame.draw.rect(self.surface, (40,40,40), (player.pos[0]-bar_width/2, player.pos[1]+20, bar_width, 6))
            pygame.draw.rect(self.surface, (140,210,100), (player.pos[0]-(bar_width-3)/2, player.pos[1]+21, (bar_width-3)*min(1, health_ratio), 3))
            if health_ratio > 1:
                absorption_ratio = health_ratio - 1
                pygame.draw.rect(self.surface, (255,220,90), (player.pos[0]+(bar_width-3)*(0.5-absorption_ratio), player.pos[1]+21, (bar_width-3)*absorption_ratio, 3))

        done = self.gameIsDone()
        
        #((self.base.health <= 0) or (self.t > 10*60*20) or \
        #        (0 == sum([max(0, p.health) for p in self.players[:self.teams[0]]])) or (0 == sum([max(0, p.health) for p in self.players[self.teams[0]:]])))

        observations = {}
        info = {"team_observations": {"defender": {}, "raider": {}} }
        for id_, player in self.players.items():
            team = "defender" if player.team==1 else "raider"
            obs = self.getInputs(id_)
            info["team_observations"][team][id_] = obs
            observations[id_] = obs
        info = AttrDict(info)

        if not done:
            reward = 0
        else:
            if self.base.health <= 0:
                reward = {n:[0,20][done] * 2*((p.team==self.base.team)-0.5) for n,p in self.players.items()}
            else:
                reward = 1
        term = False

        if display:
            frame = self.camera.getFrame(self.surface)
            frame = pygame.transform.flip(frame, False, True)
            pygame.transform.scale(frame, self.screen_size, self.screen)
            pygame.display.flip()
            self.clock.tick(20)

        return observations, reward, done, term, info

    def gameIsDone(self):
        if self.base.health <= 0:
            return True
        teams = [0,0]
        for player in self.getPlayers():
            if player.health <= 0: continue
            teams[player.team-1] += 1
        if teams[0] == 0:
            return True
        if teams[1] == 0:
            return True
        return False

        #((self.base.health <= 0) or (self.t > 10*60*20) or \
        #        (0 == sum([max(0, p.health) for p in self.players[:self.teams[0]]])) or (0 == sum([max(0, p.health) for p in self.players[self.teams[0]:]])))

    
    def getInputs(self, id_):
        scale = 0.25
        h, w = int(self.map_size[0] * scale), int(self.map_size[1] * scale)
        small_surface = pygame.transform.scale(self.surface, (w, h))
        np_surface = pygame.surfarray.pixels3d(small_surface)

        player = self.players[id_]

        x, y = int(player.pos[0]*scale), int(player.pos[1]*scale)
        w, h = int(600*scale), int(600*scale)
        x, y, w, h = [int(_) for _ in [x,y,w,h]]
        obs = np_surface[x:x+w , y:y+h]

        vec_obs = np.array([
            (player.team),
            (max(0,player.health)**0.5)/5,
            (max(0,player.food)**0.5)/20,
            (max(0,player.wood)**0.5)/25,
            (max(0,player.stone)**0.5)/20,
        ], dtype=np.float32)

        info = AttrDict({
            "metadata": self.metadata,
            "image_obs": obs,
            "vector_obs": vec_obs,
        })

        for type in ("base", "spike", "stonewall", "woodwall", "turret", "stone", "tree", "bush", "explosion", "frag", "bullet", "chargedarrow", "arrow", "heal", "player"):
            info[type] = []

        info["self"] = player.getInfo()
        objects = self.grid.getNearbyObjects(player.pos, size=2) + self.dynamic_objects + self.effects
        for obj in objects:
            dx, dy = obj.pos[0]-player.pos[0], obj.pos[1]-player.pos[1]
            if abs(dx) > 320 or abs(dy) > 320:
                continue

            obj_info = obj.getInfo()
            if obj_info["type"] == "player" and obj_info["team"] != player.team: # hide resource information of opponents
                del obj_info["food"]
                del obj_info["wood"]
                del obj_info["stone"]
            obj_info["relative_position"] = (dx, dy)
            info[obj_info["type"]].append(obj_info)

        return info

