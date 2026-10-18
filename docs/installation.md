# Installation

## Prerequisites

Use Python 3.10+ and a local graphical display. Python 3.10/3.11 are the intended
setup targets for the legacy dependency pins; metadata does not guarantee wheels
on every Python version or operating system.

| Dependency | Requirement | Purpose |
| --- | --- | --- |
| Pygame | `2.5.0` | Display and input |
| pygame-menu | `4.4.3` | Selection menu |
| NumPy | `>=1.23.5,<2` | Controllers; TensorFlow may narrow this range |
| TensorFlow | `2.13.0` | Eagerly imported DQN adapter, including MCTS-only launches |
| OpenSpiel | API target `1.3` | Rules and bots; supply locally or use `[spiel]` |
| gdown | `5.2.2`, optional `[download]` | Explicit checkpoint download |

## Install

From the repository root, choose one OpenSpiel workflow.

For the pinned convenience dependency:

```bash
python -m pip install ".[spiel]"
```

For an existing local OpenSpiel source build:

```bash
python -m pip install .
```

The second command does not request an OpenSpiel distribution and therefore does
not ask the resolver to replace a research build. Provide importable `pyspiel`
and `open_spiel` from a local 1.3-compatible build; see
[OpenSpiel source installation](https://github.com/google-deepmind/open_spiel/blob/v1.3/docs/install.md).
This preserves the installation choice, not a compatibility claim for arbitrary
OpenSpiel versions. Local modifications need their own integration checks.

PEP 517 builds use setuptools 84.0.0 and wheel 0.48.0 from
[pyproject.toml](../pyproject.toml). The Python minimum matches the backend and ZIP
resource APIs. Transitive runtime dependencies are not fully locked. The
[contributor setup](../CONTRIBUTING.md) installs a smaller source-check environment.

## Models and cache paths

The application reads models from external user-owned storage and never downloads
them during game construction. With download support installed, explicitly fetch
the upstream Breakthrough archive:

```bash
python -m pip install ".[download]"
python -m pygame_spiel.downloads breakthrough
```

The downloader prints the checkpoint path and refuses an existing destination.
`pygame_spiel_download` is the equivalent installed command. For an alternate cache:

```bash
python -m pygame_spiel.downloads breakthrough --cache-dir /path/to/cache
```

Set `PYGAME_SPIEL_CACHE_DIR` to that same directory before launching the menu.
Without an override, Windows uses `%LOCALAPPDATA%/pygame_spiel` (fallback
`~/AppData/Local/pygame_spiel`), macOS uses `~/Library/Caches/pygame_spiel`, and Linux
uses `$XDG_CACHE_HOME/pygame_spiel` (fallback `~/.cache/pygame_spiel`). Checkpoints
live below `models/dqn/breakthrough/weights_default`. Lookup creates no directories.
Paths resolving within the `pygame_spiel` package are rejected. Packaged PNGs are
read-only resources accessed through `importlib.resources`.

The Python `set_bots` API also accepts an external DQN checkpoint directory;
see [extension APIs](extending.md). An absent checkpoint fails locally with an
explicit preparation command. Archive availability/integrity and restoration are
unqualified; only download code invoked explicitly can contact the archive host.

## Qualification limits

Real OpenSpiel/Pygame/menu integration, display behavior and checkpoint restoration
are unqualified. Source/unit tests use explicit doubles and do not certify any
Python/platform/backend combination. Python 3.10 matches the declared minimum;
minimum-version integration has not been established. TensorFlow 2.13 imposes
additional platform/Python/NumPy constraints; provision a compatible environment
before using the application. No dependency compatibility follows from a package
archive building successfully. See [backend qualification](../CONTRIBUTING.md#backend-qualification).
