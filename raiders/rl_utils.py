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
from sound_utils import SoundUtils
from agents.base_agent import BaseAgent
from agents.player_agent import PlayerAgent

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
        self.hover_player = 1
        self.camera_mode = mode
        
        self.t = time.time()
        self.framerate = 0
        self.speedup = False

        self.reset()

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

    def step(self, display=False, sounds=False, debug=False):   
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
            self.display(self.hover_player, sounds, debug)
        
        return observations, rewards, terminated, truncated, info
    
    def display(self, player_id, sounds, debug):
        old_camera_scale = self.env.camera.scale
        old_camera_center = self.env.camera.frame_rect.center

        if not (self.mode == "god" and self.camera_mode == "god"):
            self.env.camera.scale = 300
            player_obj = self.env.players[player_id]
            self.env.camera.frame_rect.center = player_obj.pos

            if sounds:
                self.playSounds(player_obj.pos, self.env.sounds)

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
    
    def calculateReward(self, player_events):
        '''
        change_food
        change_wood
        change_stone
        change_health
        change_health_enemy_player
        damage_dealt_enemy_structure
        change_health_team_player
        damage_dealt_team_structure
        killed_enemy_player
        died
        self_damage_dealt_base
        damage_dealt_base
        '''

        
pygame.init()

# example usage
if __name__ == "__main__":

    env = RaiderEnvironmentWrapper(mode="god")
    env.reset()
    c = 0
    while True:
        if c == 0:
            env.reset()
            c = -1
        elif c > 0:
            c -= 1
        obs, reward, done, term, info = env.step(display=True, sounds=True, debug=False)
        if done:
            c = 5*30
