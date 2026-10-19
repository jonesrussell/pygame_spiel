"""TensorFlow adapter lifetime checks with explicit doubles; no model execution."""

from contextlib import nullcontext
import importlib
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from support import SpielGame, State, runtime_modules


class DQNAdapterDoubleTests(unittest.TestCase):
    def setUp(self):
        modules = runtime_modules()
        tf = ModuleType("tensorflow.compat.v1")
        graph = Mock()
        graph.as_default.side_effect = nullcontext
        tf.Graph = Mock(return_value=graph)
        tf.Session = Mock(return_value=Mock())
        tf.set_random_seed = Mock()
        for name in ("tensorflow", "tensorflow.compat"):
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        modules["tensorflow"].compat = modules["tensorflow.compat"]
        modules["tensorflow.compat"].v1 = tf
        modules["tensorflow.compat.v1"] = tf
        env = ModuleType("open_spiel.python.rl_environment")
        env.TimeStep = lambda **kwargs: SimpleNamespace(**kwargs)
        env.StepType = SimpleNamespace(MID="mid")
        modules[env.__name__] = env
        modules["open_spiel.python"].rl_environment = env
        dqn = ModuleType("open_spiel.python.algorithms.dqn")
        self.agents = []

        def new_agent(**kwargs):
            agent = Mock(arguments=kwargs)
            agent.step.return_value = SimpleNamespace(action=2)
            self.agents.append(agent)
            return agent

        dqn.DQN = Mock(side_effect=new_agent)
        modules[dqn.__name__] = dqn
        sys.modules.pop("pygame_spiel.bots.dqn", None)
        self.addCleanup(sys.modules.pop, "pygame_spiel.bots.dqn", None)
        runtime = patch.dict(sys.modules, modules)
        runtime.start()
        self.addCleanup(runtime.stop)
        self.tf = tf
        self.adapter = importlib.import_module("pygame_spiel.bots.dqn")

    def test_pair_order_seed_parameters_restore_and_session_ownership(self):
        game = SpielGame()
        with tempfile.TemporaryDirectory() as tmp, patch.object(game, "new_initial_state") as state:
            bot = self.adapter.DQNBot(game, 1, checkpoint_dir=tmp, seed=17,
                                      hidden_layers_sizes=(8, 4), batch_size=2)
        self.addCleanup(bot.close)
        self.assertEqual([a.arguments["player_id"] for a in self.agents], [0, 1])
        self.assertEqual(self.agents[1].arguments["state_representation_size"], 27)
        self.assertEqual(self.agents[1].arguments["hidden_layers_sizes"], [8, 4])
        self.assertEqual(self.agents[1].arguments["batch_size"], 2)
        self.agents[0].restore.assert_not_called()
        self.agents[1].restore.assert_called_once_with(tmp)
        self.tf.set_random_seed.assert_called_once_with(17)
        state.assert_not_called()
        session = self.tf.Session.return_value
        bot.close()
        bot.close()
        session.close.assert_called_once()

    def test_restore_failure_closes_session(self):
        original = self.adapter.DQN

        def fail_restore(**kwargs):
            agent = original(**kwargs)
            agent.restore.side_effect = ValueError("bad checkpoint")
            return agent

        with tempfile.TemporaryDirectory() as tmp, patch.object(self.adapter, "DQN", side_effect=fail_restore):
            with self.assertRaisesRegex(ValueError, "bad checkpoint"):
                self.adapter.DQNBot(SpielGame(), 1, checkpoint_dir=tmp)
        self.tf.Session.return_value.close.assert_called_once()

    def test_information_tensor_dimensions_match_environment_default(self):
        game = SpielGame()
        game.get_type = lambda: SimpleNamespace(provides_information_state_tensor=True)
        game.information_state_tensor_shape = lambda: [4, 5]
        bot = self.adapter.DQNBot(game, 1)
        self.addCleanup(bot.close)
        self.assertEqual(self.agents[1].arguments["state_representation_size"], 20)
        state = State("tic_tac_toe")
        state.moves.append(0)
        state.information_state_tensor = lambda player: [99, player]
        bot.step(state)
        self.assertEqual(self.agents[1].step.call_args.args[0].observations["info_state"],
                         [[99, 0], [99, 1]])

    def test_step_uses_evaluation_and_rejects_wrong_turn_or_terminal(self):
        bot = self.adapter.DQNBot(SpielGame(), 1)
        self.addCleanup(bot.close)
        state = State("tic_tac_toe")
        with self.assertRaisesRegex(ValueError, "different player"):
            bot.step(state)
        state.moves.append(0)
        self.assertEqual(bot.step(state), 2)
        call = self.agents[1].step.call_args
        self.assertTrue(call.kwargs["is_evaluation"])
        self.assertEqual(call.args[0].observations["info_state"], [[0, 1], [1, 1]])
        state.terminal = True
        self.assertEqual(bot.step(state), -1)
        self.agents[1].step.assert_called_once()


if __name__ == "__main__":
    unittest.main()
