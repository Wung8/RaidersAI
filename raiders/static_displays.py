import pygame
import numpy as np
import math
import os

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

    def process_object(self, obj):
        '''
        type, x, y, health, angle, hit, r, g, b
        '''
        info = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        match type(obj):
            case raiders.Player:
                info = (-1, obj.pos[0], obj.pos[1], obj.health, obj.angle, obj.hit, *obj.color, obj.active, obj.attack_tick, obj.frames, obj.id_, obj.kills)
            case raiders.Heal:
                info = (0, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Arrow:
                info = (1, obj.pos[0], obj.pos[1], 0, obj.angle, 0, 0, 0, 0)
            case raiders.ChargedArrow:
                info = (2, obj.pos[0], obj.pos[1], 0, obj.angle, 0, 0, 0, 0)
            case raiders.Bullet:
                info = (3, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Frag:
                info = (4, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Explosion:
                info = (5, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Turret:
                info = (6, obj.pos[0], obj.pos[1], 0, obj.angle, obj.hit, *obj.color)
            case raiders.Bush:
                info = (7, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            case raiders.Tree:
                info = (8, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            case raiders.Stone:
                info = (9, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            case raiders.WoodWall:
                info = (10, obj.pos[0], obj.pos[1], 0, 0, obj.hit, 0, 0, 0)
            case raiders.StoneWall:
                info = (11, obj.pos[0], obj.pos[1], 0, 0, obj.hit, *obj.color)
            case raiders.Spike:
                info = (12, obj.pos[0], obj.pos[1], -1, 0, obj.hit, *obj.color)
            case raiders.Base:
                info = (13, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            
        
        return info

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