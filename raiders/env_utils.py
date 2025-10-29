import pygame
import numpy as np
import random, math, os
import importlib
import inspect
import keyboard as k
from attrdict import AttrDict
import math, time
from enum import Enum

from raiders import RaiderEnvironment
from agents.base_agent import BaseAgent
from agents.player_agent import PlayerAgent


def discoverAgents():
    agent_classes = {}
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")

    for filename in os.listdir(agents_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"agents.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseAgent) and obj is not BaseAgent:
                        agent_classes[name] = obj
            except Exception as e:
                print(f"Failed to import {module_name}: {e}")

    return AttrDict(agent_classes)

def convAngleToAction(player_angle, target_angle):
    angle = 0
    d_angle = (target_angle - (player_angle)) % (2 * math.pi)
    if d_angle < abs(d_angle - 2 * math.pi):
        if d_angle < 0.09817: angle = 0
        elif d_angle < 0.09817 * 4: angle = 1
        else: angle = 2
    else:
        d_angle = abs(d_angle - 2 * math.pi)
        if d_angle < 0.09817: angle = 0
        elif d_angle < 0.09817 * 4: angle = -1
        else: angle = -2
    angle = angle + 2  # matches PlayerAgent offset
    return angle

class RaiderEnvironmentWrapper():
    def __init__(
        self,
        teams,
        agent_scripts,
        mode = "god"
    ):
        self.mode = mode
        self.env = RaiderEnvironment()

        self.food_img = pygame.image.load("assets/food.png")
        self.wood_img = pygame.image.load("assets/wood.png")
        self.stone_img = pygame.image.load("assets/stone.png")
        self.font = pygame.font.Font(None, 30) 
        self.font2 = pygame.font.Font(None, 25) 

        self.teams = teams
        self.agent_scripts = agent_scripts
        self.num_agents = sum(teams)

        for i, (agent_ids, script) in enumerate(self.agent_scripts):
            script.initialize(agent_ids, 2-(agent_ids[0] < teams[0]))
            self.agent_scripts[i] = (agent_ids, script)
            if isinstance(script, PlayerAgent):
                player_idx = agent_ids[0]

        if mode == "god":
            self.hover_player = 0
            self.camera_mode = "god"
        elif mode == "player":
            self.hover_player = player_idx
            self.camera_mode = "human"
        
        self.t = time.time()
        self.framerate = 0
        self.speedup = False

        self.reset()

    def reset(self):
        self.actions = [[1, 1, 0, 0, 2] for agent_id in range(self.num_agents)]
        observations, info = self.env.reset(self.teams)

        team_observations = [ observations[:self.teams[0]], observations[self.teams[0]:] ]

        for agent_ids, agent_script in self.agent_scripts:
            script_observations = []
            names = agent_script.getNames()
            for n, agent_id in enumerate(agent_ids):
                self.env.players[agent_id].name = names[n]
                script_observations.append(observations[agent_id])
            actions = agent_script.step(observations=script_observations, team_observations=team_observations[agent_ids[0] < self.teams[0]])
            for agent_id, action in zip(agent_ids, actions):
                self.actions[agent_id] = action

    def step(self, display=False, debug=False):   
        observations, rewards, terminated, truncated, info = self.env.step(self.actions)
        team_observations = [ observations[:self.teams[0]], observations[self.teams[0]:] ]

        for (agent_ids, agent_script) in self.agent_scripts:
            script_observations = []
            for agent_id in agent_ids:
                script_observations.append(observations[agent_id])
            actions = agent_script.step(observations=script_observations, team_observations=team_observations[agent_ids[0] < self.teams[0]])
            for agent_id, action in zip(agent_ids, actions):
                self.actions[agent_id] = action
        
        if self.mode == "god":
            self.cameraControl()

        if display:
            self.display(self.hover_player, debug)
        
        return observations, rewards, terminated, truncated, info
    
    def display(self, player_id, debug=False):
        old_camera_scale = self.env.camera.scale
        old_camera_center = self.env.camera.frame_rect.center

        if not (self.mode == "god" and self.camera_mode == "god"):
            self.env.camera.scale = 300
            player_obj = self.env.players[player_id]
            self.env.camera.frame_rect.center = player_obj.pos

        if debug:
            for agent_ids, script in self.agent_scripts:
                script.debug(self.env.surface)
        
        frame = self.env.camera.getFrame(self.env.surface)
        frame = pygame.transform.flip(frame, False, True)

        if not (self.mode == "god" and self.camera_mode == "god"):
            for img, text, y in zip(
                (self.food_img, self.wood_img, self.stone_img), 
                (player_obj.food, player_obj.wood, player_obj.stone), 
                (420, 470, 520)):
                frame.blit(img, (15, y))
                text_surf = self.font.render(str(int(text)), True, (255,255,255))
                frame.blit(text_surf, (60, y+10))

        pygame.transform.scale(frame, self.env.screen_size, self.env.screen)
        t = self.env.t // 20
        m, s = str(t // 60), ('00'+str(t % 60))[-2:]
        text_surf = self.font2.render(f"{m}:{s}", True, (255,255,255))
        text_rect = text_surf.get_rect(midright=(780, 40))
        self.env.screen.blit(text_surf, text_rect)
        text_surf = self.font2.render(str(self.framerate), True, (255,255,255))
        text_rect = text_surf.get_rect(midright=(780, 20))
        self.env.screen.blit(text_surf, text_rect)
        pygame.display.flip()

        self.framerate = int(1 / (time.time() - self.t))
        if self.speedup:
            self.env.clock.tick(60)
        else:    
            self.env.clock.tick(20)
        self.t = time.time()

        self.env.camera.scale = old_camera_scale
        self.env.camera.frame_rect.center = old_camera_center


    def cameraControl(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Check for KEYDOWN events
            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_SPACE:
                    self.camera_mode = ["god", "hover_player"][self.camera_mode == "god"]
                    print(self.camera_mode)
                
                if self.camera_mode == "hover_player":
                    if event.key == pygame.K_COMMA:
                        self.hover_player = (self.hover_player - 1) % self.num_agents
                        print(self.hover_player)
                    if event.key == pygame.K_PERIOD:
                        self.hover_player = (self.hover_player + 1) % self.num_agents
                        print(self.hover_player)
        
        keys = pygame.key.get_pressed()

        if keys[pygame.K_EQUALS]:
            self.env.camera.scale *= 0.9
        if keys[pygame.K_MINUS]:
            self.env.camera.scale /= 0.9
        if keys[pygame.K_f]:
            self.speedup = True
        else:
            self.speedup = False
            
        if keys[pygame.K_LEFT]: self.env.camera.frame_rect.move_ip(-10,0)
        if keys[pygame.K_RIGHT]: self.env.camera.frame_rect.move_ip(10,0)
        if keys[pygame.K_DOWN]: self.env.camera.frame_rect.move_ip(0,-10)
        if keys[pygame.K_UP]: self.env.camera.frame_rect.move_ip(0,10)
        
pygame.init()
agents = discoverAgents()

if __name__ == "__main__":
    agent_scripts = [
        ([8], agents.PlayerAgent()),
        ([0,1,2,3,4,5,6,7], agents.BasicAgent()),
        ([9,10,11,12], agents.BasicAgent())
    ]

    env = RaiderEnvironmentWrapper(
        teams = [5,8],
        agent_scripts = agent_scripts,
        mode="god"
    )
    c = 0
    while True:
        if c == 0:
            env.reset()
            c = -1
        elif c > 0:
            c -= 1
        obs, reward, done, term, info = env.step(display=True)
        if done:
            c = 5*30