import base64
import copy
import io
import sys
import time
from pathlib import Path
from typing import Any, Iterable

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

from problems.moon_lander.dataset import TRAINING_INSTANCES, TESTING_INSTANCES
from problems.moon_lander.feature_pipeline import moon_lander_feature
from problems.moon_lander.task_definition import template_program

REQUIRED_FUNCTION_NAME = "choose_action"


def _extract_required_callable(program_globals: dict[str, Any]) -> Any:
    """Return the task-required callable from an executed program namespace."""
    if REQUIRED_FUNCTION_NAME not in program_globals:
        raise KeyError(
            f"Expected function `{REQUIRED_FUNCTION_NAME}` was not defined. "
            f"Do not rename the required task entrypoint."
        )
    return program_globals[REQUIRED_FUNCTION_NAME]


class MoonLanderEvaluator(Evaluator):
    """Evaluate heuristic controllers for the LunarLander environment."""

    def __init__(
        self,
        whocall: str = "algodisco",
        max_steps: int = 200,
        render_summary: bool = False,
        gravity: float = -10.0,
        enable_wind: bool = False,
        wind_power: float = 15.0,
        turbulence_power: float = 1.5,
        instances: dict[int, int] | None = None,
        instance_set: dict[int, int] | None = None,
        ins_to_be_solve_set: dict[int, int] | None = None,
        run_mode: str = "Training",
        **kwargs,
    ):
        super().__init__(**kwargs)
        if gym is None:
            raise ImportError(
                "MoonLanderEvaluator requires `gymnasium` with the Box2D extras "
                "installed, for example `pip install gymnasium[box2d]`."
            ) from GYM_IMPORT_ERROR
        effective_render_summary = render_summary or whocall == "mles"
        if effective_render_summary and matplotlib is None:
            raise ImportError(
                "MoonLanderEvaluator requires `matplotlib` for trajectory summary plots."
            ) from MATPLOTLIB_IMPORT_ERROR
        self.whocall = whocall
        self.env_name = "LunarLander-v3"
        self.max_steps = max_steps
        self.render_summary = effective_render_summary
        self.gravity = gravity
        self.enable_wind = enable_wind
        self.wind_power = wind_power
        self.turbulence_power = turbulence_power
        configured_instance_set = instance_set
        if configured_instance_set is None:
            configured_instance_set = instances
        self.instance_set = dict(
            TRAINING_INSTANCES if configured_instance_set is None else configured_instance_set
        )
        self.ins_to_be_solve_set = dict(
            TESTING_INSTANCES if ins_to_be_solve_set is None else ins_to_be_solve_set
        )
        self.instance_id_set = tuple(self.instance_set.keys())
        self.to_be_solve_instance_id_set = tuple(self.ins_to_be_solve_set.keys())
        self.instances = self.instance_set
        self.run_mode = run_mode

        # Keep feature computation lazy because these trajectories are only
        # auxiliary diagnostics and can be expensive to synthesize.
        self.instance_feature: dict[int, list[float]] = {}
        self.to_be_solve_ins_feature: dict[int, list[float]] = {}

    def _resolve_instance_ids(
        self, ins_to_be_evaluated_id: Iterable[int] | None, training_mode: bool
    ) -> tuple[dict[int, int], list[int]]:
        """Choose the active split and normalize the requested instance ids."""
        active_instances = self.instance_set if training_mode else self.ins_to_be_solve_set
        if not active_instances:
            split_name = "training" if training_mode else "testing"
            raise ValueError(f"No {split_name} instances are configured for evaluation.")

        if ins_to_be_evaluated_id is None:
            normalized_ids = list(active_instances.keys())
        else:
            normalized_ids = list(ins_to_be_evaluated_id)

        missing_ids = [
            instance_id for instance_id in normalized_ids if instance_id not in active_instances
        ]
        if missing_ids:
            split_name = "training" if training_mode else "testing"
            raise KeyError(
                f"Unknown {split_name} instance id(s): {missing_ids}. "
                f"Available ids: {list(active_instances.keys())}"
            )
        return active_instances, normalized_ids

    def _resolve_training_mode(self, training_mode: bool | None) -> bool:
        """Infer the active split from run_mode when callers omit the flag."""
        if training_mode is not None:
            return training_mode
        return self.run_mode != "Using"

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
                    infos["summary_canvas"] = canvas
                    infos["summary_image"] = self._create_base64(
                        canvas=canvas,
                        score=float(episode_reward),
                        infos=infos,
                    )
                return infos

        raise RuntimeError("Episode loop terminated unexpectedly.")

    def _create_base64(
        self, canvas: np.ndarray, score: float, infos: dict[str, Any]
    ) -> str:
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
            "Lander Trajectory\n" f"Score: {score:.3f} | Final State: {final_state}"
        )
        plt.axis("off")
        plt.savefig(img_bytes, format="png")
        plt.close()
        img_bytes.seek(0)
        return base64.b64encode(img_bytes.read()).decode("utf-8")

    def generate_instance_features(self) -> dict[int, list[float]]:
        """Compute passive trajectory features for the training split."""
        if not self.instance_feature:
            self.instance_feature = {
                instance_id: moon_lander_feature(seed)
                for instance_id, seed in self.instance_set.items()
            }
        return self.instance_feature

    def generate_testing_instance_features(self) -> dict[int, list[float]]:
        """Compute passive trajectory features for the testing split."""
        if not self.to_be_solve_ins_feature:
            self.to_be_solve_ins_feature = {
                instance_id: moon_lander_feature(seed)
                for instance_id, seed in self.ins_to_be_solve_set.items()
            }
        return self.to_be_solve_ins_feature

    def evaluate(
        self,
        action_select: callable,
        ins_to_be_evaluated_id: Iterable[int] | None = None,
        training_mode: bool | None = None,
    ) -> dict[str, Any]:
        """Evaluate a controller across the configured training or testing split."""
        resolved_training_mode = self._resolve_training_mode(training_mode)
        active_instances, normalized_ids = self._resolve_instance_ids(
            ins_to_be_evaluated_id=ins_to_be_evaluated_id,
            training_mode=resolved_training_mode,
        )

        per_instance: dict[int, dict[str, Any]] = {}
        rewards: dict[int, float] = {}
        total_fuel = 0.0
        success_count = 0
        image_canvas_by_instance: dict[int, np.ndarray] = {}
        instance_performance: dict[int, dict[str, float]] = {}

        for instance_id in normalized_ids:
            env_seed = active_instances[instance_id]
            infos = self._evaluate_single_episode(action_select, env_seed=env_seed)
            per_instance[instance_id] = infos
            rewards[instance_id] = float(infos["episode_reward"])
            total_fuel += float(infos["episode_fuel"])
            if infos["episode_reward"] >= 200:
                success_count += 1
            instance_performance[instance_id] = {
                "score": float(infos["episode_reward"]),
                "evaluate_time": float(infos["evaluate_time"]),
            }

            summary_canvas = infos.get("summary_canvas")
            if isinstance(summary_canvas, np.ndarray):
                image_canvas_by_instance[instance_id] = summary_canvas

        num_episodes = len(normalized_ids)
        mean_reward = float(np.mean(list(rewards.values())))
        mean_fuel = total_fuel / num_episodes
        success_rate = success_count / num_episodes
        nws = (
            (mean_reward / 200.0) * 0.6
            + (1.0 - min(mean_fuel / 100.0, 1.0)) * 0.2
            + success_rate * 0.2
        )

        sorted_ids = sorted(instance_performance.keys())
        list_performance = [
            instance_performance[instance_id]["score"] for instance_id in sorted_ids
        ]

        result: dict[str, Any] = {
            "score": nws,
            "metadata": {
                "nws": nws,
                "mean_reward": mean_reward,
                "mean_fuel": mean_fuel,
                "success_rate": success_rate,
                "per_instance": per_instance,
                "all_ins_performance": instance_performance,
                "list_performance": list_performance,
            },
        }

        if image_canvas_by_instance:
            worst_instance_id = min(rewards, key=rewards.get)
            worst_infos = per_instance[worst_instance_id]
            result["metadata"]["image"] = self._create_base64(
                canvas=image_canvas_by_instance[worst_instance_id],
                score=nws,
                infos=worst_infos,
            )
            result["metadata"]["observation"] = str(worst_infos.get("observations"))

        if self.whocall == "mles":
            result["Test result"] = {
                "Mean Reward": mean_reward,
                "Mean Fuel": mean_fuel,
                "Success Rate": success_rate,
                "NWS": nws,
            }

        return result

    @sandbox_run(timeout=300, redirect_to_devnull=True)
    def evaluate_program(
        self,
        program_str: str,
        ins_to_be_evaluated_id: Iterable[int] | None = None,
        training_mode: bool | None = None,
    ) -> EvalResult:
        """Execute a candidate controller and score it on the chosen split."""
        program_globals: dict[str, Any] = {}
        exec(program_str, program_globals)
        action_select = _extract_required_callable(program_globals)
        return self.evaluate(
            action_select,
            ins_to_be_evaluated_id=ins_to_be_evaluated_id,
            training_mode=training_mode,
        )


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
    print(f"instances: {len(evaluator.instance_set)}")
    print(f"score: {result['score']}")
    metadata = result.get("metadata", {})
    print(f"mean_reward: {metadata.get('mean_reward')}")
    print(f"mean_fuel: {metadata.get('mean_fuel')}")
    print(f"success_rate: {metadata.get('success_rate')}")
    print(f"execution_time: {metadata.get('execution_time')}")
    print(f"error_msg: {metadata.get('error_msg')}")


if __name__ == "__main__":
    main()
