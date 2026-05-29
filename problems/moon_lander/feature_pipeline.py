"""Helper feature extraction utilities for the moon lander task."""

import numpy as np

try:
    import gymnasium as gym
except ImportError as import_error:
    gym = None
    GYM_IMPORT_ERROR = import_error
else:
    GYM_IMPORT_ERROR = None


def moon_lander_feature(seed: int, env_max_episode_steps: int = 100) -> list[float]:
    """Generate a simple no-action trajectory feature for one seed.

    This mirrors the upstream task's idea: use the passive trajectory as a cheap
    descriptor of the instance's initial conditions.
    """
    if gym is None:
        raise ImportError(
            "moon_lander_feature requires `gymnasium` with the Box2D extras "
            "installed, for example `pip install gymnasium[box2d]`."
        ) from GYM_IMPORT_ERROR

    env = gym.make(
        "LunarLander-v3",
        render_mode="rgb_array",
        gravity=-10.0,
        enable_wind=False,
        wind_power=15.0,
        turbulence_power=1.5,
    )
    observation, _ = env.reset(seed=seed)
    action = 0
    observations = []
    flash_calculator = 0

    for _ in range(env_max_episode_steps + 1):
        observation, _, done, truncated, _ = env.step(action)
        if flash_calculator >= 5:
            observations.append(observation)
            flash_calculator = 0
        flash_calculator += 1
        if done or truncated:
            break

    env.close()
    observations_array = np.array(observations)
    if len(observations_array) == 0:
        return []

    feature_x = observations_array[:, 0]
    feature_y = observations_array[:, 1]
    return (np.concatenate((feature_x, feature_y)) * 10.0).tolist()
