"""Behavioral contracts isolated with explicit OpenSpiel/Pygame doubles."""

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np

from pygame_spiel.config import ControllerConfig, GameConfig, SessionConfig
from pygame_spiel.controllers import build_controller, build_controllers, register_classes
from pygame_spiel.games.factory import GameFactory
from support import Bot, SpielGame, pygame_module, runtime_modules


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.modules = runtime_modules()
        self.runtime = patch.dict(sys.modules, self.modules)
        self.runtime.start()
        self.addCleanup(self.runtime.stop)

    def test_random_bots_use_the_requested_player_and_independent_explicit_rngs(self):
        config = SessionConfig(controllers=(ControllerConfig(0, "random", 10),
                                            ControllerConfig(1, "random", 20)))
        bots = build_controllers(SpielGame(), config)
        self.assertEqual([b.player_id for b in bots], [0, 1])
        self.assertIsNot(bots[0].rng, bots[1].rng)
        self.assertEqual(bots[0].rng.randint(2**30), np.random.RandomState(10).randint(2**30))
        self.assertEqual(bots[1].rng.randint(2**30), np.random.RandomState(20).randint(2**30))
        again = build_controllers(SpielGame(), config)
        self.assertEqual(again[0].rng.randint(2**30), np.random.RandomState(10).randint(2**30))
        self.assertNotIn("tensorflow", sys.modules)
        self.assertNotIn("torch", sys.modules)

    def test_mcts_parameters_and_rng_are_forwarded(self):
        config = ControllerConfig(1, "mcts", 17, {
            "uct_c": 1.5, "max_simulations": 12, "rollout_count": 3,
            "solve": False, "verbose": True,
        })
        bot = build_controller(SpielGame(), config)
        self.assertEqual((bot.uct_c, bot.max_simulations, bot.evaluator[0]), (1.5, 12, 3))
        self.assertIs(bot.evaluator[1], bot.params["random_state"])
        self.assertFalse(bot.params["solve"])
        self.assertTrue(bot.params["verbose"])

    def test_unknown_bot_and_out_of_range_player_raise(self):
        for config in (ControllerConfig(0, "typo"), ControllerConfig(2, "random", 3)):
            with self.assertRaises(ValueError):
                build_controller(SpielGame(), config)

    def test_dummy_keeps_scalar_action_contract_when_no_legal_actions(self):
        # The shipped developer example is consumed through the bot-file loader.
        registry = register_classes(Path(__file__).resolve().parents[1] / "pygame_spiel/bots/dummy.py")
        state = SpielGame().new_initial_state()
        bot = registry["Dummy"](SpielGame(), 0)
        self.assertEqual(bot.step(state), 0)
        state.terminal = True
        self.assertEqual(bot.step(state), -1)

    def test_all_config_validation_precedes_controller_construction(self):
        config = replace(SessionConfig(), controllers=(
            ControllerConfig(0, "random", 1), ControllerConfig(1, "missing"),
        ))
        with patch("pygame_spiel.controllers.build_controller") as builder:
            with self.assertRaises(ValueError):
                build_controllers(SpielGame(), config)
            builder.assert_not_called()

    def test_construction_failure_closes_previously_created_controllers(self):
        class Broken(Bot):
            def __init__(self, game, player_id):
                raise RuntimeError("expected constructor failure")

        first = Bot()
        config = SessionConfig(controllers=(ControllerConfig(0, "human"), ControllerConfig(1, "Broken")))
        self.modules["open_spiel.python.bots.human"].HumanBot = lambda: first
        with self.assertRaisesRegex(RuntimeError, "expected constructor"):
            build_controllers(SpielGame(), config, {"Broken": Broken})
        self.assertTrue(first.closed)

    def test_missing_neural_extra_error_is_selected_only(self):
        with patch("pygame_spiel.controllers.importlib.import_module", side_effect=ImportError("no TF")) as imported:
            build_controller(SpielGame(), ControllerConfig(0, "human"))
            imported.assert_not_called()
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ImportError, r"pygame_spiel\[tensorflow\]"):
                    build_controller(SpielGame(), ControllerConfig(1, "dqn", 7, model_path=tmp))
            imported.assert_called_once_with("pygame_spiel.bots.dqn")

    def test_custom_parameters_player_seed_and_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bots.py"
            path.write_text('''import pyspiel
from dataclasses import dataclass
@dataclass
class Options:
    value: int = 4
class Custom(pyspiel.Bot):
    def __init__(self, game, player_id, strength=4, seed=None):
        super().__init__()
        self.arguments = (game, player_id, strength, seed)
''')
            registry = register_classes(str(path))
        self.assertEqual(list(registry), ["Custom"])
        game = SpielGame()
        bot = build_controller(game, ControllerConfig(0, "Custom", 11, {"strength": 9}), registry)
        self.assertEqual(bot.arguments, (game, 0, 9, 11))

    def test_constructor_mutation_cannot_change_repeated_session_construction(self):
        class Custom(Bot):
            def __init__(self, game, player_id, options):
                super().__init__()
                self.initial = options["choices"][:]
                self.options = options
                options["choices"].append("constructor-mutated")
                options["pair"][0]["weights"].append(2.0)

        options = {"choices": ["first"], "pair": ({"weights": [1.0]},)}
        config = SessionConfig(controllers=(ControllerConfig(0, "human"),
            ControllerConfig(1, "Custom", parameters={"options": options})))
        first = build_controllers(SpielGame(), config, {"Custom": Custom})[1]
        second = build_controllers(SpielGame(), config, {"Custom": Custom})[1]
        self.assertEqual(first.initial, ["first"])
        self.assertEqual(second.initial, ["first"])
        self.assertEqual(options, {"choices": ["first"], "pair": ({"weights": [1.0]},)})
        self.assertEqual(list(config.controllers[1].parameters["options"]["choices"]), ["first"])
        self.assertIsNot(first.options, second.options)
        self.assertIsNot(first.options["choices"], second.options["choices"])
        first.options["choices"][0] = "later-retained-argument-mutation"
        self.assertEqual(second.options["choices"], ["first", "constructor-mutated"])
        self.assertEqual(list(config.controllers[1].parameters["options"]["choices"]), ["first"])


