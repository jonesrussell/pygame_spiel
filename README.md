# Pygame_spiel

A Pygame interface for OpenSpiel board games, created by Giovanni Ortolani.

- Games: Tic Tac Toe and 8x8 Breakthrough.
- Controllers: human, random and MCTS; optional TensorFlow DQN for Breakthrough.
- Developer extension: load Python files containing custom `pyspiel.Bot` classes.

Python 3.10+, OpenSpiel, NumPy, Pygame and pygame-menu are required. Playing needs
a local graphical display. See [installation and compatibility limits](docs/installation.md)
before setting up an environment: real OpenSpiel/Pygame integration and DQN
checkpoint restoration are unqualified.

## Start

After [installing from the repository](docs/installation.md#install), open the menu:

```bash
python -m pygame_spiel.main
```

Or start a human-versus-random Tic Tac Toe game directly:

```bash
python -m pygame_spiel.main --no-menu --game tic_tac_toe --opponent random --seed 42
```

## Documentation

- [Installation](docs/installation.md): dependencies, optional DQN, models and cache paths.
- [Getting started](docs/get_started.md): menu, mouse controls and command-line options.
- [Extending the application](docs/extending.md): configuration, controller APIs and Python bot files.
- [Session and controller plan](docs/next_milestone.md): remaining work and acceptance criteria.
- [Contributing](CONTRIBUTING.md): source/package checks and backend qualification.
- [Agent instructions](AGENTS.md): owners, boundaries and documentation policy.

The application handles two-player, sequential, deterministic, perfect-information
games with fixed board geometry. Controllers run synchronously during rendering;
frame rate affects turn pacing. More seats, hidden-information policy boundaries,
and remote execution are outside the current application.

## License

[MIT](LICENSE). Copyright (c) 2023 Giovanni Ortolani.
Upstream: [giogix2/pygame_spiel](https://github.com/giogix2/pygame_spiel).
