import base64
import copy
import io
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

try:
    import gymnasium as gym
except ImportError as import_error:
    gym = None
    GYM_IMPORT_ERROR = import_error
else:
    GYM_IMPORT_ERROR = None

try:
    import matplotlib

    # Use a non-interactive backend before importing pyplot so figure generation
    # is robust in automated runs.
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
except ImportError as import_error:
    matplotlib = None
    plt = None
    MATPLOTLIB_IMPORT_ERROR = import_error
else:
    MATPLOTLIB_IMPORT_ERROR = None

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.decorators import sandbox_run

try:
    from .dataset import TRAINING_INSTANCES
    from .feature_pipeline import moon_lander_feature
    from .task_definition import template_program
except ImportError:
    from dataset import TRAINING_INSTANCES
    from feature_pipeline import moon_lander_feature
    from task_definition import template_program


def _extract_callable(program_globals: dict[str, Any], func_name: str) -> Any:
    """Return the required callable from the executed candidate program."""
    if func_name not in program_globals:
        raise KeyError(f"Expected function `{func_name}` was not defined.")
    return program_globals[func_name]


class MoonLanderEvaluator(Evaluator):
    """Evaluate heuristic controllers for the LunarLander environment."""

    def __init__(
        self,
        max_steps: int = 200,
        render_summary: bool = False,
        gravity: float = -10.0,
        enable_wind: bool = False,
        wind_power: float = 15.0,
        turbulence_power: float = 1.5,
        instances: dict[int, int] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if gym is None:
            raise ImportError(
                "MoonLanderEvaluator requires `gymnasium` with the Box2D extras "
                "installed, for example `pip install gymnasium[box2d]`."
            ) from GYM_IMPORT_ERROR
        if render_summary and matplotlib is None:
            raise ImportError(
                "MoonLanderEvaluator requires `matplotlib` for trajectory summary plots."
            ) from MATPLOTLIB_IMPORT_ERROR
        self.env_name = "LunarLander-v3"
        self.max_steps = max_steps
        self.render_summary = render_summary
        self.gravity = gravity
        self.enable_wind = enable_wind
        self.wind_power = wind_power
        self.turbulence_power = turbulence_power
        self.instances = dict(TRAINING_INSTANCES if instances is None else instances)

        # Keep feature computation lazy because the bundled training split is
        # fairly large and these features are only auxiliary diagnostics.
        self.instance_features: dict[int, list[float]] = {}

    def _evaluate_single_episode(
        self, action_select: callable, env_seed: int
    ) -> dict[str, Any]:
        """Run one seeded landing episode and return metrics plus optional render artifacts."""
        start_time = time.time()
        env = gym.make(
            self.env_name,
            render_mode="rgb_array" if self.render_summary else None,
            gravity=self.gravity,
            enable_wind=self.enable_wind,
            wind_power=self.wind_power,
            turbulence_power=self.turbulence_power,
        )
        observation, _ = env.reset(seed=env_seed)
        action = 0
        episode_reward = 0.0
        episode_fuel = 0

        # Only allocate a canvas in the optional rendered mode. The default
        # scoring path does not need any frame synthesis.
        canvas = None
        if self.render_summary:
            canvas = np.zeros((400, 600, 3), dtype=np.float32)
        observations: list[str] = []

        pre_observation = copy.deepcopy(observation)
        observation, _, _, _, _ = env.step(action)
        flash_calculator = 0

        for step_index in range(self.max_steps + 1):
            action = action_select(observation, action, pre_observation)
            pre_observation = copy.deepcopy(observation)
            observation, reward, done, truncated, _ = env.step(action)
            episode_reward += reward

            if action in [1, 2, 3]:
                episode_fuel += 1

            if flash_calculator >= 10:
                if self.render_summary:
                    frame = env.render()
                    mask = np.any(frame != [0, 0, 0], axis=-1)
                    alpha = min(step_index / self.max_steps, 1.0)
                    canvas[mask] = canvas[mask] * (1 - alpha) + frame[mask] * alpha
                observations.append(
                    "[" + ", ".join(f"{value:.3f}" for value in observation) + "]"
                )
                flash_calculator = 0

            flash_calculator += 1

            if done or truncated or step_index == self.max_steps:
                if self.render_summary:
                    frame = env.render()
                    mask = np.any(frame != [0, 0, 0], axis=-1)
                    alpha = min(step_index / self.max_steps, 1.0)
                    canvas[mask] = canvas[mask] * (1 - alpha) + frame[mask] * alpha
                observations.append(
                    "[" + ", ".join(f"{value:.3f}" for value in observation) + "]"
                )
                env.close()
                end_time = time.time()
                infos = {
                    "done": done,
                    "truncated": truncated,
                    "episode_fuel": episode_fuel,
                    "episode_reward": float(episode_reward),
                    "observations": observations,
                    "evaluate_time": end_time - start_time,
                }
                if self.render_summary and canvas is not None:
                    infos["summary_image"] = self._create_base64(
                        canvas=canvas,
                        score=float(episode_reward),
                        infos=infos,
                    )
                return infos

        raise RuntimeError("Episode loop terminated unexpectedly.")

    def _create_base64(self, canvas: np.ndarray, score: float, infos: dict[str, Any]) -> str:
        """Convert a canvas into a base64-encoded PNG for debugging."""
        img_bytes = io.BytesIO()
        plt.imshow(canvas.astype(np.uint8))

        if infos["done"]:
            final_state = "Landed safely"
        elif infos["truncated"]:
            final_state = "Episode truncated"
        else:
            final_state = "Landing failed"

        plt.title(
            "Lander Trajectory\n"
            f"Score: {score:.3f} | Final State: {final_state}"
        )
        plt.axis("off")
        plt.savefig(img_bytes, format="png")
        plt.close()
        img_bytes.seek(0)
        return base64.b64encode(img_bytes.read()).decode("utf-8")

    def generate_instance_features(self) -> dict[int, list[float]]:
        """Compute passive trajectory features for the currently configured seeds."""
        if self.instance_features:
            return self.instance_features

        self.instance_features = {
            instance_id: moon_lander_feature(seed)
            for instance_id, seed in self.instances.items()
        }
        return self.instance_features

    @sandbox_run(timeout=300, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str) -> EvalResult:
        """Execute a candidate controller and score it across bundled seeds."""
        program_globals: dict[str, Any] = {}
        exec(program_str, program_globals)
        action_select = _extract_callable(program_globals, "choose_action")

        per_instance: dict[int, dict[str, Any]] = {}
        rewards: list[float] = []
        total_fuel = 0.0
        success_count = 0

        for instance_id, seed in self.instances.items():
            infos = self._evaluate_single_episode(action_select, env_seed=seed)
            rewards.append(infos["episode_reward"])
            total_fuel += infos["episode_fuel"]
            if infos["episode_reward"] >= 200:
                success_count += 1
            per_instance[instance_id] = infos

        mean_reward = float(np.mean(rewards))
        mean_fuel = total_fuel / len(self.instances)
        success_rate = success_count / len(self.instances)

        # Preserve the original task's composite objective:
        # reward is primary, lower fuel use helps, and success rate matters.
        normalized_weighted_score = (
            (mean_reward / 200.0) * 0.6
            + (1.0 - min(mean_fuel / 100.0, 1.0)) * 0.2
            + success_rate * 0.2
        )

        return {
            "score": float(normalized_weighted_score),
            "mean_reward": mean_reward,
            "mean_fuel": float(mean_fuel),
            "success_rate": float(success_rate),
            "per_instance": per_instance,
        }


def main() -> None:
    """Run a smoke test with the bundled moon lander template."""
    smoke_test_instances = {
        index: seed for index, seed in enumerate(list(TRAINING_INSTANCES.values())[:3])
    }
    try:
        evaluator = MoonLanderEvaluator(instances=smoke_test_instances)
    except ImportError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    print("Moon Lander Template Evaluation")
    print(f"instances: {len(evaluator.instances)}")
    print(f"score: {result['score']}")
    print(f"mean_reward: {result.get('mean_reward')}")
    print(f"mean_fuel: {result.get('mean_fuel')}")
    print(f"success_rate: {result.get('success_rate')}")
    print(f"execution_time: {result.get('execution_time')}")
    print(f"error_msg: {result.get('error_msg')}")


if __name__ == "__main__":
    main()
