class BaseAgent():
    def __init__(self):
        pass

    def initialize(self, agent_ids, team):
        # agent script initialization
        '''
        INPUTS:
        agent_id is a list of id's (ints) that the script is responsible for controlling
        team is either 1 (defender) or 2 (raider)

        no outputs necessary
        '''
        pass

    def step(self, observations, team_observations):
        # each agent outputs an action when step is called
        '''
        INPUTS:
        observations is a list of observations, observations are defined as nested AttrDicts
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
        
        team_observations contains observations of every teammate, not just the ones being controlled by the script

        OUTPUTS:
        action is defined as 5 ints:
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
        pass

    def debug(self, surface):
        # called when display=True and debug=True in the environment wrapper, for your visual debugging needs
        '''
        INPUTS:
        surface is a pygame surface where everything being displayed is being blitted to

        no outputs necessary
        '''
        pass

    def getNames(self):
        # return the names of your agents as strings, just for fun
        pass