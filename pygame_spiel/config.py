"""Small immutable configuration objects; importing/validating opens no display."""

from dataclasses import dataclass, field
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

from pygame_spiel.resources import ModelPaths, user_path


GAME_SIZES = MappingProxyType({"tic_tac_toe": (600, 600), "breakthrough": (1200, 1200)})
BUILTIN_BOTS = ("mcts", "random", "human", "dqn")
DEFAULT_SEED = 42
MAX_SEED = 2**32 - 1
MCTS_DEFAULTS = MappingProxyType({
    "uct_c": 2.0, "max_simulations": 1000, "rollout_count": 1,
    "solve": True, "verbose": False,
})
DQN_DEFAULTS = MappingProxyType({
    "hidden_layers_sizes": (64, 64), "replay_buffer_capacity": 100000, "batch_size": 32,
})


class _FrozenList(tuple):
    """Immutable list snapshot; distinguish it from tuples when copying kwargs."""

    __slots__ = ()


def _freeze_parameter(value, active=None):
    """Snapshot a settings value tree; never retain arbitrary mutable objects."""
    if type(value) in (type(None), bool, int, float, str, bytes, type(Path())):
        return value
    if not isinstance(value, Mapping) and type(value) not in (list, tuple, _FrozenList):
        raise ValueError(f"Unsupported controller parameter value: {type(value).__name__}")
    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise ValueError("Controller parameter containers must be acyclic")
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            if any(type(key) is not str for key in value):
                raise ValueError("Controller parameter mapping keys must be strings")
            return MappingProxyType({key: _freeze_parameter(item, active) for key, item in value.items()})
        items = (_freeze_parameter(item, active) for item in value)
        return _FrozenList(items) if type(value) in (list, _FrozenList) else tuple(items)
    finally:
        active.remove(identity)


def _copy_parameter(value):
    """Restore ordinary containers, freshly allocated for each constructor call."""
    if isinstance(value, Mapping):
        return {key: _copy_parameter(item) for key, item in value.items()}
    if isinstance(value, _FrozenList):
        return [_copy_parameter(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_parameter(item) for item in value)
    return value


def _integer(value, name, minimum=0, maximum=None):
    if (type(value) is not int or value < minimum
            or (maximum is not None and value > maximum)):
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum or 'unbounded'}]")


def available_bots(game_name):
    if not isinstance(game_name, str) or game_name not in GAME_SIZES:
        raise ValueError(f"Unsupported game {game_name!r}; choose from {tuple(GAME_SIZES)}")
    return ("mcts", "random", "human", "dqn") if game_name == "breakthrough" else (
        "mcts", "random", "human"
    )


def default_controller(player_id, kind, parameters=None, model_path=None):
    """Defaults for menus and the two-player controller convenience API."""
    params = dict(parameters or {})
    seed = params.pop("seed", DEFAULT_SEED + player_id if kind in ("random", "mcts", "dqn") else None)
    return ControllerConfig(player_id, kind, seed, params, model_path)


@dataclass(frozen=True)
class GameConfig:
    name: str = "breakthrough"
    parameters: Mapping = field(default_factory=dict)

    def __post_init__(self):
        available_bots(self.name)
        if not isinstance(self.parameters, Mapping):
            raise ValueError("Game parameters must be a mapping")
        params = dict(self.parameters)
        # Existing drawing/input geometry supports only the default board sizes.
        allowed = {"rows": 8, "columns": 8} if self.name == "breakthrough" else {}
        if any(key not in allowed or type(value) is not int or value != allowed[key]
               for key, value in params.items()):
            raise ValueError(f"Unsupported renderer parameters for {self.name}: {params}")
        object.__setattr__(self, "parameters", MappingProxyType(params))


