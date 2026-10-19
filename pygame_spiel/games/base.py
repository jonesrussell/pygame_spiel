import abc
from dataclasses import replace
from pathlib import Path

from pygame_spiel.config import GAME_SIZES, SessionConfig, default_controller, validate_session
from pygame_spiel.controllers import build_controllers, close_controllers, validate_bot_classes
from pygame_spiel.resources import asset


class Game(metaclass=abc.ABCMeta):
    """Own the OpenSpiel game, state and controllers; display setup is explicit."""

    def __init__(self, config: SessionConfig, registered_bots=None):
        registry = validate_session(config, registered_bots)
        try:
            import pyspiel
        except ImportError as exc:
            raise ImportError("Install pygame_spiel[spiel] or provide a compatible local OpenSpiel 1.3 build") from exc

        validate_bot_classes(registry)
        self.config = config
        self._name = config.game.name
        self._game = pyspiel.load_game(self._name, dict(config.game.parameters))
        self._state = self._game.new_initial_state()
        self._registered_bots = registry
        self._bots = build_controllers(self._game, config, registry)
        self._pygame = None
        self._screen = None

    @property
    def _current_player(self):
        return self._state.current_player()

    @property
    def _state_string(self):
        return self._state.to_string()

    def open_display(self):
        if self._screen is not None:
            return
        import pygame

        self._pygame = pygame
        try:
            pygame.init()
            self._screen = pygame.display.set_mode(GAME_SIZES[self._name])
            pygame.display.set_caption(self.config.presentation.caption)
            self._load_assets()
        except BaseException:
            pygame.quit()
            self._pygame = None
            self._screen = None
            raise

    def _load_image(self, name):
        with asset(name).open("rb") as stream:
            return self._pygame.image.load(stream, name).convert_alpha()

    @abc.abstractmethod
    def _load_assets(self):
        """Load display-dependent resources after a display has been opened."""

    @abc.abstractmethod
    def play(self, mouse_pos, mouse_pressed):
        """Handle one frame using the application-owned display/event loop."""

    def _is_human(self):
        return self.config.controllers[self._current_player].kind == "human"

    def _apply_action(self, action):
        player = self._current_player
        if self._state.is_terminal() or action not in self._state.legal_actions():
            raise ValueError(f"Illegal action {action!r} for player {player}")
        # OpenSpiel inform_action receives the state BEFORE the action is applied.
        for other, bot in enumerate(self._bots):
            if other != player:
                bot.inform_action(self._state, player, action)
        self._state.apply_action(action)

    def register_bots(self, registered_bots: dict):
        """Validate and replace the registry used for custom-bot construction."""
        registry = validate_session(self.config, registered_bots)
        validate_bot_classes(registry)
        self._registered_bots = registry

    def set_bots(self, bot1_type, bot1_params, bot2_type, bot2_params):
        """Configure players 0 and 1 through typed controller settings.

        Parameters are dictionaries; DQN also accepts a checkpoint path.
        No model is downloaded. Use model_path in the dictionary for DQN.
        """
        controllers = []
        for player_id, kind, raw in ((0, bot1_type, bot1_params), (1, bot2_type, bot2_params)):
            if isinstance(raw, (str, Path)):
                params = {"model_path": raw}
            else:
                params = dict(raw or {})
            path = params.pop("model_path", None)
            controllers.append(default_controller(player_id, kind, params, path))
        config = replace(self.config, controllers=tuple(controllers))
        bots = build_controllers(self._game, config, self._registered_bots)
        old_bots = self._bots
        self._bots, self.config = bots, config
        close_controllers(old_bots)

    def close(self):
        bots, self._bots = self._bots, []
        try:
            close_controllers(bots)
        finally:
            if self._pygame is not None:
                self._pygame.quit()
                self._pygame = None
                self._screen = None