class GameTests(unittest.TestCase):
    def setUp(self):
        self.modules = runtime_modules()
        self.modules["pygame"] = pygame_module()
        self.runtime = patch.dict(sys.modules, self.modules)
        self.runtime.start()
        self.addCleanup(self.runtime.stop)

    def create(self, name="tic_tac_toe", controllers=None):
        config = SessionConfig(game=GameConfig(name))
        if controllers:
            config = replace(config, controllers=controllers)
        game = GameFactory.create(config)
        self.addCleanup(game.close)
        return game

    def test_both_existing_games_construct_without_display_or_assets(self):
        for name in ("tic_tac_toe", "breakthrough"):
            game = self.create(name)
            self.assertEqual(game._game.name, name)
            self.assertEqual(game._registered_bots, {})
            self.assertEqual(game._current_player, game._state.current_player())
            self.assertIsNone(game._screen)
        self.modules["pygame"].init.assert_not_called()
        self.modules["pygame"].image.load.assert_not_called()

    def test_game_parameters_reach_open_spiel_once(self):
        config = SessionConfig(game=GameConfig("breakthrough", {"rows": 8, "columns": 8}))
        game = GameFactory.create(config)
        self.addCleanup(game.close)
        self.modules["pyspiel"].load_game.assert_called_once_with("breakthrough", {"rows": 8, "columns": 8})

    def test_factory_convenience_and_set_bots_delegate_with_real_parameters(self):
        game = GameFactory.get_game("tic_tac_toe", 0)
        self.addCleanup(game.close)
        old = list(game._bots)
        game.set_bots("random", {"seed": 7}, "mcts", {"seed": 9, "max_simulations": 14})
        self.assertEqual(game._bots[0].player_id, 0)
        self.assertEqual(game.config.controllers[0].seed, 7)
        self.assertEqual(game._bots[1].max_simulations, 14)
        self.assertTrue(all(bot.closed for bot in old))
        current = list(game._bots)
        with self.assertRaises(ValueError):
            game.set_bots("human", None, "typo", None)
        self.assertEqual(game._bots, current)
        self.assertFalse(any(bot.closed for bot in current))

    def test_registration_uses_mapping_and_same_constructor(self):
        class Custom(Bot):
            def __init__(self, game, player_id):
                super().__init__()
                self.player_id = player_id

        game = self.create()
        registry = {"Custom": Custom}
        game.register_bots(registry)
        registry.clear()
        game.set_bots("human", None, "Custom", None)
        self.assertEqual(game._bots[1].player_id, 1)
        self.assertEqual(game.config.controllers[1].kind, "Custom")
        with self.assertRaisesRegex(ValueError, "inherit"):
            game.register_bots({"Custom": Custom, "invalid": type("Invalid", (), {})})
        self.assertEqual(list(game._registered_bots), ["Custom"])

    def test_registration_rejects_non_bot_before_loading_game(self):
        self.modules["pyspiel"].load_game.reset_mock()
        with self.assertRaisesRegex(ValueError, "inherit"):
            GameFactory.create(SessionConfig(), {"invalid": type("Invalid", (), {})})
        self.modules["pyspiel"].load_game.assert_not_called()

    def test_notifications_precede_state_change_and_illegal_action_is_rejected(self):
        game = self.create()
        game._apply_action(0)
        self.assertEqual(game._bots[1].informed, [(0, 0, 0)])
        self.assertEqual(game._state.moves, [0])
        with self.assertRaisesRegex(ValueError, "Illegal action"):
            game._apply_action(0)
        self.assertEqual(game._state.moves, [0])

    def test_tic_tac_toe_occupied_click_and_board_edges(self):
        game = self.create(controllers=(ControllerConfig(0, "human"), ControllerConfig(1, "human")))
        game.open_display()
        game.play((20, 20), (True, False, False))
        game.play((20, 20), (True, False, False))
        game.play((-1, 900), (True, False, False))
        self.assertEqual(game._state.moves, [0])
        game.play((220, 20), (True, False, False))
        self.assertEqual(game._state.moves, [0, 1])
        self.assertEqual(len(game._list_o_pos), 1)
        self.assertEqual(game._get_quadrant(200, 200), 4)
        self.assertIsNone(game._get_quadrant(600, 600))

    def test_bot_player_zero_and_terminal_state_are_handled(self):
        game = self.create(controllers=(ControllerConfig(0, "random", 19), ControllerConfig(1, "human")))
        game.open_display()
        game.play((0, 0), (False, False, False))
        self.assertEqual(game._state.moves, [0])
        game._state.terminal = True
        game.play((0, 0), (True, False, False))
        self.assertEqual(game._state.moves, [0])

    def test_breakthrough_clicks_outside_board_are_ignored(self):
        game = self.create("breakthrough")
        game.open_display()
        for pos in ((-1000, -1000), (0, 0), (2000, 2000)):
            game.play(pos, (True, False, False))
        self.assertEqual(game._state.moves, [])
        self.assertEqual((game._selected_row, game._selected_col), (None, None))

    def test_display_is_explicit_idempotent_and_loads_packaged_streams(self):
        game = self.create("breakthrough")
        pygame = self.modules["pygame"]
        game.open_display()
        game.open_display()
        pygame.display.set_mode.assert_called_once_with((1200, 1200))
        self.assertEqual(pygame.image.load.call_count, 4)
        for call in pygame.image.load.call_args_list:
            self.assertTrue(call.args[0].closed)
            self.assertTrue(call.args[1].endswith(".png"))
        game.close()
        pygame.quit.assert_called_once()
        self.assertEqual(game._bots, [])

    def test_asset_failure_releases_display_and_close_failure_still_releases_others(self):
        game = self.create()
        pygame = self.modules["pygame"]
        with patch.object(game, "_load_assets", side_effect=ValueError("bad asset")):
            with self.assertRaisesRegex(ValueError, "bad asset"):
                game.open_display()
        self.assertIsNone(game._screen)
        pygame.quit.assert_called_once()
        game.open_display()
        other = game._bots[1]
        game._bots[0].close = Mock(side_effect=RuntimeError("close failure"))
        with self.assertRaisesRegex(RuntimeError, "close failure"):
            game.close()
        self.assertTrue(other.closed)
        self.assertIsNone(game._screen)
        self.assertEqual(pygame.quit.call_count, 2)


