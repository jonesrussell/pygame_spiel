"""Interactive selection only; construction/configuration itself is headless."""

from dataclasses import replace
import os
from pathlib import Path

from pygame_spiel.config import (
    GAME_SIZES, SessionConfig, GameConfig, available_bots, default_controller, validate_session,
)
from pygame_spiel.controllers import register_classes


class Menu:
    def __init__(self, config=None):
        self.config = config or SessionConfig()
        validate_session(self.config)
        self._selected_game = self.config.game.name
        self._selected_opponent_type = self.config.controllers[1].kind
        self._registered_bots = {}
        self._current_path = os.getcwd()
        self._bot_path = None
        self._result = None

    def display(self):
        import pygame
        import pygame_menu

        pygame.init()
        surface = pygame.display.set_mode((600, 600))
        pygame.display.set_caption(self.config.presentation.caption)
        self._mainmenu = pygame_menu.Menu(
            "Pygame spiel", 600, 600, theme=pygame_menu.themes.THEME_SOLARIZED,
        )
        self._menu_dropselect_module = self._mainmenu.add.dropselect(
            "Module (optional):", self._get_files_and_folders(self._current_path),
            onchange=self._select_module,
        )
        self._mainmenu.add.label("", label_id="path_display", max_char=-1, font_size=20)
        games = list(GAME_SIZES)
        self._mainmenu.add.dropselect(
            "Game:", [(name, name) for name in games], onchange=self._select_game,
            default=games.index(self._selected_game),
        )
        opponents = self._opponent_names()
        self._menu_dropselect_opponent = self._mainmenu.add.dropselect(
            "Opponent:", [(name, name) for name in opponents], onchange=self._select_opponent,
            default=opponents.index(self._selected_opponent_type),
        )
        self._mainmenu.add.button("Play", self._start_game)
        self._mainmenu.mainloop(surface)
        return self._result

    def _get_files_and_folders(self, path="."):
        return [(name, name) for name in [".."] + sorted(os.listdir(path))]

    def _opponent_names(self):
        return list(available_bots(self._selected_game)) + list(self._registered_bots)

    def _refresh_opponents(self):
        names = self._opponent_names()
        if self._selected_opponent_type not in names:
            self._selected_opponent_type = names[0]
        self._menu_dropselect_opponent.update_items([(name, name) for name in names])
        self._menu_dropselect_opponent.set_value(names.index(self._selected_opponent_type))

    def _select_module(self, selected_value, *args):
        selected = selected_value[0][0]
        path = Path(self._current_path) / selected
        try:
            if path.is_dir():
                self._current_path = str(path.resolve())
            elif path.suffix == ".py":
                registry = register_classes(str(path))
                # Reject reserved names before replacing the active registry.
                validate_session(self.config, registry)
                self._registered_bots = registry
                self._bot_path = str(path)
                self._refresh_opponents()
                self._mainmenu.get_widget("path_display").set_title(
                    f"Selected file: {path.name} (new Bots: {', '.join(registry)})"
                )
            self._menu_dropselect_module.update_items(self._get_files_and_folders(self._current_path))
        except (OSError, ValueError, ImportError) as exc:
            self._mainmenu.get_widget("path_display").set_title(str(exc))

    def _select_game(self, selected, *args):
        self._selected_game = selected[0][0]
        self._refresh_opponents()

    def _select_opponent(self, selected, *args):
        self._selected_opponent_type = selected[0][0]

    def _selected_config(self):
        old = self.config.controllers[1]
        kind = self._selected_opponent_type
        if kind == old.kind:
            opponent = old
        else:
            path = self.config.paths.breakthrough_dqn() if kind == "dqn" else None
            params = {"seed": old.seed} if old.seed is not None and kind in ("random", "mcts", "dqn") else {}
            opponent = default_controller(1, kind, params, model_path=path)
        return replace(self.config, game=GameConfig(self._selected_game),
                       controllers=(self.config.controllers[0], opponent))

    def _start_game(self):
        try:
            selected = self._selected_config()
            validate_session(selected, self._registered_bots)
        except (ValueError, OSError) as exc:
            self._mainmenu.get_widget("path_display").set_title(str(exc))
            return
        self._result = selected
        self._mainmenu.disable()

    def get_selected_game(self):
        return self._selected_game

    def get_selected_opponent(self):
        return self._selected_opponent_type

    def get_selected_bot_file(self):
        return self._bot_path

    def get_registered_bots(self):
        return dict(self._registered_bots)
