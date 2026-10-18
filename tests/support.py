"""Explicit test doubles. These are NOT real backend compatibility checks."""

from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


class Bot:
    def __init__(self):
        self.informed = []
        self.closed = False

    def inform_action(self, state, player, action):
        self.informed.append((len(state.moves), player, action))

    def step(self, state):
        return state.legal_actions()[0]

    def close(self):
        self.closed = True


class UniformRandomBot(Bot):
    def __init__(self, player_id, rng):
        super().__init__()
        self.player_id = player_id
        self.rng = rng


class MCTSBot(Bot):
    def __init__(self, game, uct_c, max_simulations, evaluator, **params):
        super().__init__()
        self.uct_c, self.max_simulations = uct_c, max_simulations
        self.evaluator, self.params = evaluator, params


class State:
    def __init__(self, name):
        self.name = name
        self.moves = []
        self.terminal = False

    def current_player(self):
        return -4 if self.terminal else len(self.moves) % 2

    def is_terminal(self):
        return self.terminal

    def legal_actions(self, player_id=None):
        if self.terminal or (player_id is not None and player_id != self.current_player()):
            return []
        return [action for action in range(9) if action not in self.moves]

    def apply_action(self, action):
        if action not in self.legal_actions():
            raise AssertionError("Test double received illegal action")
        self.moves.append(action)

    def to_string(self):
        return ("8bbbbbbbb\n7bbbbbbbb\n6........\n5........\n4........\n3........\n"
                "2wwwwwwww\n1wwwwwwww\n abcdefgh\n") if self.name == "breakthrough" else "........."

    def rewards(self):
        return [0, 0]

    def observation_tensor(self, player_id):
        return [player_id, len(self.moves)]


class SpielGame:
    def __init__(self, name="tic_tac_toe"):
        self.name = name

    def num_players(self):
        return 2

    def new_initial_state(self):
        return State(self.name)

    def observation_tensor_shape(self):
        return [3, 3, 3]

    def get_type(self):
        return SimpleNamespace(provides_information_state_tensor=False)

    def num_distinct_actions(self):
        return 9


def runtime_modules():
    names = ["pyspiel", "open_spiel", "open_spiel.python", "open_spiel.python.bots",
             "open_spiel.python.bots.human", "open_spiel.python.bots.uniform_random",
             "open_spiel.python.algorithms", "open_spiel.python.algorithms.mcts"]
    modules = {name: ModuleType(name) for name in names}
    for name, module in modules.items():
        module.__path__ = []
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(modules[parent], child, module)
    modules["pyspiel"].Bot = Bot
    modules["pyspiel"].INVALID_ACTION = -1
    modules["pyspiel"].load_game = Mock(side_effect=lambda name, params: SpielGame(name))
    modules["open_spiel.python.bots.human"].HumanBot = Bot
    modules["open_spiel.python.bots.uniform_random"].UniformRandomBot = UniformRandomBot
    mcts = modules["open_spiel.python.algorithms.mcts"]
    mcts.MCTSBot = MCTSBot
    mcts.RandomRolloutEvaluator = Mock(side_effect=lambda count, rng: (count, rng))
    return modules


def pygame_module():
    module = ModuleType("pygame")
    for name in ("init", "quit", "display", "draw", "image", "font", "transform", "time", "event", "mouse"):
        setattr(module, name, Mock())
    module.QUIT = 256
    return module
