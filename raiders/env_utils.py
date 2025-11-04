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
        mode = "god"
    ):
        self.mode = mode
        self.env = RaiderEnvironment()

        self.food_img = pygame.image.load("assets/food.png")
        self.wood_img = pygame.image.load("assets/wood.png")
        self.stone_img = pygame.image.load("assets/stone.png")
        self.font = pygame.font.Font(None, 30) 
        self.font2 = pygame.font.Font(None, 25) 

        self.scripts = []
        self.active_ids = {}

        if mode == "god":
            self.hover_player = 0
            self.camera_mode = "god"
        elif mode == "player":
            self.camera_mode = "human"
        
        self.t = time.time()
        self.framerate = 0
        self.speedup = False

        self.reset()

    def loadAgentScripts(self, agent_scripts):
        for script, num_agents, team in agent_scripts:
            self.addScript(script, team)
            for i in range(num_agents):
                id_ = self.addAgent(script=script) # team automatically assigned when passing in a script

    def addScript(self, script, team):
        script.initialize(team)
        script.__team__ = team
        self.scripts.append(script)

    def getActiveIDs(self):
        return tuple(self.active_ids.keys())

    def getAvailableID(self):
        return max(tuple(self.active_ids.keys()) + (0,))+1
    
    def addAgent(self, team=None, script=None):
        if script is None:
            if team is None:
                team_counts = self.env.getTeamCounts()
                if team_counts[0] < team_counts[1]:
                    team = 1
                else:
                    team = 2
        else:
            if team is not None:
                print("Passing in team to addAgent when a script is assigned will be overrided by the team the script is assigned to")
            team = script.__team__

        id_ = self.getAvailableID()
        if script is not None:
            script.addAgent(id_)
        self.active_ids[id_] = script
        self.env.addPlayer(id_, team)
        self.actions[id_] = [1, 1, 0, 0, 2]
        return id_

    def removeAgent(self, id_):
        if id_ not in self.active_ids:
            print(f"Tried to remove inactive id {id_}")
        script = self.active_ids[id_]
        if script is not None:
            script.removeAgent(id_)
        self.env.removePlayer(id_)
        del self.active_ids[id_]
        del self.actions[id_]

    def reset(self):
        self.actions = {id_: [1, 1, 0, 0, 2] for id_ in self.env.players.keys()}
        observations, info = self.env.reset()

        for script in self.scripts:
            team = script.__team__
            team_observation = info.team_observations[team]
            script.handleTeamObservation(team_observation)
        
        for id_, script in self.active_ids.items():
            if script is None: continue
            action = script.getAction(observations[id_], id_)
            self.actions[id_] = action

    def step(self, display=False, debug=False):   
        observations, rewards, terminated, truncated, info = self.env.step(self.actions)

        for script in self.scripts:
            team = script.__team__
            team_observation = info.team_observations[team]
            script.handleTeamObservation(team_observation)
        
        for id_, script in self.active_ids.items():
            if script is None: continue
            action = script.getAction(observations[id_], id_)
            self.actions[id_] = action
        
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
            for id_, script in self.active_ids.items():
                script.debug(self.env.surface, id_)
        
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
AgentScripts = discoverAgents()

if __name__ == "__main__":
    agent_scripts = [
        (AgentScripts.PlayerAgent(), 1, "defender"),
        (AgentScripts.NewAgent(), 3, "defender"),
        (AgentScripts.BasicAgent(), 8, "raider")
    ]

    env = RaiderEnvironmentWrapper()
    env.loadAgentScripts(agent_scripts)
    env.reset()
    c = 0
    while True:
        if c == 0:
            env.reset()
            c = -1
        elif c > 0:
            c -= 1
        obs, reward, done, term, info = env.step(display=True, debug=True)
        if done:
            c = 5*30
