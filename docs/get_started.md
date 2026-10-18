# Getting started

Complete [installation](installation.md) in the environment you will use. Real
backend and display qualification limits are listed in that guide.

## Play from the menu

```bash
python -m pygame_spiel.main
```

1. Choose `tic_tac_toe` or `breakthrough` in **Game**.
2. Choose a controller in **Opponent**: `mcts`, `random`, `human`, or `dqn`
   for Breakthrough with a [prepared checkpoint](installation.md#models-and-cache-paths).
3. Select **Play**.

Player 0 is human-controlled; **Opponent** controls player 1. The default
selection is Breakthrough against MCTS. Choosing `human` lets both players use
the mouse in turn.

For Tic Tac Toe, click a legal empty cell. For Breakthrough, click one of the
acting player's pawns, then its destination. Clicking the selected pawn again
deselects it. Moves stop at a terminal state; close the window to exit.

The optional **Module** selector loads Python code for the
[developer bot-file extension](extending.md#python-bot-files). Ordinary play with
built-in controllers does not require a bot file.

## Start a game directly

Bypass the menu to play Tic Tac Toe against the random controller:

```bash
python -m pygame_spiel.main --no-menu --game tic_tac_toe --opponent random --seed 42
```

The CLI assigns the opponent seed as the base `--seed` plus player ID 1, so this
example uses opponent seed 43. Frame rate affects the pace of bot turns.

| Option | Meaning |
| --- | --- |
| `--game` | `tic_tac_toe` or `breakthrough`; default `breakthrough` |
| `--opponent` | `mcts`, `random`, `human`, or Breakthrough-only `dqn`; default `mcts` |
| `--seed` | Base integer seed from 0 through 4294967294; default 42 |
| `--fps` | Frame limit from 1 through 240; default 10 |
| `--no-menu` | Start the configured game directly |
| `--cache-dir` | Override the [user cache](installation.md#models-and-cache-paths) |
| `--model-path` | Select an external DQN checkpoint directory |
| `--help` | Show usage without opening a display |

View the complete options:

```bash
python -m pygame_spiel.main --help
python -m pygame_spiel.downloads --help
```

An installed package also provides `pygame_spiel` and `pygame_spiel_download`.
From a source checkout, `python main.py` invokes the application entry point.
`pygame_spiel` and `python main.py` accept the same game options as the module
launcher. The downloader has its own help and arguments.

For Python configuration, custom controllers and manual frame handling, see
[Extending the application](extending.md).