@dataclass(frozen=True)
class ControllerConfig:
    player_id: int
    kind: str
    seed: Optional[int] = None
    parameters: Mapping = field(default_factory=dict)
    model_path: Optional[Path] = None

    def __post_init__(self):
        _integer(self.player_id, "player_id")
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("Controller kind must be a nonempty name")
        if self.seed is not None:
            _integer(self.seed, "controller seed", maximum=MAX_SEED)
        if self.kind in ("random", "mcts", "dqn") and self.seed is None:
            raise ValueError(f"An explicit RNG seed is required for {self.kind}")
        if not isinstance(self.parameters, Mapping):
            raise ValueError("Controller parameters must be a mapping")
        params = dict(self.parameters)
        defaults = MCTS_DEFAULTS if self.kind == "mcts" else (
            DQN_DEFAULTS if self.kind == "dqn" else {}
        )
        if self.kind in BUILTIN_BOTS:
            unknown = set(params) - set(defaults)
            if unknown:
                raise ValueError(f"Unsupported {self.kind} parameters: {sorted(unknown)}")
            params = {**defaults, **params}
        if self.kind == "mcts":
            # OpenSpiel 1.3 first evaluates the root, then expands its children.
            _integer(params["max_simulations"], "max_simulations", minimum=2)
            _integer(params["rollout_count"], "rollout_count", minimum=1)
            value = params["uct_c"]
            if (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError("uct_c must be finite and nonnegative")
            for key in ("solve", "verbose"):
                if type(params[key]) is not bool:
                    raise ValueError(f"{key} must be a bool")
        if self.kind == "dqn":
            for key in ("replay_buffer_capacity", "batch_size"):
                _integer(params[key], key, minimum=1)
            if not isinstance(params["hidden_layers_sizes"], (tuple, list)):
                raise ValueError("hidden_layers_sizes must be a sequence of positive integers")
            layers = tuple(params["hidden_layers_sizes"])
            if not layers:
                raise ValueError("hidden_layers_sizes must not be empty")
            for size in layers:
                _integer(size, "hidden layer size", minimum=1)
            params["hidden_layers_sizes"] = layers
            if self.model_path is None:
                raise ValueError("dqn requires an explicit model_path; download separately if needed")
        elif self.model_path is not None:
            raise ValueError("model_path is only supported by dqn")
        if set(params) & {"game", "player_id", "seed", "checkpoint_dir"}:
            raise ValueError("Controller parameters cannot override construction arguments")
        object.__setattr__(self, "parameters", _freeze_parameter(params))
        if self.model_path is not None:
            object.__setattr__(self, "model_path", user_path(self.model_path))

    def parameters_for_constructor(self) -> dict:
        """Give a constructor an independent mutable copy of its settings."""
        return _copy_parameter(self.parameters)


@dataclass(frozen=True)
class PresentationConfig:
    fps: int = 10
    caption: str = "Pygame Open Spiel"

    def __post_init__(self):
        _integer(self.fps, "fps", minimum=1, maximum=240)
        if not isinstance(self.caption, str) or not self.caption.strip():
            raise ValueError("caption must be a nonempty string")
        # Window geometry remains with the existing fixed-size renderers.


@dataclass(frozen=True)
class SessionConfig:
    game: GameConfig = field(default_factory=GameConfig)
    controllers: Tuple[ControllerConfig, ...] = field(default_factory=lambda: (
        default_controller(0, "human"), default_controller(1, "mcts"),
    ))
    presentation: PresentationConfig = field(default_factory=PresentationConfig)
    paths: ModelPaths = field(default_factory=ModelPaths)

    def __post_init__(self):
        if not isinstance(self.game, GameConfig):
            raise ValueError("game must be a GameConfig")
        if not isinstance(self.presentation, PresentationConfig) or not isinstance(self.paths, ModelPaths):
            raise ValueError("presentation/paths must be PresentationConfig/ModelPaths")
        controllers = tuple(self.controllers)
        if not all(isinstance(c, ControllerConfig) for c in controllers):
            raise ValueError("controllers must contain ControllerConfig objects")
        ids = [c.player_id for c in controllers]
        if sorted(ids) != [0, 1]:
            raise ValueError("Existing renderers require exactly one controller for players 0 and 1")
        for controller in controllers:
            if (controller.kind in BUILTIN_BOTS
                    and controller.kind not in available_bots(self.game.name)):
                raise ValueError(f"{controller.kind} is unsupported for {self.game.name}")
        object.__setattr__(self, "controllers", tuple(sorted(controllers, key=lambda c: c.player_id)))


def validate_session(config: SessionConfig, registered_bots=None):
    """Validate all selections and model files before loading a game/controller."""
    import inspect

    if not isinstance(config, SessionConfig):
        raise ValueError("Expected a SessionConfig")
    registry = dict(registered_bots or {})
    for name, constructor in registry.items():
        if not isinstance(name, str) or not name or name in BUILTIN_BOTS or not isinstance(constructor, type):
            raise ValueError(f"Invalid or reserved registered bot: {name!r}")
    for controller in config.controllers:
        if controller.kind not in BUILTIN_BOTS:
            if controller.kind not in registry:
                raise ValueError(f"Unsupported bot {controller.kind!r}; register it before construction")
            kwargs = controller.parameters_for_constructor()
            kwargs.update(game=None, player_id=controller.player_id)
            if controller.seed is not None:
                kwargs["seed"] = controller.seed
            try:
                inspect.signature(registry[controller.kind]).bind(**kwargs)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid constructor parameters for {controller.kind}: {exc}") from exc
        if controller.kind == "dqn":
            path = controller.model_path
            if not path.is_dir():
                raise FileNotFoundError(f"DQN checkpoint directory not found: {path}; download explicitly")
            for name in ("q_network", "target_q_network"):
                prefix = f"{name}_pid{controller.player_id}"
                if (not (path / f"{prefix}.index").is_file()
                        or not any(file.is_file() for file in path.glob(f"{prefix}.data-*"))):
                    raise FileNotFoundError(f"Missing DQN checkpoint files for {prefix} in {path}")
    return registry
