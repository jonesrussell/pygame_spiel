import typing as t

from pygame_spiel.games import base


class TicTacToe(base.Game):
    def __init__(self, config, registered_bots=None):
        if config.game.name != "tic_tac_toe":
            raise ValueError("TicTacToe requires a tic_tac_toe GameConfig")
        super().__init__(config, registered_bots)

        # TicTacToe vertical/horizontal lines
        self._line_h1_x_start, self._line_h1_y_start = 0, 200
        self._line_h1_x_end, self._line_h1_y_end = 600, 200
        self._line_h2_x_start, self._line_h2_y_start = 0, 400
        self._line_h2_x_end, self._line_h2_y_end = 600, 400
        self._line_v1_x_start, self._line_v1_y_start = 200, 0
        self._line_v1_x_end, self._line_v1_y_end = 200, 600
        self._line_v2_x_start, self._line_v2_y_start = 400, 0
        self._line_v2_x_end, self._line_v2_y_end = 400, 600

        self._quadrant_pos_map_x = [
            (20, 20),
            (220, 20),
            (420, 20),
            (20, 220),
            (220, 220),
            (420, 220),
            (20, 420),
            (220, 420),
            (420, 420),
        ]
        self._quadrant_pos_map_circle = [
            (100, 100),
            (300, 100),
            (500, 100),
            (100, 300),
            (300, 300),
            (500, 300),
            (100, 500),
            (300, 500),
            (500, 500),
        ]

        self._list_x_pos, self._list_o_pos = [], []

    def _get_quadrant(self, x: int, y: int) -> t.Optional[int]:
        """
        Returns the quadrant index given the x,y coordinates in the board.
        The quadrant indices are numbered 0 to 8 starting from top-left to
        bottom-right:
        0 1 2
        3 4 5
        6 7 8

        Examples:
            _get_quadrant(1, 1) -> 0
            _get_quadrant(220, 420) -> 7

        Parameters:
            x (int): x coordinate
            y (int): y coordinate

        Returns:
            index (int or None): quadrant index, or None outside the board
        """
        if not (0 <= x < 600 and 0 <= y < 600):
            return None
        return (y // 200) * 3 + x // 200

    def _load_assets(self):
        self._text_font = self._pygame.font.SysFont("Arial", 30)
        self._x_image = self._load_image("tic_tac_toe/x_image.png")

    def _draw_text(self, text: str, text_col: t.Tuple[int, int, int], x: int, y: int):
        """
        Draws a text on the board. Used to write whether the player has won or
        lost the game

        Parameters:
            text (str): text to visualize
            text_col (tuple): text's color in the format (red, green, blue)
            x (int): x coordinate
            y (int): y coordinate
        """
        img = self._text_font.render(text, True, text_col)
        self._screen.blit(img, (x, y))

    def play(self, mouse_pos, mouse_pressed):
        pygame = self._pygame
        if not self._state.is_terminal():
            player = self._current_player
            action = None
            if self._is_human():
                if mouse_pressed[0]:
                    selected = self._get_quadrant(*mouse_pos)
                    if selected in self._state.legal_actions():
                        action = selected
            else:
                action = self._bots[player].step(self._state)
            if action is not None:
                self._apply_action(action)
                if player == 0:
                    self._list_x_pos.append(self._quadrant_pos_map_x[action])
                else:
                    self._list_o_pos.append(self._quadrant_pos_map_circle[action])

        # Visualization
        self._screen.fill("white")

        pygame.draw.line(
            self._screen,
            "black",
            (self._line_h1_x_start, self._line_h1_y_start),
            (self._line_h1_x_end, self._line_h1_y_end),
            2,
        )
        pygame.draw.line(
            self._screen,
            "black",
            (self._line_h2_x_start, self._line_h2_y_start),
            (self._line_h2_x_end, self._line_h2_y_end),
            2,
        )
        pygame.draw.line(
            self._screen,
            "black",
            (self._line_v1_x_start, self._line_v1_y_start),
            (self._line_v1_x_end, self._line_v1_y_end),
            2,
        )
        pygame.draw.line(
            self._screen,
            "black",
            (self._line_v2_x_start, self._line_v2_y_start),
            (self._line_v2_x_end, self._line_v2_y_end),
            2,
        )

        for x_pos in self._list_x_pos:
            self._screen.blit(self._x_image, x_pos)
        for o_pos in self._list_o_pos:
            pygame.draw.circle(self._screen, "black", o_pos, 60, width=4)

        if self._state.is_terminal():
            rewards = self._state.rewards()
            if rewards[0] == 0 and rewards[1] == 0:
                self._draw_text(f"DRAW", (0, 0, 0), 220, 300)
            elif rewards[0] == 1:
                self._draw_text(f"Winner: player 0", (0, 0, 0), 220, 300)
            else:
                self._draw_text(f"Winner: player 1", (0, 0, 0), 220, 300)
