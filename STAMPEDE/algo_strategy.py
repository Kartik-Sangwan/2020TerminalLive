import gamelib
import random
import math
import warnings
from sys import maxsize
import json

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips:

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical
  board states. Though, we recommended making a copy of the map to preserve
  the actual current map state.
"""


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
        self.sendSCRAMBLER = False

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER, BITS, CORES
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        BITS = 1
        CORES = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.enemy_health_overtime = [40]
        self.dest = 0
        self.sendSCRAMBLER = False
        self.destruct = False

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(
            game_state.turn_number))
        # Comment or remove this line to enable warnings.
        game_state.suppress_warnings(True)

        self.starter_strategy(game_state)

        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        # First, place basic defenses
        self.enemy_health_overtime.append(game_state.enemy_health)
        # self.build_defences(game_state)
        self.buildEnc(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        self.build_defences(game_state)

        self.attack(game_state)

        upgraded = self.upgrade(game_state)

        gamelib.debug_write('enemy health last time was {}'.format(
            self.enemy_health_overtime))

        gamelib.debug_write('number of units upgraded {}'.format(
            upgraded))

    def buildEnc(self, game_state):
        blue_encryptors_points = [[9, 6], [10, 6], [11, 6], [12, 6], [13, 6], [14, 6], [15, 6], [16, 6], [17, 6], [18, 6], [10, 5], [11, 5], [12, 5], [13, 5], [
            14, 5], [15, 5], [16, 5], [17, 5],
            [11, 4], [12, 4], [13, 4], [14, 4], [15, 4], [
            16, 4], [12, 3], [13, 3], [14, 3],
            [15, 3], [13, 2]]
        game_state.attempt_spawn(ENCRYPTOR, blue_encryptors_points)

    def attack(self, game_state):
        if game_state.turn_number == 0 or game_state.turn_number == 1:
            game_state.attempt_spawn(SCRAMBLER, [13, 0], 3)
            game_state.attempt_spawn(SCRAMBLER, [14, 0], 2)
        num = math.floor(game_state.get_resource(BITS) / 2)
        if self.scored_on_locations == []:
            edges = game_state.game_map.get_edge_locations(
                game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            loca = self.least_damage_spawn_location(game_state, edges)
            game_state.attempt_spawn(SCRAMBLER, loca, num*2+1)
        else:
            loca = self.scored_on_locations[-1]
            game_state.attempt_spawn(SCRAMBLER, loca, num*2+1)
        if self.sendSCRAMBLER or \
                (game_state.turn_number > 2 and self.enemy_health_overtime[-2] - 3 <= self.enemy_health_overtime[-1]):
            # pings not working properly
            # send scramblers again
            if self.scored_on_locations == []:
                game_state.attempt_spawn(SCRAMBLER, [14, 0], 2 * num + 1)
            else:
                loc = self.scored_on_locations[-1]
                game_state.attempt_spawn(SCRAMBLER, loc, 2 * num + 1)
            self.sendSCRAMBLER = True

        if not self.sendSCRAMBLER:
            if game_state.turn_number < 3:
                game_state.attempt_spawn(SCRAMBLER, [13, 0], num)
                game_state.attempt_spawn(SCRAMBLER, [14, 0], num + 1)
            else:
                if game_state.turn_number % 2 == 0:
                    game_state.attempt_spawn(PING, [13, 0], math.ceil(
                        game_state.get_resource(BITS)))
                else:
                    game_state.attempt_spawn(PING, [14, 0], math.ceil(
                        game_state.get_resource(BITS)))
            #  get attacked locations

        else:
            if self.scored_on_locations != []:
                scored_on = self.scored_on_locations[-1]
                game_state.attempt_spawn(SCRAMBLER, scored_on, math.ceil(
                    game_state.get_resource(BITS)))
            else:
                game_state.attempt_spawn(SCRAMBLER, [14, 0], math.ceil(
                    game_state.get_resource(BITS)))

    def upgrade(self, game_state):
        num_upgraded = 0
        for i in range(1, 28):
            for j in range(1, 28):
                if game_state.contains_stationary_unit([i, j]):
                    if game_state.attempt_upgrade([i, j]):
                        num_upgraded += 1
        return num_upgraded

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place destructors that attack enemy units
        # destructor_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        blue_encryptors_points = [[9, 6], [10, 6], [11, 6], [12, 6], [13, 6], [14, 6], [15, 6], [16, 6], [17, 6],
                                  [18, 6], [10, 5], [11, 5], [12, 5], [13, 5], [
                                      14, 5], [15, 5], [16, 5], [17, 5],
                                  [11, 4], [12, 4], [13, 4], [14, 4], [15, 4], [
                                      16, 4], [12, 3], [13, 3], [14, 3],
                                  [15, 3], [13, 2]]
        teal_destructors_points = [[0, 13], [27, 13], [3, 12], [7, 12], [11, 12], [15, 12], [19, 12], [23, 12], [5, 10],
                                   [9, 10], [13, 10], [17, 10], [21, 10]]

        if 8 < self.detect_unit(game_state, 0, ENCRYPTOR) < 12 and self.destruct is False:
            self.dest += game_state.attempt_spawn(
                DESTRUCTOR, teal_destructors_points)
            self.destruct = True

        if self.detect_unit(game_state, 0, DESTRUCTOR) != len(teal_destructors_points):
            self.destruct = False

        blue_encryptors_points.reverse()
        if self.detect_unit(game_state, 0, ENCRYPTOR) <= 12:
            game_state.attempt_spawn(ENCRYPTOR, blue_encryptors_points)
        else:
            # game_state.attempt_upgrade(teal_destructors_points)
            game_state.attempt_spawn(ENCRYPTOR, blue_encryptors_points, 1)

        game_state.attempt_upgrade(blue_encryptors_points)
        if self.dest >= len(teal_destructors_points):
            game_state.attempt_spawn(ENCRYPTOR, blue_encryptors_points)

    def detect_unit(self, game_state, player_index=1, unit_type=None, valid_x=None, valid_y=None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == player_index and (unit_type is None or unit.unit_type == unit_type) and (
                            valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames
        as shown in the on_action_frame function
        """
        if len(self.scored_on_locations) >= 1:
            loc = self.scored_on_locations[-1]
            for i in range(2, 7):
                for j in range(2, 7):
                    game_state.attempt_spawn(
                        DESTRUCTOR, [loc[0] + i, loc[1] + j])
                    game_state.attempt_spawn(
                        DESTRUCTOR, [loc[0] - i, loc[1] - j])
                    game_state.attempt_spawn(
                        DESTRUCTOR, [loc[0] + i, loc[1] - j])
                    game_state.attempt_spawn(
                        DESTRUCTOR, [loc[0] - i, loc[1] + j])

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(
            game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)

        # Remove locations that are blocked by our own firewalls
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(
            friendly_edges, game_state)

        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(BITS) >= game_state.type_cost(SCRAMBLER)[BITS] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]

            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.BITS] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[
                    game_state.BITS]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path:
                for path_location in path:
                    # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                    damage += len(game_state.get_attackers(path_location, 0)) * \
                        gamelib.GameUnit(
                        DESTRUCTOR, game_state.config).damage_i
                damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write(
                    "All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
