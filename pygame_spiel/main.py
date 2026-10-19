"""Application entry point: selections, explicit display and event lifetime."""

import argparse
from pathlib import Path

from pygame_spiel.config import (
    DEFAULT_SEED, MAX_SEED, GAME_SIZES, GameConfig, PresentationConfig, SessionConfig,
    default_controller, validate_session,
)
from pygame_spiel.games.factory import GameFactory
from pygame_spiel.resources import ModelPaths


def parse_args(argv=None):
    defaults = SessionConfig()
    parser = argparse.ArgumentParser(description="Play Tic Tac Toe or Breakthrough with OpenSpiel controllers")
    parser.add_argument("--game", choices=tuple(GAME_SIZES), default=defaults.game.name)
    parser.add_argument("--opponent", choices=("mcts", "random", "human", "dqn"),
                        default=defaults.controllers[1].kind)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="Base seed; built-in opponent uses seed + player_id")
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--fps", type=int, default=defaults.presentation.fps)
    parser.add_argument("--no-menu", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.seed < MAX_SEED:
        raise ValueError(f"Base seed must be between 0 and {MAX_SEED - 1} (opponent uses seed + 1)")
    paths = ModelPaths(args.cache_dir) if args.cache_dir else ModelPaths()
    model = args.model_path
    if args.opponent == "dqn" and model is None:
        model = paths.breakthrough_dqn()
    config = SessionConfig(
        game=GameConfig(args.game),
        controllers=(default_controller(0, "human"), default_controller(
            1, args.opponent, {"seed": args.seed + 1}, model,
        )),
        presentation=PresentationConfig(fps=args.fps), paths=paths,
    )
    validate_session(config)
    return config, args.no_menu


def run(config: SessionConfig, registered_bots=None):
    """Programmatic entry point; all construction succeeds before display setup."""
    game = GameFactory.create(config, registered_bots)
    try:
        game.open_display()
        pygame = game._pygame
        clock = pygame.time.Clock()
        done = False
        while not done:
            clock.tick(config.presentation.fps)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True
            if done:
                break
            game.play(pygame.mouse.get_pos(), pygame.mouse.get_pressed())
            pygame.display.flip()
    finally:
        game.close()


def pygame_spiel(argv=None):
    config, no_menu = parse_args(argv)
    if no_menu:
        run(config)
        return
    from pygame_spiel.menu import Menu

    menu = Menu(config)
    try:
        selected = menu.display()
    finally:
        import pygame

        pygame.quit()
    if selected is not None:
        run(selected, menu.get_registered_bots())


if __name__ == "__main__":
    pygame_spiel()
