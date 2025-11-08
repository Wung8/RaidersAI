import pygame
import numpy as np
import random, math, os
import keyboard as k
from attrdict import AttrDict
import math, time
from enum import Enum

from agents.base_agent import BaseAgent

def dist2(v1, v2):
    return (v2[0]-v1[0])**2 + (v2[1]-v1[1])**2

class BasicAgent(BaseAgent):
    class States(Enum): # basic agent states
        IDLE = 0
        EXPLORING = 1
        GATHERING = 2
        REGROUPING = 3
        ATTACKING = 4
        RETREATING = 5
        SEIGING = 6

    class AgentState():
        DEFAULT_ACTION = [1, 1, 0, 0, 2]

        def __init__(self, agent_script, agent_id):
            self.agent_script = agent_script
            self.agent_id = agent_id
            self.state = self.agent_script.States.IDLE
            self.action = self.DEFAULT_ACTION[:]
            self.target_pos = None
            self.patience = -1
            self.base_is_objective = False
        
        def changeState(self, state):
            self.state = state
            self.target_pos = None
            self.patience = -1

    def __init__(self):
        self.solid_objects = ("spike", "stonewall", "woodwall", "turret", "stone", "tree", "bush")
        self.structures = ("spike", "stonewall", "woodwall", "turret")

        self.font = pygame.font.Font(None, 20)
        self.state_texts = {
            s: pygame.transform.flip(
                self.font.render(s.name, True, (255,255,255)), False, True)
            for s in self.States
        }

    def initialize(self, team):
        self.team = 1 if team=="defender" else 2
        self.agent_states = {}
        self.agent_ids = []

    def addAgent(self, id_):
        self.agent_states[id_] = self.AgentState(self, id_)
        self.agent_ids.append(id_)
        return f"BasicAgent{id_}"

    def removeAgent(self, id_):
        self.agent_states.remove(id_)
        self.agent_ids.remove(id_)

    def teamStr(self, team):
        return "defender" if team == 1 else "raider"

    def getAction(self, observation, id_):
        # each agent outputs an action when step is called
        '''
        Observation is defined as nested AttrDicts
        observation:
            metadata: 
                colors: color information
                map_size: map size
                center: map center x,y
                screen_size: screen size
                screen_center: screen center x,y
                time: current game timestep
                storm_size: current storm size
            vector_obs:
                [0]: player team
                [1]: player health scaled
                [2]: player food scaled
                [3]: player wood scaled
                [4]: player stone scaled
            self:
                player_info
            <object type>:
                list of infos of nearby object of type <object type>


        Action is defined as 5 ints:
        action:
            [0]: action_x (0: left, 1: none, 2: right)
            [1]: action_y (0: down, 1: none, 2: up)
            [2]: select_active
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
            [3]: place/attack (0: none, 1: action)
            [4]: action_angle
                    0: rotate 22.5° clockwise
                    1: rotate 5.625° clockwise
                    2: no rotation
                    3: rotate 5.625° counterclockwise
                    4: rotate 22.5° counterclockwise
        '''

        self.obs = observation
        self.state = self.agent_states[id_]

        if (self.highOnResources() or self.obs.metadata.time > 180*20) and not self.state.base_is_objective:
            self.state.base_is_objective = True
            self.state.changeState(self.States.IDLE)

        state = self.state.state

        if self.state.base_is_objective and (self.teamStr(self.team) != "raider" or not self.lowOnResources(50)):
            if state is self.States.GATHERING and (self.state.target_pos is not None and dist2(self.state.target_pos, self.obs.metadata.center) > 210**2):
                self.state.state = self.States.IDLE
                state = self.state.state

        match state: # basic agent operates on a Finite State Automaton
            case self.States.IDLE:
                self.handleIdle()
            case self.States.EXPLORING:
                self.handleExploring()
            case self.States.GATHERING:
                self.handleGathering()
            case self.States.REGROUPING:
                self.handleRegrouping()
            case self.States.ATTACKING:
                self.handleAttacking()
            case self.States.RETREATING:
                self.handleRetreating()
            case self.States.SEIGING:
                self.handleSeiging()
        
        # no hitting friendly turrets
        if self.state.action[2] in (1,3):
            for obj in self.obs.turret:
                if obj.team != self.team: continue
                dist = math.dist(obj.position, self.obs.self.position)
                if dist < 90:
                    dx, dy = obj.position[0] - self.obs.self.position[0], obj.position[1] - self.obs.self.position[1]
                    d_angle = (self.obs.self.angle - math.atan2(dy, dx)) % math.pi

                    if dist < 50 or min(abs(d_angle-math.pi), d_angle) < math.pi * 0.8 / (math.dist(obj.position, self.obs.self.position) / 30):
                        if self.state.state in (self.States.ATTACKING, self.States.SEIGING, self.States.RETREATING):
                            self.state.action[2] = 2
                        else:
                            self.state.action[3] = 0
                            self.moveTowardsPos(obj.position, away=True)

        # autoheal
        if self.obs.self.health <= 15 and self.obs.self.food >= 15 and random.random() < 0.05:
            self.state.action[2] = 9
            self.state.action[3] = 1
        # autoapproach heals
        nearby_heals = self.obs.heal
        closest_heal, dist = self.getClosestObject(nearby_heals)
        if self.state.state != self.States.RETREATING and closest_heal is not None and dist < 50 and self.obs.self.health < 18:
            self.moveTowardsPos(closest_heal.position, move_threshold=10)
        # autoavoid frags
        nearby_frags = self.obs.frag
        frag_avg_position = self.averagePositionOfObjects(nearby_frags)
        if frag_avg_position != (0,0):
            self.moveTowardsPos(frag_avg_position, away=True)

        return self.agent_states[id_].action
    

    def handleTeamObservation(self, team_observation):
        '''
        handle any macro team-wide decision making
        '''
        self.observations = team_observation

        self.sample_id = tuple(team_observation.keys())[0]
        if team_observation[self.sample_id].metadata.time == 1:
            for agent_id in self.agent_ids:
                self.agent_states[agent_id].base_is_objective = False

        if team_observation[self.sample_id].metadata.time > 180*20: # 3 minutes
            for agent_id in self.agent_ids:
                self.agent_states[agent_id].base_is_objective = True
        
        if self.__team__ == "raider":
            self.handleTeamObservationsRaider(team_observation)
        else:
            self.handleTeamObservationsDefender(team_observation)
    

    def handleTeamObservationsRaider(self, team_observations):
        pass


    def handleTeamObservationsDefender(self, team_observations):
        # handle defender decision making
        enemies_near_base = 0
        teammates_defending_base = []
        for id_, state in self.agent_states.items():
            self.obs = self.observations[id_]
            self.state = self.agent_states[id_]

            if self.state.base_is_objective:
                teammates_defending_base.append(id_)

        seen_enemies = set()
        for id_, obs in team_observations.items():
            enemies = [player for player in obs.player if player.team != self.team]
            for enemy in enemies:
                if enemy.id_ in seen_enemies: continue
                seen_enemies.add(enemy.id_)
                if dist2(enemy.position, team_observations[self.sample_id].metadata.center) < 400:
                    enemies_near_base += 1

        necessary_defenders = min(enemies_near_base + 2, len(self.agent_ids))

        if len(teammates_defending_base) == necessary_defenders:
            return
        
        teammates_sorted = sorted(self.agent_ids, 
                                  key=lambda id_: \
                                    self.observations[id_].self.food +\
                                    self.observations[id_].self.wood +\
                                    self.observations[id_].self.stone)
        if len(teammates_defending_base) < necessary_defenders: 
            # make teammates with most resources defenders
            for agent_id in teammates_sorted[::-1]:
                if self.agent_states[agent_id].base_is_objective:
                    continue
                self.agent_states[agent_id].base_is_objective = True
                teammates_defending_base.append(agent_id)
                if len(teammates_defending_base) == necessary_defenders:
                    break
        elif len(teammates_defending_base) > necessary_defenders:
            # make teammates with least resources non defenders
            for agent_id in teammates_sorted:
                self.obs = self.observations[agent_id]
                self.state = self.agent_states[agent_id]

                if (not self.agent_states[agent_id].base_is_objective) or self.highOnResources():
                    continue
                self.agent_states[agent_id].base_is_objective = False
                teammates_defending_base.remove(agent_id)
                if len(teammates_defending_base) == necessary_defenders:
                    break
            

    def handleIdle(self):
        '''
        transition, decision-making
        '''
        # if enemies nearby 
        teammates, enemies = self.nearbyPlayers()
        if enemies:
            self.state.changeState(self.States.ATTACKING)
        # if need resources and no enemies around, explore
        else:
            self.state.changeState(self.States.EXPLORING)

        pass

    def handleExploring(self):
        '''
        wandering the map
        '''
        teammates, enemies = self.nearbyPlayers()
        if (enemies or (self.teamStr(self.team) == "raider" and self.obs.base)) and not (self.lowOnResources() and self.obs.self.health <= 6):
            self.state.changeState(self.States.ATTACKING)
            return

        to_collect = self.resourcesToCollect()

        bush_nearby = False
        tree_nearby = False
        stone_nearby = False
        if 0 and self.teamStr(self.team) == "raider":
            bush_nearby = bool(self.obs.bush)
            tree_nearby = bool(self.obs.tree)
            stone_nearby = bool(self.obs.stone)
        else:
            for bush in self.obs.bush:
                if self.state.base_is_objective == (dist2(bush.position, self.obs.metadata.center) < 210**2):
                    bush_nearby = True
                    break
            for tree in self.obs.tree:
                if self.state.base_is_objective == (dist2(tree.position, self.obs.metadata.center) < 210**2):
                    tree_nearby = True
                    break
            for stone in self.obs.stone:
                if self.state.base_is_objective == (dist2(stone.position, self.obs.metadata.center) < 210**2):
                    stone_nearby = True
                    break

        if ((bush_nearby and "food" in to_collect)\
            or (tree_nearby and "wood" in to_collect) \
            or (stone_nearby and "stone" in to_collect)):
            self.state.changeState(self.States.GATHERING)
            return

        target_pos = self.state.target_pos

        if target_pos is not None: # still wandering
            reached_target = self.moveTowardsPos(target_pos)
            if self.obs.bush + self.obs.tree + self.obs.stone or self.nearbyEnemyStructures():
                dx, dy = target_pos[0]-self.obs.self.position[0], target_pos[1]-self.obs.self.position[1]
                angle = math.atan2(dy, dx)
                self.pointToAngle(angle)
                self.state.action[2] = 3
                self.state.action[3] = 1
            else:
                self.state.action[2] = 1
            if reached_target:
                self.state.changeState(self.States.IDLE)
                return
        else:
            # wander to random point on map some distance away
            if self.state.base_is_objective:
                map_size = self.obs.metadata.map_size[0]
                wander_distance_threshold = 0

                self_pos = self.obs.self.position
                target_pos = self_pos
                for i in range(15):
                    buffer = 750
                    target_pos = (random.randint(0+buffer, map_size-buffer), random.randint(0+buffer, map_size-buffer))
                    if dist2(self_pos, target_pos) > wander_distance_threshold**2:
                        break
            else:
                map_size = self.obs.metadata.map_size[0]
                wander_distance_threshold = 400

                self_pos = self.obs.self.position
                target_pos = self_pos
                for i in range(15):
                    buffer = 200
                    target_pos = (random.randint(0+buffer, map_size-buffer), random.randint(0+buffer, map_size-buffer))
                    if dist2(self_pos, target_pos) > wander_distance_threshold**2:
                        break
            
            self.state.target_pos = target_pos

        pass

    def handleGathering(self):
        '''
        collecting resources within vicinity
        '''

        teammates, enemies = self.nearbyPlayers()
        if enemies:
            self.state.changeState(self.States.ATTACKING)
            return
        
        resource_to_object = {
            "food": "bush",
            "wood": "tree",
            "stone": "stone"
        }

        if self.state.target_pos is not None:
            self.moveTowardsPos(self.state.target_pos, move_threshold=40)
            self.pointToTarget(self.state.target_pos)
            self.state.action[3] = 1
            self.state.action[2] = 3
                
            # check if object is destroyed
            obj_destroyed = True
            objects_to_collect = []
            for resource in self.resourcesToCollect():
                objects_to_collect += self.obs[resource_to_object[resource]]
            for obj in objects_to_collect:
                if dist2(obj.position, self.state.target_pos) < 5**2:
                    obj_destroyed = False
            if obj_destroyed:
                self.state.changeState(self.States.IDLE)
        else:
            min_dist = math.inf
            closest_object = None
            for resource in self.resourcesToCollect():
                valid_objects = [obj for obj in self.obs[resource_to_object[resource]] if self.state.base_is_objective == (dist2(obj.position, self.obs.metadata.center) < 210**2)]
                n_closest_object, n_min_dist = self.getClosestObject(valid_objects)
                if n_min_dist < min_dist:
                    min_dist = n_min_dist
                    closest_object = n_closest_object

            if closest_object:
                self.state.target_pos = closest_object.position
            else:
                self.state.changeState(self.States.IDLE)


        pass

    def handleRegrouping(self):
        '''
        group with other teammates
        '''
        pass

    def handleAttacking(self):
        '''
        advance on enemies and deal damage
        '''
        teammates, enemies = self.nearbyPlayers()

        if self.lowOnResources(30) or self.obs.self.health <= 6:
            self.state.changeState(self.States.RETREATING)
            return

        if len(teammates) + 1 < len(enemies):
            self.state.changeState(self.States.SEIGING)
            return
        
        if not enemies:
            if self.teamStr(self.team) == "raider" and self.obs.base:
                self.state.patience = 90
                base = self.obs.base[0]
                self.moveTowardsPos(base.position, move_threshold=50)
                self.pointToTarget(base.position)
                self.state.action[2] = 1
                self.state.action[3] = 1
                return
            if self.state.patience < 0:
                self.state.patience = 90
            elif self.state.patience == 0:
                self.state.changeState(self.States.IDLE)
            else:
                if self.state.target_pos:
                    self.moveTowardsPos(self.state.target_pos)
                self.state.patience -= 1
            return
        self.state.patience = 90

        target, dist = self.getClosestObject(enemies)
        self.state.target_pos = target.position

        structures_between_target = [obj for obj in self.objectsInWay(self.state.target_pos) if \
                                     dist2(obj.relative_position, (0,0)) < dist**2 and obj.type in self.structures]
        if len(structures_between_target) > 5:
            self.state.changeState(self.States.SEIGING)
            return
        
        for object in structures_between_target:
            if object.type in ("spike", "turret"):
                self.state.changeState(self.States.SEIGING)
                return
        
        self.moveTowardsPos(target.position)

        spike_threshold = 50
        if dist < spike_threshold and self.placeSpike(target.position):
            return

        melee_threshold = 60
        self.pointToTarget(target.position)
        self.state.action[3] = 1
        if dist > melee_threshold:
            if not self.objectsInWay(target.position, 5):
                self.state.action[2] = 2
            else:
                self.state.action[2] = 3
        else:
            self.state.action[2] = 1
    
    def placeSpike(self, target_pos):
        dist = 15 + 1.4*17 + 10
        dx, dy = dist*math.cos(self.obs.self.angle), dist*math.sin(self.obs.self.angle)
        spike_pos = np.add(self.obs.self.position, (dx,dy))
        for obj in self.obs.bush + self.obs.tree + self.obs.stone + self.obs.woodwall + self.obs.stonewall + self.obs.turret:
            if math.dist(obj.position, spike_pos) <= obj.size + 20:
                return False
        self.moveTowardsPos(target_pos)
        self.pointToTarget(target_pos)
        self.state.action[2] = 7
        self.state.action[3] = 1
        return True

    def handleRetreating(self):
        '''
        run away from enemies
        '''
        teammates, enemies = self.nearbyPlayers()
        if not (self.lowOnResources(40) or self.obs.self.health <= 10 or len(teammates) + 1 < len(enemies)):
            self.state.changeState(self.States.IDLE)
            return
        
        if not enemies:            
            if self.state.patience == -1:
                self.state.patience = 30
            elif self.state.patience == 0:
                self.state.changeState(self.States.IDLE)
            else:
                if self.state.target_pos is not None:
                    self.moveTowardsPos(self.state.target_pos, away=True)
                    self.pointToTarget(self.state.target_pos, away=True)
                self.state.patience -= 1
            return
        self.state.patience = 30

        target, dist = self.getClosestObject(enemies)
        self.state.target_pos = target.position
        self.moveTowardsPos(target.position, away=True)

        melee_threshold = 60
        self.pointToTarget(target.position)
        if dist > melee_threshold:
            if not self.objectsInWay(target.position, 5):
                if self.obs.self.health < 8 and random.random() < 0.1:
                    self.state.action[2] = 5
                    self.state.action[3] = 1
                else:
                    self.state.action[2] = 2
            else:
                self.state.action[2] = 3
                self.pointToTarget(target.position, away=True)
        else:
            if not self.lowOnResources(20) and random.random() < 0.3 and self.placeSpike(target.position):
                return
            else:
                self.state.action[2] = 1
        self.state.action[3] = 1


    def handleSeiging(self):
        '''
        hold a position and clear a path forward
        '''
        # advantage: plenty of resources and more teammates than enemies
        #   - expend resources to push forward
        # disadvantage: not enough resources or significantly fewer teammates
        #   - save resources and stall, or retreat
        # neutral
        #   - focus on positive resource trading

        teammates, enemies = self.nearbyPlayers()

        closest_enemy, dist = self.getClosestObject(enemies)
        if closest_enemy is None:
            if self.state.patience < 0:
                self.state.patience = 30
            elif self.state.patience == 0:
                self.state.changeState(self.States.IDLE)
            else:
                if self.handleTurrets(): return
                if self.handleSpikes(): return
                self.state.patience -= 1
            return
        
        self.state.patience = -1
        if not self.lowOnResources(resource_threshold=100) and len(teammates) >= len(enemies):
            seige_state = "advantage"
        elif self.lowOnResources(resource_threshold=30) or (len(teammates)+1) * 1.7 <= len(enemies):
            seige_state = "disadvantage"
        else:
            seige_state = "neutral"
        
        if seige_state == "advantage":
            spike_threshold = 30
            melee_threshold = 50
            turret_threshold = 150
            range_threshold = 250
            if dist < spike_threshold and self.placeSpike(closest_enemy.position):
                return
            if dist < melee_threshold:
                self.moveTowardsPos(closest_enemy.position)
                self.pointToTarget(closest_enemy.position)
                self.state.action[2] = 1
                self.state.action[3] = 1
                return
            if dist > turret_threshold:
                self.moveTowardsPos(closest_enemy.position)
                self.pointToTarget(closest_enemy.position)
                if self.highOnResources(100, True) and math.dist(self.obs.self.position, self.obs.metadata.center) < 500 and self.placeSpike(closest_enemy.position):
                    self.state.action[2] = 8
                    self.state.action[3] = 1
                    self.moveTowardsPos(closest_enemy.position, away=True)
                    return
                elif random.random() < 0.2 :
                    self.state.action[2] = 5
                    self.state.action[3] = 1
                    return
            if dist < range_threshold and self.obs.self.wood > 15:
                objects_in_way = self.objectsInWay(closest_enemy.position)
                if not objects_in_way:
                    self.state.action[2] = 2
                    self.state.action[3] = 1
                    self.pointToTarget(closest_enemy.position)
                    self.moveTowardsPos(closest_enemy.position)
                    return
                elif len(objects_in_way) >= 5:
                    self.state.action[2] = 4
                    self.state.action[3] = 1
                    self.pointToTarget(closest_enemy.position)
                    self.moveTowardsPos(closest_enemy.position)
                    return
                
            if self.handleTurrets(): return
            if self.state.action[3] != 2 and self.handleSpikes(): return

            self.state.target_pos = self.averagePositionOfObjects(enemies)
            self.moveTowardsPos(self.state.target_pos)
            self.state.action[2] = 3
            self.state.action[3] = 1
            return
                
        if seige_state == "disadvantage":
            if self.lowOnResources() and self.obs.self.health < 6:
                self.state.state = self.States.RETREATING
                return
            # evaluate importance of defending
            important = False
            if math.dist(self.obs.self.position, self.obs.metadata.center) < 300:
                important = True
            for teammate in teammates:
                if self.agent_states[teammate.id_].state == self.States.RETREATING:
                    important = True
            if not important:
                self.state.state = self.States.RETREATING
                return

            melee_threshold = 50
            spike_threshold = 105
            range_threshold = 200
            if dist < melee_threshold:
                self.moveTowardsPos(closest_enemy.position, away=True)
                self.state.action[2] = 1
                self.state.action[3] = 1
                return
            if dist < spike_threshold and random.random() < 0.1 and self.placeSpike(closest_enemy.position):
                self.moveTowardsPos(closest_enemy.position)
                return
            if dist < range_threshold and not self.objectsInWay(closest_enemy.position) and self.obs.self.wood > 15:
                if random.random() < 0.1 and self.placeSpike(closest_enemy.position):
                    self.state.action[2] = 5
                else:
                    self.state.action[2] = 2
                self.state.action[3] = 1
                self.pointToTarget(closest_enemy.position)
                return

            wood_threshold = 40
            if self.obs.self.wood > wood_threshold and self.obs.self.health < 15:
                for enemy in enemies:
                    dist = math.dist(enemy.relative_position, (0,0))
                    if dist < 250: continue
                    structure_between_target = False
                    for obj in self.objectsInWay(enemy.position, size=30):
                        if obj.type in self.structures and obj.type != "spike":
                            structure_between_target = True
                            break

                    if not structure_between_target and random.random() < 0.2:
                        self.pointToTarget(enemy.position)
                        self.moveTowardsPos(enemy.position)
                        self.state.action[2] = 5
                        self.state.action[3] = 1
                        return              
            
            if self.handleTurrets(): return
            if self.state.action[3] != 2 and self.handleSpikes(): return
            
            self.state.target_pos = self.averagePositionOfObjects(enemies)
            self.moveTowardsPos(self.state.target_pos)
            self.state.action[2] = 3
            self.state.action[3] = 1
            return
        if seige_state == "neutral":
            spike_threshold = 40
            melee_threshold = 50
            range_threshold = 250
            if dist < spike_threshold and self.placeSpike(closest_enemy.position):
                return

            if dist < melee_threshold:
                self.moveTowardsPos(closest_enemy.position, away=True)
                self.state.action[2] = 1
                self.state.action[3] = 1
                return
            
            if dist < range_threshold and not self.objectsInWay(closest_enemy.position):
                if self.highOnResources(100, True) and math.dist(self.obs.self.position, self.obs.metadata.center) < 500 and dist > 150 and self.placeSpike(closest_enemy.position):
                    self.state.action[2] = 8
                    self.state.action[3] = 1
                    self.moveTowardsPos(closest_enemy.position, away=True)
                    return
                self.state.action[2] = 2
                self.state.action[3] = 1
                self.pointToTarget(closest_enemy.position)
                return
            
            structures_between_target = [obj for obj in self.objectsInWay(closest_enemy.position) if \
                                     math.dist(obj.relative_position, (0,0)) < dist and obj.type in self.structures]
            if len(structures_between_target) > 5:
                self.state.action[2] = 4
                self.state.action[3] = 1
                return

            wood_threshold = 40
            if self.obs.self.wood > wood_threshold and self.obs.self.health < 15:
                for enemy in enemies:
                    dist = math.dist(enemy.relative_position, (0,0))
                    if dist < 250: continue
                    structure_between_target = False
                    health_threshold = 12
                    for obj in self.objectsInWay(enemy.position, size=30):
                        if obj.type in self.structures and obj.type != "spike":
                            structure_between_target = True
                            break

                    if not structure_between_target and random.random() < 0.2:
                        self.pointToTarget(enemy.position)
                        self.moveTowardsPos(enemy.position)
                        self.state.action[2] = 5
                        self.state.action[3] = 1
                        return            
            
            if self.handleTurrets(): return
            if self.state.action[3] != 2 and self.handleSpikes(): return
            
            self.state.target_pos = self.averagePositionOfObjects(enemies)
            self.moveTowardsPos(self.state.target_pos)
            self.state.action[2] = 3
            self.state.action[3] = 1
            return

    def handleSpikes(self):
        nearby_spikes = [spike for spike in self.obs.spike if spike.team != self.team]
        if len(nearby_spikes) == 0:
            return False
        closest_spike, dist = self.getClosestObject(nearby_spikes)
        if dist > 120:
            return False
        self.moveTowardsPos(closest_spike.position, move_threshold=50)
        self.pointToTarget(closest_spike.position)
        self.state.action[2] = 3
        self.state.action[3] = 1
        return True
    
    def handleTurrets(self):
        nearby_turrets = [turret for turret in self.obs.turret if turret.team != self.team]
        if len(nearby_turrets) == 0:
            return False
        closest_turret, dist = self.getClosestObject(nearby_turrets)
        if dist > 200:
            return False
        if dist > 120:
            objects_in_way = self.objectsInWay(closest_turret.position)
            if objects_in_way:
                return False
            self.moveTowardsPos(closest_turret.position)
            self.pointToTarget(closest_turret.position)
            self.state.action[2] = 5
            self.state.action[3] = 1
        else:
            self.moveTowardsPos(closest_turret.position, move_threshold=50)
            self.pointToTarget(closest_turret.position)
            self.state.action[2] = 3
            self.state.action[3] = 1
        return True

    def objectsInWay(self, target_pos, size=None):
        if size is None:
            size = self.obs.self.size

        self_pos = self.obs.self.position
        dx, dy = target_pos[0] - self_pos[0], target_pos[1] - self_pos[1]
        
        A = -dy
        B = dx
        C = 0
        denom = max(0.01, math.sqrt(A*A + B*B))

        objects_in_way = []
        for obj in sum([self.obs[type_] for type_ in self.solid_objects], []):
            if obj.type in ("spike", "stonewall", "turret") and obj.team == self.team:
                continue
            x, y = obj.relative_position
            d = abs(A*x + B*y + C) / denom
            if d < obj.size + size and dx*x + dy*y > 0:
                objects_in_way.append(obj)

        return objects_in_way
    
    def nearbyEnemyStructures(self):
        enemy_structures = []
        for obj in self.obs.spike + self.obs.turret:
            if obj.team != self.team:
                enemy_structures.append(obj)
        return enemy_structures

    def averagePositionOfObjects(self, objects, distance_threshold=999):
        x_positions = []
        y_positions = []
        for obj in objects:
            if math.dist(obj.relative_position, (0,0)) >= distance_threshold:
                continue
            x_positions.append(obj.position[0])
            y_positions.append(obj.position[1])
        n = len(x_positions)
        return (sum(x_positions) / max(1,n), sum(y_positions) / max(1,n))

    def pointToTarget(self, target_pos, away=False):
        self_pos = self.obs.self.position
        dx, dy = target_pos[0] - self_pos[0], target_pos[1] - self_pos[1]
        if away:
            dx, dy = -dx, -dy
        target_angle = math.atan2(dy, dx)
        self.pointToAngle(target_angle)
    
    def pointToAngle(self, target_angle):
        self_angle = self.obs.self.angle
        d_angle = (target_angle - self_angle) % (2*math.pi)
        if d_angle < abs(d_angle - 2*math.pi):
            if d_angle < 0.09817: angle = 0
            elif d_angle < 0.09817*4: angle = 1
            else: angle = 2
        else:
            d_angle = abs(d_angle - 2*math.pi)
            if d_angle < 0.09817: angle = 0
            elif d_angle < 0.09817*4: angle = -1
            else: angle = -2
        a_angle = angle + 2
        self.state.action[4] = a_angle
    
    def getClosestObject(self, objects):
        self_pos = self.obs.self.position

        min_dist = math.inf
        closest_object = None
        for obj in objects:
            obj_pos = obj.position
            dist = math.dist(self_pos, obj_pos)
            if dist < min_dist:
                min_dist = dist
                closest_object = obj
        
        return closest_object, min_dist

    def nearbyPlayers(self):
        teammates, enemies = [], []
        for player_info in self.obs.player:
            if player_info.team == self.team:
                if player_info.id_ in self.agent_ids:
                    teammates.append(player_info)
            else:
                enemies.append(player_info)
        return teammates, enemies

    def moveTowardsPos(self, pos, move_threshold=5, away=False):
        self_pos = self.obs.self.position
        dx, dy = pos[0] - self_pos[0], pos[1] - self_pos[1]

        if math.dist(self_pos, pos) < 1.4*move_threshold:
            return True
        
        if away: dx, dy = -dx, -dy
        angle = math.atan2(dy, dx)
        self.moveTowardsAngle(angle)
        return

        if abs(dx) < move_threshold: ax = 1
        else: ax = 2 if (dx > 0) == (not away) else 0

        if abs(dy) < move_threshold: ay = 1
        else: ay = 2 if (dy > 0) == (not away) else 0

        self.state.action[0] = ax
        self.state.action[1] = ay

        return False
    
    def moveTowardsAngle(self, angle, rad=True):
        for spike in self.obs.spike:
            if math.dist(self.obs.self.position, spike.position) < 55:
                dx, dy = spike.position[0] - self.obs.self.position[0], spike.position[1] - self.obs.self.position[1]
                angle2 = math.atan2(dy, dx)
                da = min(0.05, angle2 - angle)
                if abs(da) < math.pi/2:
                    angle = da / abs(da) * math.pi * 0.44 + angle2
                    break


        # law of large numbers
        if rad==False: 
            angle_rad = angle / 180 * math.pi
        else:
            angle_rad = angle
        dx, dy = math.cos(angle_rad), math.sin(angle_rad)
        if dx > dy:
            ax = 2 if dx > 0 else 0
            if random.random() < abs(dy):
                ay = 2 if dy > 0 else 0
            else:
                ay = 1
        else:
            ay = 2 if dy > 0 else 0
            if random.random() < abs(dx):
                ax = 2 if dx > 0 else 0
            else:
                ax = 1
        self.state.action[0] = ax
        self.state.action[1] = ay


    def resourcesToCollect(self, resource_threshold=250):
        food, wood, stone = self.obs.self.food, self.obs.self.wood, self.obs.self.stone
        threshold2 = max(food, wood, stone) * 0.65

        toreturn = []
        if food < threshold2: toreturn.append("food")
        if wood < threshold2: toreturn.append("wood")
        if stone < threshold2: toreturn.append("stone")
        if toreturn: return toreturn

        if food < resource_threshold: toreturn.append("food")
        if wood < resource_threshold: toreturn.append("wood")
        if stone < resource_threshold: toreturn.append("stone")
        return toreturn
    
    def lowOnResources(self, resource_threshold=40):
        if self.obs.self.food < resource_threshold / 2: return True
        if self.obs.self.wood < resource_threshold: return True
        if self.obs.self.stone < resource_threshold: return True
        return False

    def highOnResources(self, resource_threshold=200, ignore_food=False):
        if not ignore_food and self.obs.self.food < resource_threshold / 2: return False
        if self.obs.self.wood < resource_threshold: return False
        if self.obs.self.stone < resource_threshold: return False
        return True
    
    def debug(self, surface, id_):
        agent_id = id_
        obs = self.observations[agent_id]
        state = self.agent_states[agent_id]

        text_surf = self.state_texts[state.state]
        # display name for demo purposes
        #text_surf = pygame.transform.flip(self.font.render("NewAgent", True, (255,255,255)), False, True)
        text_rect = text_surf.get_rect(center=(obs.self.position[0], obs.self.position[1]+30))
        surface.blit(text_surf, text_rect)
    
    def getNames(self):
        return [f"BasicAI {i}" for i in self.agent_ids]
