# Getting started

Complete [installation](installation.md), including an OpenSpiel choice and,
for DQN, checkpoint preparation. Then launch the installed application:

```bash
pygame_spiel
```

From a source checkout, `python main.py` invokes the same menu.

1. Choose **breakthrough** or **tic_tac_toe** in **Game**.
2. Choose **mcts**, or **dqn** for Breakthrough with a prepared checkpoint.
3. Select **Play**.

Player 0 uses the mouse; the selected opponent drives player 1. Breakthrough
against MCTS is the default. Click an empty Tic Tac Toe cell, or select a
Breakthrough pawn and then its destination. Close the window to exit.
Turn advancement and controller work run synchronously during rendering.

The optional **Module** selector executes a custom Python bot file for developer
testing. See [Python bot files](extending.md#python-bot-files); ordinary play does
not need one. This application has no non-graphical command-line play mode.
