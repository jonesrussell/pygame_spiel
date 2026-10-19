"""Optional TensorFlow DQN adapter for perfect-information board games."""

import math
from pathlib import Path

try:
    import tensorflow.compat.v1 as tf
except ImportError as exc:
    raise ImportError("DQN requires the 'pygame_spiel[tensorflow]' extra") from exc

from open_spiel.python import rl_environment
from open_spiel.python.algorithms.dqn import DQN
import pyspiel


class DQNBot(pyspiel.Bot):
    def __init__(self, game, player_id, replay_buffer_capacity=100000, batch_size=32,
                 checkpoint_dir=None, hidden_layers_sizes=(64, 64), seed=42):
        super().__init__()
        if not 0 <= player_id < game.num_players():
            raise ValueError("Invalid DQN player_id")
        if checkpoint_dir is not None and not Path(checkpoint_dir).is_dir():
            raise FileNotFoundError(f"DQN checkpoint directory not found: {checkpoint_dir}")
        self._player_id = player_id
        self._num_players = game.num_players()
        # Match rl_environment.Environment's default representation without owning
        # another environment/state. Existing checkpoint dimensions depend on it.
        self._use_information_state = game.get_type().provides_information_state_tensor
        shape = (game.information_state_tensor_shape() if self._use_information_state
                 else game.observation_tensor_shape())
        self._graph = tf.Graph()
        self._sess = tf.Session(graph=self._graph)
        try:
            with self._graph.as_default():
                tf.set_random_seed(seed)
                # Preserve the player-ordered variable names used by the upstream
                # breakthrough_dqn.py checkpoints (OpenSpiel issue #1104).
                agents = [DQN(
                    session=self._sess, player_id=i,
                    state_representation_size=math.prod(shape),
                    num_actions=game.num_distinct_actions(),
                    hidden_layers_sizes=list(hidden_layers_sizes),
                    replay_buffer_capacity=replay_buffer_capacity, batch_size=batch_size,
                ) for i in range(self._num_players)]
                self._agent = agents[player_id]
                if checkpoint_dir is not None:
                    self._agent.restore(str(checkpoint_dir))
        except Exception:
            self.close()
            raise

    def restart_at(self, state):
        pass

    def close(self):
        if self._sess is not None:
            self._sess.close()
            self._sess = None

    def step(self, state):
        if state.is_terminal():
            return pyspiel.INVALID_ACTION
        if state.current_player() != self._player_id:
            raise ValueError("DQN called for a different player's turn")
        tensor = state.information_state_tensor if self._use_information_state else state.observation_tensor
        time_step = rl_environment.TimeStep(
            observations={
                "info_state": [tensor(i) for i in range(self._num_players)],
                "legal_actions": [state.legal_actions(i) for i in range(self._num_players)],
                "current_player": self._player_id,
            },
            rewards=state.rewards(), discounts=[1.0] * self._num_players,
            step_type=rl_environment.StepType.MID,
        )
        with self._graph.as_default():
            return self._agent.step(time_step, is_evaluation=True).action
