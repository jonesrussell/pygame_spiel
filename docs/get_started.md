# Get started

## Play
Complete [installation](installation.md), then launch PygameSpiel:

```bash
pygame_spiel
```

From a source checkout, `python main.py` invokes the same menu.

If the user just wants to play with the available Bots and games, the procedure is simple. After launching PygameSpiel, the main menu appears showing Game and Opponent dropdown menus which include the available games and Bots. Simply select the game and BOT and click play.

The default is Breakthrough against MCTS. Player 0 uses the mouse, and
**Opponent** controls player 1. Choose **random** or **human** as alternatives;
with **human**, both players use the mouse in turn. Close the window to exit.

For DQN, prepare the Breakthrough checkpoint as described in
[model setup](installation.md#models-and-cache-paths) before selecting Play.

## Start a game directly

The module launcher accepts the same options as `pygame_spiel` and `python main.py`:

```bash
python -m pygame_spiel.main --no-menu --game tic_tac_toe --opponent random --seed 42
```

`--no-menu` skips selection and opens the game display. Controller work and turn
advancement run synchronously during rendering; frame rate affects their pace.
The CLI opponent uses the base seed plus player ID 1, so this example uses seed 43.

| Option | Meaning |
| --- | --- |
| `--game` | `tic_tac_toe` or `breakthrough`; default `breakthrough` |
| `--opponent` | `mcts`, `random`, `human`, or Breakthrough-only `dqn`; default `mcts` |
| `--seed` | Base integer seed from 0 through 4294967294; default 42 |
| `--fps` | Frame limit from 1 through 240; default 10 |
| `--cache-dir` | Override the [user cache](installation.md#models-and-cache-paths) |
| `--model-path` | Select an external DQN checkpoint directory |
| `--help` | Show usage without opening a display or importing runtime backends |

For Python configuration and display lifetime, see [Extension APIs](extending.md).

## Register a new bot
Custom Python bot files are the developer extension for testing algorithms.
Selecting a file executes its Python code.

To dynamically add new algorithms, Pygame_spiel uses the Bot class from pyspiel as interface (pyspiel.Bot). This class is present in the OpenSpiel library, and it's currently used as template for other available algorithms in OpenSpiel (e.g., [MCTSBot](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/mcts.py), [RandomUniform](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/bots/uniform_random.py), [Human](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/bots/human.py), ...). This class offers a useful format to create a generic interface between new algorithms and Pygame_spiel. The user can create a new class, which includes the logic of their new algorithm.

### Create a Bot class
In the snippet below we show an example of a simple Bot which always select the first legal action:

```python
import pyspiel

class Dummy(pyspiel.Bot):

  def __init__(self, game, player_id):
    pyspiel.Bot.__init__(self)
    self._player_id = player_id

  def step(self, state):
    legal_actions = state.legal_actions(self._player_id)
    if not legal_actions:
      return pyspiel.INVALID_ACTION
    action = legal_actions[0] # Always choose 1st action
    return action
```
This class definition can be saved in a .py file in any folder.
**NOTE:** There are two requirements when creating a new Bot:
1) The class needs to be inherited from pyspiel.Bot
2) The class needs to have the two mandatory arguments **game** and **player_id**. While these might not be used by the Bot, Pygame_spiel expects these parameters.

### Register the  class
After launching Pygame_spiel, the user can provide the path the the Python file containing the Bot definition, which will be loaded and visible in the list of Bots (called "Opponent" in the main menu). In the *Module* dropdown menu navigate through the filesystem and select the Python file

![alt text](images/module_dropdown_1.png)

After selecting the file, the file name will be visualized below the dropdown menu as in the next image. Also, if the Python file contains classes inherited from pyspiel.Bot, the class names will be printed next to the file name. This information can be used to know if the Bots have been correctly registered or not. If no names are printed after the text "new Bots:", the classes have not been correctly registered.

![alt text](images/module_dropdown_2.png)

If the new classes are correctly registered, the class names will appear in the *Opponent* dropdown menu, after the Bots which are already available in Pygame_spiel by default (see the new class "Dummy" in the image below).

![alt text](images/module_dropdown_3.png)

After this, just click on *Play*!.