class EntryAndMenuTests(unittest.TestCase):
    def test_cli_parameters_and_early_validation(self):
        from pygame_spiel.main import parse_args

        config, no_menu = parse_args(["--game", "tic_tac_toe", "--opponent", "random",
                                      "--seed", "18", "--fps", "25", "--no-menu"])
        self.assertTrue(no_menu)
        self.assertEqual(config.controllers[1].seed, 19)
        self.assertEqual(config.presentation.fps, 25)
        for args in (["--fps", "0"], ["--opponent", "dqn", "--game", "tic_tac_toe"]):
            with self.assertRaises(ValueError):
                parse_args(args)

    def test_cli_base_seed_bounds_are_validated_before_offset(self):
        from pygame_spiel.main import parse_args

        for seed in (-1, 2**32 - 1):
            with self.assertRaisesRegex(ValueError, "Base seed"):
                parse_args(["--seed", str(seed)])
        config, _ = parse_args(["--seed", "0"])
        self.assertEqual(config.controllers[1].seed, 1)

    def test_console_entrypoint_delegates_to_run(self):
        from pygame_spiel.main import pygame_spiel

        with patch("pygame_spiel.main.run") as run:
            pygame_spiel(["--no-menu"])
            run.assert_called_once()
            self.assertIsInstance(run.call_args.args[0], SessionConfig)

    def test_application_stops_before_another_turn_on_quit_and_always_closes(self):
        from pygame_spiel.main import run

        pygame = pygame_module()
        pygame.event.get.return_value = [SimpleNamespace(type=pygame.QUIT)]
        game = Mock(_pygame=pygame)
        with patch.object(GameFactory, "create", return_value=game):
            run(SessionConfig())
        game.open_display.assert_called_once()
        game.play.assert_not_called()
        game.close.assert_called_once()

    def test_application_closes_on_display_failure(self):
        from pygame_spiel.main import run

        game = Mock()
        game.open_display.side_effect = RuntimeError("display failure")
        with patch.object(GameFactory, "create", return_value=game):
            with self.assertRaises(RuntimeError):
                run(SessionConfig())
        game.close.assert_called_once()

    def test_menu_preserves_custom_bots_and_clears_stale_opponent_on_game_change(self):
        from pygame_spiel.menu import Menu

        menu = Menu()
        menu._registered_bots = {"Custom": Bot}
        menu._menu_dropselect_opponent = Mock()
        menu._selected_opponent_type = "dqn"
        menu._select_game((("tic_tac_toe", "tic_tac_toe"), 0))
        self.assertEqual(menu.get_selected_opponent(), "mcts")
        names = [x[0] for x in menu._menu_dropselect_opponent.update_items.call_args.args[0]]
        self.assertIn("Custom", names)
        self.assertNotIn("dqn", names)
        menu._select_opponent((("random", "random"), 0))
        config = menu._selected_config()
        self.assertEqual(config.game.name, "tic_tac_toe")
        self.assertEqual(config.controllers[1].kind, "random")


if __name__ == "__main__":
    unittest.main()
