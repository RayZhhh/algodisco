# OpenEvolve 示例：排序算法

本示例展示如何使用 OpenEvolve 发现多种排序算法实现。

## 问题定义

给定一个整数数组，将其按升序排列。

## 1. 准备模板程序

创建文件 `templates/sort.py`:

```python
from typing import List

def solve(arr: List[int]) -> List[int]:
    """Sort the array in ascending order.

    Args:
        arr: A list of integers

    Returns:
        The sorted array
    """
    # TODO: Implement this function
    return sorted(arr) if arr else []
```

## 2. 准备任务描述

创建文件 `tasks/sort.txt`:

```
Implement the `solve(arr: List[int]) -> List[int]` function to sort the array in ascending order.

Requirements:
1. Return a new sorted array (don't modify the input)
2. Handle empty arrays
3. Handle arrays with duplicate elements
4. Implement an efficient sorting algorithm
```

## 3. 创建评估器

创建文件 `evaluators/sort_evaluator.py`:

```python
from algodisco.base.evaluator import Evaluator, EvalResult
import time


class SortEvaluator(Evaluator):
    def __init__(self):
        self.test_cases = [
            # Basic cases
            {"input": [3, 1, 2], "expected": [1, 2, 3]},
            {"input": [5, 4, 3, 2, 1], "expected": [1, 2, 3, 4, 5]},
            {"input": [1], "expected": [1]},

            # Edge cases
            {"input": [], "expected": []},
            {"input": [2, 2, 2], "expected": [2, 2, 2]},
            {"input": [-1, 5, -3, 0, 2], "expected": [-3, -1, 0, 2, 5]},

            # Larger cases
            {"input": list(range(20, 0, -1)), "expected": list(range(1, 21))},
            {"input": [i % 10 for i in range(20)], "expected": [i % 10 for i in range(20)]},
        ]

    def evaluate_program(self, program_str: str) -> EvalResult:
        start_time = time.time()

        try:
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

创建文件 `configs/sort_openevolve.yaml`:

```yaml
method:
  template_program_path: "templates/sort.py"
  task_description_path: "tasks/sort.txt"
  language: "python"
  diff_based_evolution: false
  num_top_programs: 1
  num_diverse_programs: 1
  exploration_ratio: 0.2
  exploitation_ratio: 0.7
  elite_selection_ratio: 0.1
  num_samplers: 4
  num_evaluators: 4
  max_samples: 300
  db_num_islands: 10
  archive_size: 50
  migration_interval: 30
  migration_rate: 0.15

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: "${OPENAI_API_KEY}"

evaluator:
  class_path: "evaluators.sort_evaluator.SortEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/sort_openevolve"
```

## 5. 运行搜索

```bash
export OPENAI_API_KEY="your-api-key"
python algodisco/methods/openevolve/main_openevolve.py --config configs/sort_openevolve.yaml
```

## 6. 分析结果

```python
import pickle
from collections import defaultdict

# 加载结果
with open("logs/sort_openevolve/algo", "rb") as f:
    results = pickle.load(f)

# 按分数分组
by_score = defaultdict(list)
for r in results:
    by_score[r["score"]].append(r)

# 找到完美解
perfect = by_score.get(1.0, [])
print(f"Found {len(perfect)} perfect solutions")

# 显示不同的完美解
if perfect:
    print("\nPerfect solutions:")
    for i, sol in enumerate(perfect[:3]):
        print(f"\n--- Solution {i+1} ---")
        print(sol["program"])
```

## OpenEvolve 特点

| 参数 | 说明 | 作用 |
|------|------|------|
| `exploration_ratio` | 探索比例 | 控制探索新解决方案的比例 |
| `exploitation_ratio` | 利用比例 | 控制利用现有解决方案的比例 |
| `num_diverse_programs` | 多样解数量 | 选择多样化解决方案的数量 |
| `archive_size` | 档案库大小 | 保存多样化解决方案的数量 |

## 期望输出

OpenEvolve 会发现多种不同的排序实现：

- 冒泡排序
- 插入排序
- 选择排序
- 快速排序
- 归并排序
