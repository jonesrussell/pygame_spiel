"""Validated game construction. No renderer or backend imports at module import."""

from importlib import import_module

from pygame_spiel.config import GameConfig, SessionConfig, validate_session


class GameFactory:
    @classmethod
    def create(cls, config: SessionConfig, registered_bots=None):
        registry = validate_session(config, registered_bots)
        module = import_module(f"pygame_spiel.games.{config.game.name}")
        game_class = module.TicTacToe if config.game.name == "tic_tac_toe" else module.Breakthrough
        return game_class(config, registry)

    @classmethod
    def get_game(cls, name, current_player=0):
        """Construct with default session settings; OpenSpiel determines turn order."""
        if type(current_player) is not int or current_player != 0:
            raise ValueError("current_player must be 0; OpenSpiel owns the turn order")
        return cls.create(SessionConfig(game=GameConfig(name)))
