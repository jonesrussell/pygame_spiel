"""Pure configuration tests; no OpenSpiel/Pygame or neural runtime."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pygame_spiel.config import (
    ControllerConfig, GameConfig, PresentationConfig, SessionConfig, default_controller,
    validate_session,
)
from pygame_spiel.games.factory import GameFactory
from pygame_spiel.resources import ModelPaths


ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def test_defaults_are_explicit_and_controllers_sorted_by_player(self):
        config = SessionConfig()
        self.assertEqual(config.controllers[1].seed, 43)
        self.assertEqual(config.controllers[1].parameters["max_simulations"], 1000)
        self.assertEqual(replace(config, controllers=config.controllers[::-1]).controllers,
                         config.controllers)

    def test_unknown_game_and_unsupported_geometry(self):
        for kwargs in ({"name": "unsupported_game"}, {"name": []}, {"parameters": None},
                       {"parameters": {"rows": 6}},
                       {"name": "tic_tac_toe", "parameters": {"foo": 1}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GameConfig(**kwargs)
        self.assertEqual(dict(GameConfig(parameters={"rows": 8, "columns": 8}).parameters),
                         {"rows": 8, "columns": 8})

    def test_invalid_controller_values(self):
        cases = [
            {"player_id": -1}, {"player_id": True}, {"seed": None}, {"seed": -1},
            {"seed": 2**32}, {"seed": True}, {"kind": ""},
            {"parameters": {"max_simulations": 0}}, {"parameters": {"max_simulations": 1}},
            {"parameters": None}, {"parameters": {"solve": 1}},
            {"parameters": {"uct_c": float("nan")}}, {"parameters": {"rollout_count": 0}},
            {"parameters": {"unrecognized": 3}},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                ControllerConfig(**dict({"player_id": 1, "kind": "mcts", "seed": 10}, **overrides))

    def test_invalid_players_and_presentation(self):
        for ids in ((0,), (0, 0), (0, 2), (0, 1, 2)):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                SessionConfig(controllers=tuple(ControllerConfig(i, "human") for i in ids))
        for fps in (0, -1, True, 241, 10.5):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                PresentationConfig(fps=fps)
        with self.assertRaises(ValueError):
            PresentationConfig(caption=" ")

    def test_mapping_inputs_are_copied_and_defaults_cannot_be_modified(self):
        params = {"max_simulations": 20}
        config = ControllerConfig(1, "mcts", 5, params)
        params["max_simulations"] = 0
        self.assertEqual(config.parameters["max_simulations"], 20)
        with self.assertRaises(TypeError):
            config.parameters["solve"] = False

    def test_nested_custom_settings_detach_from_caller_and_remain_read_only(self):
        class Custom:
            def __init__(self, game, player_id, options):
                pass

        options = {"choices": ["first"], "variants": ({"weights": [1.0]},)}
        config = ControllerConfig(1, "Custom", parameters={"options": options})
        validate_session(SessionConfig(controllers=(ControllerConfig(0, "human"), config)),
                         {"Custom": Custom})
        options["choices"][0] = "caller-mutated"
        options["variants"][0]["weights"].append(2.0)
        stored = config.parameters["options"]
        self.assertEqual(list(stored["choices"]), ["first"])
        self.assertEqual(list(stored["variants"][0]["weights"]), [1.0])
        with self.assertRaises(TypeError):
            stored["extra"] = True
        with self.assertRaises(TypeError):
            stored["choices"][0] = "mutated"

    def test_custom_settings_reject_objects_nonstring_keys_and_cycles(self):
        class Mutable:
            pass

        cycle = []
        cycle.append(cycle)
        mapping_cycle = {}
        mapping_cycle["self"] = mapping_cycle
        for value in (Mutable(), {1, 2}, bytearray(b"mutable"), cycle, mapping_cycle, {1: "key"}):
            with self.subTest(type=type(value).__name__), self.assertRaises(ValueError):
                ControllerConfig(1, "Custom", parameters={"options": value})

    def test_constructor_copies_preserve_value_types_and_survive_dataclass_replace(self):
        options = {"choices": ["first"], "pair": ({"weights": [1.0]},),
                   "scalar": (None, True, 3, 1.5, "value", b"bytes", Path("model"))}
        config = ControllerConfig(1, "Custom", parameters={"options": options})
        copied = replace(config, seed=9).parameters_for_constructor()["options"]
        self.assertEqual(copied, options)
        self.assertIs(type(copied), dict)
        self.assertIs(type(copied["choices"]), list)
        self.assertIs(type(copied["pair"]), tuple)
        self.assertIs(type(copied["pair"][0]["weights"]), list)
        copied["choices"].append("mutated")
        self.assertEqual(config.parameters_for_constructor()["options"], options)

    def test_invalid_selection_fails_before_factory_import(self):
        config = replace(SessionConfig(), controllers=(
            ControllerConfig(0, "human"), ControllerConfig(1, "missing"),
        ))
        with patch("pygame_spiel.games.factory.import_module") as imported:
            with self.assertRaisesRegex(ValueError, "Unsupported bot"):
                GameFactory.create(config)
            imported.assert_not_called()
        for name, current in (("missing", 0), ("breakthrough", 1)):
            with self.assertRaises(ValueError):
                GameFactory.get_game(name, current)

    def test_custom_constructor_validation_and_reserved_names(self):
        class Custom:
            def __init__(self, game, player_id, strength):
                pass

        config = replace(SessionConfig(), controllers=(
            ControllerConfig(0, "human"), ControllerConfig(1, "Custom", parameters={"strength": 7}),
        ))
        validate_session(config, {"Custom": Custom})
        self.assertIsNone(default_controller(1, "Custom").seed)
        with self.assertRaisesRegex(ValueError, "constructor"):
            validate_session(replace(config, controllers=(config.controllers[0],
                             ControllerConfig(1, "Custom"))), {"Custom": Custom})
        for registry in ({"mcts": Custom}, {"bad": object()}, {"": Custom}):
            with self.assertRaises(ValueError):
                validate_session(SessionConfig(), registry)

    def test_neural_path_and_parameters_are_validated_without_backend_import(self):
        with self.assertRaisesRegex(ValueError, "model_path"):
            ControllerConfig(1, "dqn", seed=3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            controller = ControllerConfig(1, "dqn", 3, model_path=path)
            config = replace(SessionConfig(), controllers=(ControllerConfig(0, "human"), controller))
            with self.assertRaisesRegex(FileNotFoundError, "q_network_pid1"):
                validate_session(config)
            for name in ("q_network", "target_q_network"):
                (path / f"{name}_pid1.index").touch()
                (path / f"{name}_pid1.data-00000-of-00001").touch()
            validate_session(config)
            with self.assertRaisesRegex(ValueError, "unsupported"):
                replace(config, game=GameConfig("tic_tac_toe"))
            with self.assertRaises(ValueError):
                ControllerConfig(1, "dqn", 3, {"hidden_layers_sizes": []}, path)
        with self.assertRaises(ValueError):
            ControllerConfig(1, "random", 3, model_path="somewhere")

    def test_pure_imports_and_validation_do_not_import_runtime_or_download(self):
        code = '''
import importlib.abc, sys
blocked = ('pygame', 'pygame_menu', 'pyspiel', 'open_spiel', 'tensorflow', 'torch', 'gdown', 'numpy')
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in blocked:
            raise AssertionError('Unexpected runtime import: ' + fullname)
sys.meta_path.insert(0, Block())
import pygame_spiel
import pygame_spiel.config, pygame_spiel.controllers, pygame_spiel.resources
import pygame_spiel.downloads, pygame_spiel.main, pygame_spiel.menu
import pygame_spiel.games.tic_tac_toe, pygame_spiel.games.breakthrough
from pygame_spiel.config import SessionConfig, validate_session
validate_session(SessionConfig())
from pygame_spiel.menu import Menu
Menu()
from pygame_spiel.main import parse_args
parse_args(['--game', 'tic_tac_toe', '--opponent', 'random', '--no-menu'])
assert not any(name.split('.')[0] in blocked for name in sys.modules)
'''
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_open_spiel_reports_both_installation_choices(self):
        from pygame_spiel.controllers import register_classes

        with patch.dict(sys.modules, {"pyspiel": None}):
            for construct in (lambda: GameFactory.create(SessionConfig()),
                              lambda: register_classes("unused.py")):
                with self.subTest(construct=construct), self.assertRaisesRegex(
                        ImportError, r"pygame_spiel\[spiel\].*local OpenSpiel 1.3"):
                    construct()


if __name__ == "__main__":
    unittest.main()
