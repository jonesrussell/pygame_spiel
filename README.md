# Pygame_spiel

A Pygame interface for OpenSpiel board games, created by Giovanni Ortolani.
Play Tic Tac Toe or 8x8 Breakthrough against MCTS, or Breakthrough against a
prepared TensorFlow DQN checkpoint. Custom Python `pyspiel.Bot` files provide
a developer extension for testing algorithms.

Python 3.10+, NumPy, Pygame, pygame-menu, TensorFlow and an OpenSpiel installation
are required. Playing needs a local graphical display. OpenSpiel is an explicit
installation choice so researchers can use their source build.

After [installation](docs/installation.md), open the menu with:

```bash
pygame_spiel
```

- [Getting started](docs/get_started.md): menu and mouse controls.
- [Extension APIs](docs/extending.md): custom Python bot files and resource paths.
- [Contributing](CONTRIBUTING.md): portable source/package checks and backend limits.
- [Agent instructions](AGENTS.md): owners and change rules.

The application supports two fixed-size, sequential perfect-information games.
Controllers run synchronously in the display loop. Real backend/display integration
and checkpoint restoration remain unqualified.

[MIT](LICENSE). Copyright (c) 2023 Giovanni Ortolani.
Upstream: [giogix2/pygame_spiel](https://github.com/giogix2/pygame_spiel).
