import base64
import copy
import sys
import time
from io import BytesIO
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

    # Use a non-interactive backend before importing pyplot so plots can be
    # generated reliably during automated runs and sandboxed evaluations.
    matplotlib.use("Agg")

    import matplotlib.patches as patches
    import matplotlib.pyplot as plt
    from matplotlib.transforms import Affine2D
except ImportError as import_error:
    matplotlib = None
    patches = None
    plt = None
    Affine2D = None
    MATPLOTLIB_IMPORT_ERROR = import_error
else:
    MATPLOTLIB_IMPORT_ERROR = None

# When this file is executed directly, Python places the task folder on
# ``sys.path`` instead of the repository root. Insert the repository root so
# imports from ``algodisco`` keep working for smoke tests.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.decorators import sandbox_run

from problems.car_racing.dataset import TRAINING_INSTANCES, TESTING_INSTANCES
from problems.car_racing.task_definition import template_program

REQUIRED_FUNCTION_NAME = "choose_action"


def _extract_required_callable(program_globals: dict[str, Any]) -> Any:
    """Return the task-required callable from an executed program namespace."""
    if REQUIRED_FUNCTION_NAME not in program_globals:
        raise KeyError(
            f"Expected function `{REQUIRED_FUNCTION_NAME}` was not defined. "
            f"Do not rename the required task entrypoint."
        )
    return program_globals[REQUIRED_FUNCTION_NAME]


