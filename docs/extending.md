# Extending the application

This guide describes configuration and the developer APIs for the two supported
games. Install the [declared dependencies](installation.md) before constructing
games or loading Python bot files.

## Configuration

Create and validate a configuration without opening a display or loading a model:

```python
from pygame_spiel.config import (
    ControllerConfig, GameConfig, PresentationConfig, SessionConfig, validate_session,
)
from pygame_spiel.resources import ModelPaths

config = SessionConfig(
    game=GameConfig("tic_tac_toe"),
    controllers=(
        ControllerConfig(0, "human"),
        ControllerConfig(1, "mcts", seed=123, parameters={"max_simulations": 200}),
    ),
    presentation=PresentationConfig(fps=10),
    paths=ModelPaths(),
)
validate_session(config)
```

| Object | Contract |
| --- | --- |
| `GameConfig` | `tic_tac_toe` uses its default board; Breakthrough accepts only default 8x8 `rows`/`columns` parameters |
| `ControllerConfig` | Binds a controller name, parameters, seed and optional model path to a player ID |
| `PresentationConfig` | Sets frame limit and window caption; renderer geometry is fixed |
| `ModelPaths` | Resolves an external cache and its checkpoint path without creating directories |
| `SessionConfig` | Combines the settings and requires one controller each for IDs 0 and 1, sorted by player ID |

Tic Tac Toe uses a 600x600 window and a 3x3 board; Breakthrough uses a 1200x1200
window and an 8x8 board. Other game names, geometry and player counts are rejected.
`validate_session(config, registered_bots)` also checks custom names/signatures
and DQN checkpoint files before game/controller construction.

Controller parameters are detached immutable value trees: string-keyed mappings,
plain lists/tuples and `None`, boolean, integer, float, string, bytes or native
`pathlib.Path` leaves. Constructors receive independent ordinary containers,
preserving list versus tuple types. `parameters_for_constructor()` returns such
a copy. Container sharing/identity is not retained. Cycles, non-string mapping
keys and arbitrary objects such as arrays, sets, RNGs or resource handles are
rejected. Create controller-owned resources in the constructor.

## Built-in controller settings

Random, MCTS and DQN configurations require explicit integer seeds from 0 through
4294967295. Each random/MCTS controller owns its own NumPy `RandomState`.
`SessionConfig()` defaults to human player 0 and MCTS player 1 with seed 43.
Seeds describe controller configuration; they do not guarantee reproducibility
across dependency/hardware versions or frame-driven turn schedules.

| MCTS parameter | Default | Accepted value |
| --- | --- | --- |
| `uct_c` | `2.0` | Finite nonnegative number |
| `max_simulations` | `1000` | Integer at least 2 |
| `rollout_count` | `1` | Positive integer |
| `solve` | `True` | Boolean |
| `verbose` | `False` | Boolean |

DQN is available for Breakthrough with the TensorFlow extra. Its session
configuration requires an explicit external `model_path`; for the default user
cache, use `paths = ModelPaths()` and `model_path=paths.breakthrough_dqn()`.
See [model preparation](installation.md#models-and-cache-paths) for directory and
checkpoint-file requirements.

| DQN parameter | Default | Accepted value |
| --- | --- | --- |
| `hidden_layers_sizes` | `(64, 64)` | Nonempty list/tuple of positive integers |
| `replay_buffer_capacity` | `100000` | Positive integer |
| `batch_size` | `32` | Positive integer |

The DQN adapter owns its TensorFlow graph/session and uses OpenSpiel's default
information-state/observation representation selection. Agents are constructed
in player order to match the variable naming used by
[OpenSpiel's Breakthrough checkpoint example](https://github.com/google-deepmind/open_spiel/blob/v1.3/open_spiel/python/examples/breakthrough_dqn.py).
Checkpoint restoration requires real-backend qualification.

## Application and resource lifetime

To let the application own the display and event loop, run the configuration
above in an environment with the required backends and display:

```python
from pygame_spiel.main import run

run(config)
```

For construction without a display:

```python
from pygame_spiel.games.factory import GameFactory

game = GameFactory.create(config)
try:
    print(game.config.game.name)
finally:
    game.close()
```

`GameFactory.create` loads OpenSpiel and constructs controllers. It creates no
window and downloads no models. The `Game` base owns the OpenSpiel game/state
and controller lifetime. OpenSpiel determines legal actions, turn order and
terminal state. Each concrete game class handles drawing and mouse mapping.

A manual frame driver must call `game.open_display()`, handle its own Pygame
events, call `game.play(mouse_pos, mouse_pressed)` and eventually `game.close()`.
The application `run()` function manages that lifetime for callers. Closing a
game releases controller resources and its Pygame display.

For package image lookup and external model/cache paths, see
[installation](installation.md#models-and-cache-paths).

## Python bot files

Python file loading is a developer extension: selecting a module executes its
code. It accepts locally defined `pyspiel.Bot` subclasses; built-in names are
reserved and imported classes are excluded. Use code you intend to execute.

The [getting-started bot example and menu walkthrough](get_started.md#register-a-new-bot)
show how to define and register `Dummy`. Save that example as `dummy.py` for the
programmatic example below. From a source checkout, the included
[Dummy example](../pygame_spiel/bots/dummy.py) can also be selected in **Module**.

The constructor must accept `game` and `player_id`. Extra configured parameters
are keyword arguments. If a custom seed is configured, the constructor must also
accept `seed`. An optional `close()` method releases controller-owned resources.
The [OpenSpiel random bot](https://github.com/google-deepmind/open_spiel/blob/v1.3/open_spiel/python/bots/uniform_random.py)
illustrates the bot interface.

Replacing the module in the menu replaces its registry; changing games
preserves that registry and clears an incompatible opponent selection.

For programmatic loading, use the same file with typed configuration:

```python
from pygame_spiel.config import ControllerConfig, GameConfig, SessionConfig, validate_session
from pygame_spiel.controllers import register_classes
from pygame_spiel.main import run

registry = register_classes("dummy.py")
config = SessionConfig(
    game=GameConfig("tic_tac_toe"),
    controllers=(ControllerConfig(0, "human"), ControllerConfig(1, "Dummy")),
)
validate_session(config, registry)
run(config, registered_bots=registry)
```

Custom bots receive full OpenSpiel state in the current perfect-information
games. This interface does not provide hidden-information policy boundaries,
remote controllers or a named-opponent selection experience.

## Convenience APIs

- `GameFactory.get_game(name, current_player=0)` constructs a game with default
  session settings. Only `current_player=0` is accepted; controller bindings
  choose who drives each seat, and OpenSpiel owns turn order.
- `game.register_bots(mapping)` validates and replaces the custom registry.
  A replacement must include any custom controller selected by the active configuration.
- `game.set_bots(bot1_type, bot1_params, bot2_type, bot2_params)` configures players
  0 and 1 through the same typed settings. Parameter dictionaries accept `seed`;
  DQN accepts `model_path` or a checkpoint path as its params argument. The method
  constructs the replacement pair, installs it and closes the old controllers.

These convenience calls are supported for the two current games. Prefer
`GameFactory.create(SessionConfig(...))` for explicit construction.
