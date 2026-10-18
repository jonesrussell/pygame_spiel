# Extension APIs

Install the [runtime dependencies](installation.md) before importing game APIs.
Game imports eagerly load Pygame, OpenSpiel and TensorFlow. Constructing a game
opens a display; resource helpers alone are safe without those backends.

## Python bot files

Custom Python files are the developer extension for testing algorithms. Loading a
file executes its code. Define a `pyspiel.Bot` subclass with keyword-compatible
`game` and `player_id` constructor arguments:

```python
import pyspiel

class FirstLegal(pyspiel.Bot):
    def __init__(self, game, player_id):
        super().__init__()
        self.player_id = player_id

    def step(self, state):
        actions = state.legal_actions(self.player_id)
        return actions[0] if actions else pyspiel.INVALID_ACTION
```

Save as `first_legal.py`. In the menu's **Module** selector, navigate to that file,
select it, then choose **FirstLegal** in **Opponent** and select **Play**. Use a
self-contained file defining the bot class. The loader in `utils.register_classes`
discovers subclasses; avoid importing unrelated Bot subclasses into the file.
Bots receive the full state of the current perfect-information game. This extension
does not provide external policy information boundaries or a named-opponent roster.

## Programmatic game setup

`GameFactory.get_game(name, current_player)` constructs one of the two fixed board
games and opens its display. The supported application uses `current_player=0`.
Call `register_bots(mapping)` before `set_bots`; the menu supplies that mapping.
For a manually driven display, handle events, call `game.play(mouse_pos,
mouse_pressed)`, flip the display and release Pygame when finished.

```python
import pygame
from pygame_spiel.games.factory import GameFactory
from pygame_spiel.resources import ModelPaths

game = GameFactory.get_game("breakthrough", current_player=0)
try:
    game.register_bots({})
    game.set_bots("human", None, "dqn", ModelPaths().breakthrough_dqn())
    # A manual driver supplies the Pygame frame/event loop here.
finally:
    pygame.quit()
```

DQN parameters accept a checkpoint directory or `None` for the default external
cache. Non-DQN parameter arguments have no effect. Checkpoint construction and
restoration require backend qualification. MCTS/random use an internal seed of 42;
there is no public seed configuration in this API.

## Resources

Use package images independently of the current working directory:

```python
from pygame_spiel.resources import asset

with asset("tic_tac_toe/x_image.png").open("rb") as stream:
    signature = stream.read(8)
```

`asset` returns an `importlib.resources` Traversable, including ZIP imports.
`ModelPaths` owns external cache lookup; `user_path` rejects package-directory
writes. See [cache selection](installation.md#models-and-cache-paths). Only
`downloads.download_weights` and its command-line entry point fetch models.
