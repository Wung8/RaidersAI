class BaseAgent():
    def __init__(self):
        pass

    def initialize(self, team):
        # agent script initialization, assume the team will not change
        '''
        INPUTS:
        team is a string, either "raider" or "defender"

        no outputs necessary
        '''
        pass

    def addAgent(self, id_):
        # register new agent id that this script will be controlling
        '''
        INPUTS:
        id_ is the id of the new agent that this script will control

        OUTPUTS:
        a string representing the name you want to call the new agent
        '''
        pass

    def removeAgent(self, id_):
        # unregister agent id that this script will no longer be controlling
        '''
        INPUTS:
        id_ is the id of the agent that this script will no longer control

        no outputs necessary
        '''
        pass

    def handleTeamObservation(self, team_observation):
        # handle team coordination, called before getting the actions of individual agents
        '''
        INPUTS:
        team_observations is a dictionary of observations, one for each agent on your team, regardless if
        your script controls them or not. observations can be accessed using "team_observations[id_]". 
        observations are explained further in the getAction function

        no outputs necessary
        '''
        pass

    def getAction(self, observation, id_):
        # each agent outputs an action when step is called
        '''
        INPUTS:
        observation is a nested AttrDict (a dictionary where you access values like "dict.key" instead of "dict['key']")
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