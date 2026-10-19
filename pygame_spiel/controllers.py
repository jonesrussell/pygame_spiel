"""Controller discovery/construction without any display or download ownership."""

import importlib
import importlib.util
import hashlib
from pathlib import Path
import sys

from pygame_spiel.config import ControllerConfig, SessionConfig, validate_session


def register_classes(file_path: str) -> dict:
    """Execute a user-selected Python file and discover locally defined pyspiel.Bot classes."""
    try:
        import pyspiel
    except ImportError as exc:
        raise ImportError("Install pygame_spiel[spiel] or provide a compatible local OpenSpiel 1.3 build") from exc

    path = Path(file_path).resolve(strict=True)
    if path.suffix != ".py":
        raise ValueError("Bot module must be a Python file")
    name = "_pygame_spiel_bot_" + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load bot module: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    return {
        name: obj for name, obj in vars(module).items()
        if isinstance(obj, type) and obj is not pyspiel.Bot
        and obj.__module__ == module.__name__ and issubclass(obj, pyspiel.Bot)
    }


def build_controller(game, config: ControllerConfig, registered_bots=None):
    """Construct a validated controller. RandomState belongs to this controller alone."""
    if not 0 <= config.player_id < game.num_players():
        raise ValueError(f"Player {config.player_id} is outside this game's player range")
    params = config.parameters_for_constructor()
    if config.kind == "dqn":
        try:
            module = importlib.import_module("pygame_spiel.bots.dqn")
        except ImportError as exc:
            raise ImportError("DQN requires the 'pygame_spiel[tensorflow]' extra and OpenSpiel") from exc
        return module.DQNBot(game, config.player_id, checkpoint_dir=config.model_path,
                             seed=config.seed, **params)
    if config.kind in ("mcts", "random"):
        import numpy as np

        rng = np.random.RandomState(config.seed)
        if config.kind == "random":
            from open_spiel.python.bots.uniform_random import UniformRandomBot

            return UniformRandomBot(config.player_id, rng)
        from open_spiel.python.algorithms import mcts

        evaluator = mcts.RandomRolloutEvaluator(params.pop("rollout_count"), rng)
        return mcts.MCTSBot(game, params.pop("uct_c"), params.pop("max_simulations"),
                            evaluator, random_state=rng, **params)
    if config.kind == "human":
        from open_spiel.python.bots.human import HumanBot

        return HumanBot()
    registry = dict(registered_bots or {})
    if config.kind not in registry:
        raise ValueError(f"Unsupported bot: {config.kind!r}")
    if config.seed is not None:
        params["seed"] = config.seed
    return registry[config.kind](game=game, player_id=config.player_id, **params)


def close_controllers(controllers):
    error = None
    for controller in controllers:
        close = getattr(controller, "close", None)
        if close is not None:
            try:
                close()
            except Exception as exc:
                error = error or exc
    if error is not None:
        raise error


def validate_bot_classes(registry):
    """Check the OpenSpiel interface only at the runtime construction boundary."""
    import pyspiel

    if any(not issubclass(bot, pyspiel.Bot) for bot in registry.values()):
        raise ValueError("Registered controllers must inherit from pyspiel.Bot")


def build_controllers(game, config: SessionConfig, registered_bots=None):
    registry = validate_session(config, registered_bots)
    validate_bot_classes(registry)
    if game.num_players() != len(config.controllers):
        raise ValueError("Game player count does not match the configured controllers")
    controllers = []
    try:
        for controller in config.controllers:
            controllers.append(build_controller(game, controller, registry))
    except Exception:
        close_controllers(controllers)
        raise
    return controllers
