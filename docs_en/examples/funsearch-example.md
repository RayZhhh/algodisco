# FunSearch 示例：最大值查找

本示例展示如何使用 FunSearch 解决最大值查找问题。

## 问题定义

给定一个整数数组，找到其中的最大值。

## 1. 准备模板程序

创建文件 `templates/max_value.py`:

```python
from typing import List

def solve(arr: List[int]) -> int:
    """Find the maximum value in the array.

    Args:
        arr: A list of integers

    Returns:
        The maximum value in the array
    """
    # TODO: Implement this function
    return arr[0] if arr else 0
```

## 2. 准备任务描述

创建文件 `tasks/max_value.txt`:

```
Implement the `solve(arr: List[int]) -> int` function to find the maximum value in the given array.

Requirements:
1. Handle empty arrays by returning 0
2. Handle arrays with negative numbers
3. Return the correct maximum value for any valid input
```

## 3. 创建评估器

创建文件 `evaluators/max_value_evaluator.py`:

```python
from algodisco.base.evaluator import Evaluator, EvalResult
import time


class MaxValueEvaluator(Evaluator):
    def __init__(self):
        self.test_cases = [
            # Basic cases
            {"input": [1, 2, 3], "expected": 3},
            {"input": [3, 2, 1], "expected": 3},
            {"input": [1], "expected": 1},

            # Edge cases
            {"input": [], "expected": 0},
            {"input": [-1, -5, -2], "expected": -1},
            {"input": [0, -1, 1], "expected": 1},

            # Larger cases
            {"input": list(range(100)), "expected": 99},
            {"input": list(range(100, 0, -1)), "expected": 100},
        ]

    def evaluate_program(self, program_str: str) -> EvalResult:
        start_time = time.time()

        try:
            # Compile and execute
            code = compile(program_str, "<string>", "exec")
            local_ns = {}
            exec(code, {}, local_ns)

            if "solve" not in local_ns:
                return {
                    "score": 0,
                    "error_msg": "solve function not found",
                    "execution_time": time.time() - start_time
                }

            solve_fn = local_ns["solve"]

            # Run tests
            correct = 0
            for tc in self.test_cases:
                result = solve_fn(tc["input"])
                if result == tc["expected"]:
                    correct += 1

            score = correct / len(self.test_cases)
            return {
                "score": score,
                "execution_time": time.time() - start_time
            }

        except Exception as e:
            return {
                "score": 0,
                "error_msg": str(e),
                "execution_time": time.time() - start_time
            }
```

## 4. 创建配置文件

创建文件 `configs/max_value_funsearch.yaml`:

```yaml
method:
  template_program_path: "templates/max_value.py"
  task_description_path: "tasks/max_value.txt"
  language: "python"
  num_samplers: 4
  num_evaluators: 4
  examples_per_prompt: 2
  samples_per_prompt: 4
  max_samples: 200
  llm_max_tokens: 1024
  llm_timeout_seconds: 120
  db_num_islands: 10
  db_max_island_capacity: 20
  db_save_frequency: 50

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4-turbo-preview"
    api_key: "${OPENAI_API_KEY}"

evaluator:
  class_path: "evaluators.max_value_evaluator.MaxValueEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/max_value_funsearch"
```

## 5. 运行搜索

```bash
export OPENAI_API_KEY="your-api-key"
python algodisco/methods/funsearch/main_funsearch.py --config configs/max_value_funsearch.yaml
```

## 6. 分析结果

```python
import pickle

# 加载结果
with open("logs/max_value_funsearch/algo", "rb") as f:
    results = pickle.load(f)

# 找到最佳解
best = max(results, key=lambda x: x.get("score", 0))

print(f"Best score: {best['score']}")
print(f"Sample #{best['sample_num']}")
print(f"Best program:\n{best['program']}")
```

## 期望输出

经过若干次迭代后，你应该能看到类似输出：

```
Algo #1            | Score:   0.1250 | Sample:  1.23s | Eval:  0.01s | Exec:  0.00s
Algo #2            | Score:   0.2500 | Sample:  0.89s | Eval:  0.01s | Exec:  0.00s
...
Algo #150          | Score:   1.0000 | Sample:  0.95s | Eval:  0.01s | Exec:  0.00s
```

## 关键配置说明

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `num_samplers` | 并行采样线程数 | 4-8 |
| `num_evaluators` | 并行评估线程数 | 4-8 |
| `db_num_islands` | 岛屿数量 | 10-20 |
| `max_samples` | 最大采样数 | 200-500 |
| `examples_per_prompt` | 提示词中的示例数 | 2-3 |
