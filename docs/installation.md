# Installation

## Prerequisites

Use Python 3.10+ and an environment that can provide these dependencies:

| Dependency | Requirement | Purpose |
| --- | --- | --- |
| OpenSpiel | API target `1.3`; local build or `[spiel]` | Game rules and built-in controllers |
| NumPy | `>=1.23.5,<2` | Controller random-number generators |
| Pygame | `pygame==2.5.0` | Display, input and rendering |
| pygame-menu | `pygame-menu==4.4.3` | Interactive selection menu |

Playing requires a local graphical display. Python version metadata alone does
not establish that compatible dependency wheels exist for an operating system
or interpreter. Read the [qualification limits](#qualification-limits) before use.

## Install

Run from the repository root in the environment you intend to use:

```bash
python -m pip install ".[spiel]"
```

Then follow [Getting started](get_started.md). The console command is
`pygame_spiel`; `python -m pygame_spiel.main` invokes the same entry point.

For an existing local OpenSpiel source build, install without requesting that extra:

```bash
python -m pip install .
```

This command does not request an OpenSpiel distribution and therefore does not ask
the resolver to replace a research build. Provide importable `pyspiel` and
`open_spiel` from a local 1.3-compatible build; see
[OpenSpiel source installation](https://github.com/google-deepmind/open_spiel/blob/v1.3/docs/install.md).
Local changes require integration checks; arbitrary versions are not qualified.

PEP 517 source builds use setuptools 84.0.0 and wheel 0.48.0, as declared in
[pyproject.toml](../pyproject.toml). The Python 3.10 minimum covers the build backend
and ZIP resource APIs. Transitive runtime dependencies are not fully locked.

## Optional DQN and download support

Install the extras you need from the repository root:

```bash
python -m pip install ".[tensorflow]"
python -m pip install ".[download]"
```

The `tensorflow` extra provides TensorFlow 2.13.0 for the Breakthrough DQN
controller. TensorFlow imposes additional Python and NumPy constraints. Selecting
DQN imports OpenSpiel's TensorFlow v1 adapter, which disables TensorFlow v2
behavior in that process. Random and MCTS controllers do not import that adapter.

The `download` extra provides gdown 5.2.2 for the explicit checkpoint downloader.
Imports and game/controller construction do not download weights.

## Models and cache paths

With download support installed, this command requests the upstream Breakthrough
TensorFlow checkpoint archive:

```bash
python -m pygame_spiel.downloads breakthrough
```

The downloader prints the checkpoint directory. The application uses that location
when no model override is supplied:

```bash
python -m pygame_spiel.main --no-menu --game breakthrough --opponent dqn
```

These commands require an available archive and a compatible checkpoint. Archive
availability and integrity, and checkpoint restoration, are unqualified. The
downloader refuses an existing destination. An externally supplied checkpoint
can be selected with `--model-path`; its directory must contain the selected
player's `q_network_pidN` and `target_q_network_pidN` index/data files. The CLI
opponent is player 1.

Cache selection uses the first applicable setting:

1. `--cache-dir`, or `ModelPaths(cache_dir=...)` in Python.
2. `PYGAME_SPIEL_CACHE_DIR`.
3. The platform default below.

| Platform | Default cache directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%/pygame_spiel`, falling back to `~/AppData/Local/pygame_spiel` |
| macOS | `~/Library/Caches/pygame_spiel` |
| Linux | `$XDG_CACHE_HOME/pygame_spiel`, falling back to `~/.cache/pygame_spiel` |

The checkpoint subdirectory is `models/dqn/breakthrough/weights_default`.
Use the same cache override for the downloader and the application. `--model-path`
overrides the application's checkpoint lookup independently of the cache directory.

Path lookup creates no directories. Downloaded models and mutable files belong
outside the `pygame_spiel` package directory; paths resolving inside it are
rejected. Packaged image assets are read through `importlib.resources` and must
be treated as read-only inputs.

## Qualification limits

Real OpenSpiel/Pygame integration, interactive display behavior and TensorFlow
checkpoint restoration are not qualified. No operating-system/Python/backend
combination is certified by the package metadata. Python 3.10 satisfies the
declared minimum; it has not been exercised as an integration environment.

The headless test suite checks configuration, ownership and construction
contracts using backend doubles and NumPy. Those checks and successful package
builds do not qualify real game, rendering or model behavior. Use a suitable
integration environment to verify the complete dependency set before relying on
the application.

The application supports only the two fixed-size, two-player games described in
the [README](../README.md). Chance, simultaneous play, hidden-information policy
interfaces, additional player counts and remote controllers require further work.