class CarRacingEvaluator(Evaluator):
    """Evaluate heuristic control policies for the Gymnasium CarRacing task."""

    def __init__(
        self,
        whocall: str = "algodisco",
        max_steps: int = 1200,
        render_summary: bool = False,
        instances: dict[int, int] | None = None,
        instance_set: dict[int, int] | None = None,
        ins_to_be_solve_set: dict[int, int] | None = None,
        run_mode: str = "Training",
        **kwargs,
    ):
        super().__init__(**kwargs)
        if gym is None:
            raise ImportError(
                "CarRacingEvaluator requires `gymnasium` with the Box2D extras "
                "installed, for example `pip install gymnasium[box2d]`."
            ) from GYM_IMPORT_ERROR
        effective_render_summary = render_summary or whocall == "mles"
        if effective_render_summary and matplotlib is None:
            raise ImportError(
                "CarRacingEvaluator requires `matplotlib` for episode summary plots."
            ) from MATPLOTLIB_IMPORT_ERROR
        self.whocall = whocall
        self.env_name = "CarRacing-v3"
        self.max_steps = max_steps
        self.render_summary = effective_render_summary
        # When summary rendering is disabled, there is no need to ask Gymnasium
        # for RGB frames at all.
        self.render_mode = "rgb_array" if self.render_summary else None

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

        missing_ids = [instance_id for instance_id in normalized_ids if instance_id not in active_instances]
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
        self, action_select: callable, env_seed: int, skip_frame: int = 1
    ) -> dict[str, Any]:
        """Run one seeded episode and return metrics plus optional render artifacts."""
        env = gym.make(
            self.env_name,
            render_mode=self.render_mode,
            domain_randomize=False,
            continuous=True,
        )
        observation, _ = env.reset(seed=env_seed)
        start_time = time.time()

        # The original evaluator primes the environment with one forward action
        # before delegating control to the learned policy. This preserves that
        # behavior so scores stay comparable to the upstream task.
        action = np.array([0.0, 1.0, 0.0])
        episode_reward = 0.0
        episode_max_reward = 0.0
        trajectory: list[tuple[float, float]] = []
        car_angles: list[float] = []
        view_rectangles: list[tuple[float, float, float, float, float]] = []

        pre_observation = copy.deepcopy(observation)
        observation, reward, done, truncated, _ = env.step(action)
        episode_reward += reward
        step = 0

        while not done and not truncated and step < self.max_steps:
            # Expose the car speed because it is a natural scalar summary that a
            # handcrafted policy can use without internal simulator access.
            car_velocity = env.unwrapped.car.hull.linearVelocity
            speed = float(np.sqrt(car_velocity[0] ** 2 + car_velocity[1] ** 2))

            action = action_select(observation, speed, action, pre_observation)
            pre_observation = copy.deepcopy(observation)

            for _ in range(skip_frame):
                observation, reward, done, truncated, _ = env.step(action)
                step += 1

                if self.render_summary:
                    # These traces are only needed for the optional debug
                    # figure, so skip them entirely in the default fast path.
                    car_pos = env.unwrapped.car.hull.position
                    car_angle = float(env.unwrapped.car.hull.angle)
                    trajectory.append((car_pos.x, car_pos.y))
                    car_angles.append(car_angle)

                    corrected_angle = car_angle + np.pi / 2
                    view_center_x = car_pos.x + np.cos(corrected_angle) * 14.0
                    view_center_y = car_pos.y + np.sin(corrected_angle) * 14.0
                    view_rectangles.append(
                        (view_center_x, view_center_y, corrected_angle, 38.0, 46.0)
                    )

                episode_reward += reward
                episode_max_reward = max(episode_max_reward, episode_reward)

                if done or truncated or step >= self.max_steps:
                    break

        track_coverage = (
            env.unwrapped.tile_visited_count / len(env.unwrapped.track) * 100.0
        )
        image_base64 = None
        if self.render_summary:
            image_base64 = self._render_summary_figure(
                env=env,
                trajectory=trajectory,
                car_angles=car_angles,
                view_rectangles=view_rectangles,
            )
        env.close()
        end_time = time.time()

        infos = {
            "done": done,
            "truncated": truncated,
            "episode_reward": float(episode_reward),
            "track_coverage": float(track_coverage),
            "episode_max_reward": float(episode_max_reward),
            "evaluate_time": end_time - start_time,
        }
        if image_base64 is not None:
            infos["summary_image"] = image_base64
        return infos

    def evaluate(
        self,
        action_select: callable,
        ins_to_be_evaluated_id: Iterable[int] | None = None,
        training_mode: bool | None = None,
    ) -> dict[str, Any]:
        """Evaluate a policy across the configured training or testing split."""
        resolved_training_mode = self._resolve_training_mode(training_mode)
        active_instances, normalized_ids = self._resolve_instance_ids(
            ins_to_be_evaluated_id=ins_to_be_evaluated_id,
            training_mode=resolved_training_mode,
        )

        per_instance: dict[int, dict[str, Any]] = {}
        coverages: dict[int, float] = {}
        rewards: list[float] = []
        image_by_instance: dict[int, str] = {}
        instance_performance: dict[int, dict[str, float]] = {}

        for instance_id in normalized_ids:
            env_seed = active_instances[instance_id]
            infos = self._evaluate_single_episode(action_select, env_seed=env_seed)
            per_instance[instance_id] = infos
            coverages[instance_id] = float(infos["track_coverage"])
            rewards.append(float(infos["episode_reward"]))
            instance_performance[instance_id] = {
                "score": float(infos["episode_reward"]),
                "evaluate_time": float(infos["evaluate_time"]),
            }

            summary_image = infos.get("summary_image")
            if isinstance(summary_image, str):
                image_by_instance[instance_id] = summary_image

        mean_track_coverage = float(np.mean(list(coverages.values())))
        mean_episode_reward = float(np.mean(rewards))
        sorted_ids = sorted(instance_performance.keys())
        list_performance = [instance_performance[instance_id]["score"] for instance_id in sorted_ids]

        result: dict[str, Any] = {
            "score": mean_track_coverage,
            "metadata": {
                "mean_track_coverage": mean_track_coverage,
                "mean_episode_reward": mean_episode_reward,
                "per_instance": per_instance,
                "all_ins_performance": instance_performance,
                "list_performance": list_performance,
            },
        }

        if image_by_instance:
            worst_instance_id = min(coverages, key=coverages.get)
            result["metadata"]["image"] = image_by_instance[worst_instance_id]

        if self.whocall == "mles":
            result["Test result"] = per_instance
            result["observation"] = None

        return result

    def _render_summary_figure(
        self,
        env: Any,
        trajectory: list[tuple[float, float]],
        car_angles: list[float],
        view_rectangles: list[tuple[float, float, float, float, float]],
    ) -> str:
        """Render a compact visualization of the episode for debugging."""
        plt.figure(figsize=(9, 8))

        green_color = "#62f972"
        plt.gca().set_facecolor(green_color)

        # Draw the road polygons from the simulator so the trajectory can be
        # interpreted without opening the environment interactively.
        for polygon in env.unwrapped.road_poly:
            vertices = polygon[0]
            color = polygon[1]
            if hasattr(color, "__iter__") and not isinstance(color, tuple):
                color = tuple(color)

            fill_color = "#666666"
            if isinstance(color, tuple) and len(color) == 3:
                r = max(0, min(255, int(round(color[0]))))
                g = max(0, min(255, int(round(color[1]))))
                b = max(0, min(255, int(round(color[2]))))
                fill_color = f"#{r:02X}{g:02X}{b:02X}"

            x_coords = [v[0] for v in vertices] + [vertices[0][0]]
            y_coords = [v[1] for v in vertices] + [vertices[0][1]]
            plt.fill(x_coords, y_coords, color=fill_color, alpha=1.0)

        view_color = "#8000FF"
        arrow_interval = 40
        for index, rect in enumerate(view_rectangles):
            if (
                index == 0
                or index == len(view_rectangles) - 1
                or index % arrow_interval == 0
            ):
                center_x, center_y, angle, length, width = rect
                rect_patch = patches.Rectangle(
                    (-length / 2, -width / 2),
                    length,
                    width,
                    linewidth=0,
                    edgecolor="none",
                    facecolor=view_color,
                    alpha=0.1,
                )
                transform = (
                    Affine2D().rotate(angle).translate(center_x, center_y)
                    + plt.gca().transData
                )
                rect_patch.set_transform(transform)
                plt.gca().add_patch(rect_patch)

        arrow_color = "#FF6A00"
        if trajectory:
            trajectory_array = np.array(trajectory)
            plt.plot(
                trajectory_array[:, 0],
                trajectory_array[:, 1],
                "-",
                color="#FFD700",
                linewidth=1,
                label="Trajectory",
            )

            for index in range(len(trajectory_array)):
                if (
                    index == 0
                    or index == len(trajectory_array) - 1
                    or index % arrow_interval == 0
                ):
                    x, y = trajectory_array[index, 0], trajectory_array[index, 1]
                    angle = car_angles[index] + np.pi / 2
                    dx = np.cos(angle) * 3
                    dy = np.sin(angle) * 5
                    plt.arrow(
                        x - dx * 0.3,
                        y - dy * 0.3,
                        dx,
                        dy,
                        head_width=3,
                        head_length=4,
                        fc=arrow_color,
                        ec=arrow_color,
                    )

        grass_patch = patches.Patch(color=green_color, label="Off-track Area")
        track_patch = patches.Patch(color="#666666", label="Track")
        border_patch = patches.Patch(color="red", label="Curb Area")
        view_patch = patches.Patch(color=view_color, alpha=0.1, label="Visual Field")
        handles, _ = plt.gca().get_legend_handles_labels()
        custom_handles = [grass_patch, track_patch, border_patch, view_patch]
        unique_handles: list[Any] = []
        seen_labels: set[str] = set()
        for handle in custom_handles + handles:
            label = handle.get_label()
            if label not in seen_labels:
                seen_labels.add(label)
                unique_handles.append(handle)

        track_coverage = (
            env.unwrapped.tile_visited_count / len(env.unwrapped.track) * 100.0
        )
        plt.title(
            "Track with Car Trajectory and Dynamic View Areas\n"
            f"Track Completion Rate: {track_coverage:.1f}%"
        )
        plt.axis("equal")
        plt.legend(handles=unique_handles)

        buffer = BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close()
        return image_base64

    @sandbox_run(timeout=180, redirect_to_devnull=True)
    def evaluate_program(
        self,
        program_str: str,
        ins_to_be_evaluated_id: Iterable[int] | None = None,
        training_mode: bool | None = None,
    ):
        """Execute a candidate program and score it on the chosen split."""
        program_globals: dict[str, Any] = {}
        exec(program_str, program_globals)
        action_select = _extract_required_callable(program_globals)
        return self.evaluate(
            action_select,
            ins_to_be_evaluated_id=ins_to_be_evaluated_id,
            training_mode=training_mode,
        )


def main() -> None:
    """Run a smoke test with the bundled car racing template."""
    try:
        evaluator = CarRacingEvaluator(instances={0: next(iter(TRAINING_INSTANCES.values()))})
    except ImportError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    print("Car Racing Template Evaluation")
    print(f"instances: {len(evaluator.instance_set)}")
    print(f"score: {result['score']}")
    metadata = result.get("metadata", {})
    print(f"mean_track_coverage: {metadata.get('mean_track_coverage')}")
    print(f"mean_episode_reward: {metadata.get('mean_episode_reward')}")
    print(f"execution_time: {metadata.get('execution_time')}")
    print(f"error_msg: {metadata.get('error_msg')}")


if __name__ == "__main__":
    main()
