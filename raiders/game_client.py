# game_client.py
import socket
import pickle
import struct
import pygame
import sys
import time
import math
import ctypes
import yaml

import os
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'

import raiders
MSG_LEN_STRUCT = struct.Struct("!I")


def send_msg(sock, obj):
    data = pickle.dumps(obj)
    sock.sendall(MSG_LEN_STRUCT.pack(len(data)) + data)


def recv_msg(sock):
    try:
        header = sock.recv(MSG_LEN_STRUCT.size)
        if not header:
            return None
        (length,) = MSG_LEN_STRUCT.unpack(header)
        data = b""
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return pickle.loads(data)
    except Exception:
        return None
    

class InputBox:
    def __init__(self, x, y, w, h, text='', placeholder=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color('gray60')
        self.color_active = pygame.Color('dodgerblue2')
        self.color = self.color_inactive
        self.text = text
        self.font = pygame.font.Font(None, 30)
        self.txt_surface = self.font.render(text or placeholder, True, self.color)
        self.active = False
        self.placeholder = placeholder

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Toggle active state
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
                self.color = self.color_inactive
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            # Re-render text
            display_text = self.text if self.text else self.placeholder
            self.txt_surface = self.font.render(display_text, True, (255,255,255))

    def draw(self, screen):
        # Draw text
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        # Draw rect
        pygame.draw.rect(screen, self.color, self.rect, 2)


class GameClient:
    def __init__(self, server_ip, port, player_id):
        pygame.init()

        self.server_ip = server_ip
        self.port = port
        self.player_id = player_id
        self.hover_player = player_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((server_ip, port))
        self.sock.settimeout(None)  # blocking for main loop
        # register with server
        send_msg(self.sock, {'type': 'register', 'player_id': self.player_id})

        # Load controls from YAML
        self.config_path = "preferences.yaml"
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
            self.controls = self.config.get("controls", {})
            self.name = self.config.get("name", f"Player{self.player_id}")
        except Exception as e:
            print(f"[client] Failed to load {self.config_path}: {e}")
            exit()
            self.controls = {}
            self.name = f"Player{self.player_id}"

        # setup pygame window (will resize to incoming frames)
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.NOFRAME)

        # Close button rectangle
        self.close_rect = pygame.Rect(self.screen_width - 45, 5, 40, 40)

        # Input boxes
        self.ip_box = InputBox(self.screen_width - 260, 10, 200, 35, text=self.server_ip, placeholder="IP Address")
        self.port_box = InputBox(self.screen_width - 260, 55, 200, 35, text=str(self.port), placeholder="Port")
        self.name_box = InputBox(self.screen_width - 260, 100, 200, 35, text=self.name, placeholder="Name")


        self.surface = pygame.Surface((800, 800))
        self.scale = self.screen.get_height() / self.surface.get_height()
        pygame.display.set_caption(f"Player {self.player_id} - Client")
        self.clock = pygame.time.Clock()
        self.running = True

        self.food_img = pygame.image.load("assets/food.png")
        self.wood_img = pygame.image.load("assets/wood.png")
        self.stone_img = pygame.image.load("assets/stone.png")
        self.font = pygame.font.Font(None, 30) 
        self.font2 = pygame.font.Font(None, 25) 
        self.name_font = pygame.font.SysFont("segoeuiemoji", 20) 
        self.last_action = (1,1,0,0,0)
        self.name = ""

    def draw_ui(self):
        # Draw close button
        pygame.draw.rect(self.screen, (200, 60, 60), self.close_rect)
        x_font = pygame.font.Font(None, 36)
        x_text = x_font.render("X", True, (255, 255, 255))
        self.screen.blit(x_text, (self.close_rect.x + 10, self.close_rect.y + 5))

        # Draw input boxes
        self.ip_box.draw(self.screen)
        self.port_box.draw(self.screen)
        self.name_box.draw(self.screen)

    def handle_ui_events(self, event):
        # Check for close button click
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.close_rect.collidepoint(event.pos):
                self.running = False
                pygame.quit()
                sys.exit()

        # Handle text input
        self.ip_box.handle_event(event)
        self.port_box.handle_event(event)
        self.name_box.handle_event(event)

    def build_action_from_input(self, player_angle, relative_pos):
        """
        Build action tuple (ax, ay, active, action, angle) matching PlayerAgent.step().
        """

        if any([box.active for box in (self.ip_box, self.port_box, self.name_box)]):
            return (1, 1, 0, 0, 2)

        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()

        # Utility: map a string like "w" → pygame.K_w
        def keycode(k):
            if len(k) == 1 and k.isalnum():
                return getattr(pygame, f"K_{k}")
            special = {
                "mouse_left": ("mouse", 0),
                "mouse_right": ("mouse", 2),
                "mouse_middle": ("mouse", 1),
            }
            return special.get(k, None)

        # --- Movement (starts at 1,1 and adjusts with YAML keys) ---
        ax, ay = 1, 1
        if keys[getattr(pygame, f"K_{self.controls.get('left', 'a')}")]: ax -= 1
        if keys[getattr(pygame, f"K_{self.controls.get('right', 'd')}")]: ax += 1
        if keys[getattr(pygame, f"K_{self.controls.get('down', 's')}")]: ay -= 1
        if keys[getattr(pygame, f"K_{self.controls.get('up', 'w')}")]: ay += 1

        # --- Active item selection ---
        active = 0
        for i, name in enumerate(
            ["sword", "bow", "axe", "frag", "wood_wall", "stone_wall", "spike", "turret", "heal"], start=1
        ):
            key_str = self.controls.get(name)
            if key_str and len(key_str) == 1 and keys[getattr(pygame, f"K_{key_str}")]:
                active = i

        # --- Place/Attack ---
        place_key = self.controls.get("place_attack", "mouse_left")
        if place_key.startswith("mouse"):
            idx = {"mouse_left": 0, "mouse_middle": 1, "mouse_right": 2}[place_key]
            action = mouse[idx]
        else:
            action = keys[getattr(pygame, f"K_{place_key}")]

        # --- Angle computation (unchanged) ---
        mx, my = pygame.mouse.get_pos()
        window_w, window_h = self.screen.get_size()
        margin = (window_w - window_h) / 2
        cx, cy = margin + relative_pos[0] * (window_h / 600), relative_pos[1] * (window_h / 600)
        dx, dy = mx - cx, my - cy
        target_angle = -math.atan2(dy, dx)

        self.last_action = (ax, ay, active, action, target_angle)
        return self.last_action


    def run(self):
        try:
            while self.running:
                # Draw background
                self.screen.fill((40, 40, 40))
                self.events = pygame.event.get()
                # Event handling
                for event in self.events:
                    if event.type == pygame.QUIT:
                        self.running = False
                    self.handle_ui_events(event)

                # Draw UI elements
                self.draw_ui()


                msg = recv_msg(self.sock)
                if msg is None:
                    print("[client] connection closed by server")
                    break

                
                # handle server messages
                mtype = msg.get('type')
                if mtype == 'frame':
                    #img_bytes = msg['img_bytes']
                    size = msg['size']
                    info = msg.get('info')

                    if info["healths"][self.player_id] > 0:
                        self.hover_player = self.player_id
                    else:
                        events = self.events
                        for event in events:
                            if event.type == pygame.KEYDOWN:
                                if event.key == pygame.K_a:
                                    self.hover_player -= 1
                                if event.key == pygame.K_d:
                                    self.hover_player += 1
                        self.hover_player = self.hover_player % len(info["healths"])
                        

                    player_pos = info["positions"][abs(self.hover_player)]
                    player_angle = info["angles"][abs(self.hover_player)]
                    px, py = info["positions"][abs(self.hover_player)]
                    objects = info['objects']
                    sounds = info['sounds']
                    
                    w, h = size
                    crop_w, crop_h = 600, 600

                    x0 = int(px - crop_w / 2)
                    y0 = int(py - crop_h / 2)

                    # clamp so we don't go out of bounds
                    x0 = max(0, min(x0, w - crop_w))
                    y0 = max(0, min(y0, h - crop_h))

                    relative_pos = (px - x0, 600 + y0 - py)
                    relative_pos2 = relative_pos
                    # reconstruct surface from raw RGB bytes
                    try:
                        frame_surf = pygame.Surface((600, 600), pygame.SRCALPHA)
                        frame_surf.fill((100, 170, 70))
                        players = []
                        for obj in objects:
                            dx, dy = obj[1]-player_pos[0], obj[2]-player_pos[1]
                            if math.dist((obj[1],obj[2]), (x0+300,y0+300)) > 550: 
                                continue
                            screen_pos = dx+relative_pos[0], dy+600-relative_pos[1]
                            raiders.StaticDisplays.display(frame_surf, screen_pos, obj)

                            if obj[0] == -1:
                                players.append(obj)
                        
                        screen_pos2 = []
                        for obj in players:
                            dx, dy = obj[1]-player_pos[0], obj[2]-player_pos[1]
                            screen_pos = dx+relative_pos[0], dy+600-relative_pos[1]
                            screen_pos2.append(screen_pos)
                            if obj[3] <= 0:
                                continue
                            bar_width = 40
                            health_ratio = obj[3] / 20
                            pygame.draw.rect(frame_surf, (40,40,40), (screen_pos[0]-bar_width/2, screen_pos[1]+20, bar_width, 6))
                            pygame.draw.rect(frame_surf, (140,210,100), (screen_pos[0]-(bar_width-3)/2, screen_pos[1]+21, (bar_width-3)*min(1, health_ratio), 3))
                            if health_ratio > 1:
                                absorption_ratio = health_ratio - 1
                                pygame.draw.rect(frame_surf, (255,220,90), (screen_pos[0]+(bar_width-3)*(0.5-absorption_ratio), screen_pos[1]+21, (bar_width-3)*absorption_ratio, 3)) 

                        map_size = msg["map_size"]
                        center = relative_pos[0] + map_size[0]//2 - px, (600-relative_pos[1]) + map_size[1]//2 - py
                        mask = pygame.Surface(size, pygame.SRCALPHA)
                        mask.fill((255, 0, 0, 120))  # semi-transparent red
                        pygame.draw.circle(mask, (0, 0, 0, 0), center, int(info["stormsize"]))  # transparent center
                        frame_surf.blit(mask, (0, 0))


                    except Exception as e:
                        print(f"[client] failed to construct image: {e}")
                        continue

                    w, h = size
                    px, py = info["positions"][self.player_id]
                    crop_w, crop_h = 600, 600

                    x0 = int(px - crop_w / 2)
                    y0 = int(py - crop_h / 2)

                    # clamp so we don't go out of bounds
                    x0 = max(0, min(x0, w - crop_w))
                    y0 = max(0, min(y0, h - crop_h))

                    relative_pos = (px - x0, 600 + y0 - py)

                    # blit and flip
                    frame_surf = pygame.transform.flip(frame_surf, False, True)

                    # fit frame to window
                    window_size = self.surface.get_size()
                    if window_size != size:
                        # scale to window size (fit)
                        frame_surf = pygame.transform.scale(frame_surf, window_size)

                    scale = window_size[1] / 600

                    for n, obj in enumerate(players):
                        kills = obj[13]
                        if kills < 3:
                            kill_color = (255, 255, 255)
                        elif kills < 5:
                            kill_color = (255, 215, 0)
                        else:
                            colorscale = (min(10, kills)-5) / 5
                            kill_color = ((1-colorscale)*255+colorscale*140, (1-colorscale)*40, colorscale*120)

                        if obj[3] > 0:
                            color = (255,255,255)
                        else:
                            color = (190,190,190)
                            kill_color = color

                        dx, dy = obj[1]-player_pos[0], obj[2]-player_pos[1]
                        screen_pos = screen_pos2[n]
                        text_surf = self.name_font.render(f"{str(info['names'][obj[12]])}", True, color)
                        text_rect = text_surf.get_rect(center=(scale * screen_pos[0], scale * (600-screen_pos[1]-40)))
                        frame_surf.blit(text_surf, text_rect)
                        if kills > 0:
                            kill_surf = self.name_font.render(f"💀{obj[13]}", True, color)
                            kill_surf.fill(kill_color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
                            kill_rect = kill_surf.get_rect(center=(text_rect.center[0], text_rect.center[1]-25))
                            frame_surf.blit(kill_surf, kill_rect)

                    for img, text, y in zip(
                        (self.food_img, self.wood_img, self.stone_img), 
                        (info["food"][self.hover_player], info["wood"][self.hover_player], info["stone"][self.hover_player]), 
                        (420, 470, 520)):
                        frame_surf.blit(img, (15, self.surface.get_size()[1] - 600 + y))
                        text_surf = self.font.render(str(int(text)), True, (255,255,255))
                        frame_surf.blit(text_surf, (60, self.surface.get_size()[1] - 600 + y+10))

                    self.surface.blit(frame_surf, (0, 0))
                    scale = self.screen.get_height() / self.surface.get_height()
                    scaled_size = self.surface.get_width() * scale, self.surface.get_height() * scale
                    scaled_surface = pygame.transform.scale(self.surface, scaled_size)
                    scaled_rect = scaled_surface.get_rect(center=self.screen.get_rect().center)
                    self.screen.blit(scaled_surface, scaled_rect)
                    pygame.display.flip()

                    px, py = info["positions"][abs(self.hover_player)]
                    for sound in sounds:
                        sound_id, sx, sy, sc = sound
                        dist = math.dist((px, py), (sx, sy))
                        if dist > 550: 
                            continue
                        raiders.SoundUtils.playSound(sound_id, dist, sc)


                    # build action from local input and send to server
                    action = self.build_action_from_input(player_angle, relative_pos)
                    msg = {'type': 'action', 'player_id': self.player_id, 'action': action}
                    if info["names"][self.player_id] != self.name_box.text:
                        new_name = self.name_box.text
                        msg["name"] = new_name
                        if self.config["name"] != new_name:
                            self.config["name"] = new_name
                            try:
                                with open(self.config_path, "w") as f:
                                    yaml.safe_dump(self.config, f)
                                print(f"[client] Saved new player name: {new_name}")
                            except Exception as e:
                                print(f"[client] Failed to save name: {e}")
                    send_msg(self.sock, msg)


                    # lightweight tick limit to avoid burning 100% CPU
                    self.clock.tick(60)

                elif mtype == 'server_shutdown':
                    print("[client] server is shutting down")
                    break
                else:
                    # ignore unknown messages
                    pass

        except KeyboardInterrupt:
            print("[client] KeyboardInterrupt, exiting")
        finally:
            try:
                self.sock.close()
            except:
                pass
            pygame.quit()
            print("[client] stopped")


if __name__ == "__main__":
    # Example usage:
    # python game_client.py <server_ip> <port> <player_id>
    if len(sys.argv) >= 4:
        print("connecting to server")
        server_ip = sys.argv[1]
        port = int(sys.argv[2])
        player_id = int(sys.argv[3])
    else:
        server_ip = "0.0.0.0"
        port = 9999
        player_id = 0

    client = GameClient(server_ip, port, player_id)
    client.run()
