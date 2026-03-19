# 自定义评估器

本指南介绍如何为 algodisco 创建自定义评估器。

## 基本结构

评估器需要继承 `Evaluator` 基类并实现 `evaluate_program` 方法：

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class MyEvaluator(Evaluator):
    def __init__(self, param1: str = "default"):
        self.param1 = param1
        self.test_cases = [...]

    def evaluate_program(self, program_str: str) -> EvalResult:
        # 实现评估逻辑
        pass
```

## 完整示例

```python
from algodisco.base.evaluator import Evaluator, EvalResult
import time
import json


class SortEvaluator(Evaluator):
    """评估排序算法"""

    def __init__(self, test_file: str = "tests.json"):
        with open(test_file) as f:
            self.test_cases = json.load(f)

    def evaluate_program(self, program_str: str) -> EvalResult:
        start_time = time.time()

        try:
            # 编译检查
            compile(program_str, "<string>", "exec")

            # 执行代码
            local_ns = {}
            exec(program_str, {}, local_ns)

            # 检查函数存在
            if "solve" not in local_ns:
                return {
                    "score": 0,
                    "error_msg": "solve function not found",
                    "execution_time": time.time() - start_time
                }

            solve_fn = local_ns["solve"]

            # 运行测试用例
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

        except SyntaxError as e:
            return {
                "score": 0,
                "error_msg": f"Syntax error: {e}",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "score": 0,
                "error_msg": str(e),
                "execution_time": time.time() - start_time
            }
```

## 使用自定义评估器

在配置文件中指定：

```yaml
evaluator:
  class_path: "my_evaluator.SortEvaluator"
  kwargs:
    test_file: "data/test_cases.json"
```

## 返回值要求

`evaluate_program` 必须返回包含 `score` 键的字典：

```python
{
    "score": float,  # 必需
    "execution_time": Optional[float],  # 可选
    "error_msg": Optional[str],  # 可选
    # 其他自定义键...
}
```

## 最佳实践

1. **错误处理**: 始终捕获异常并返回有效的 EvalResult
2. **超时控制**: 使用沙箱或设置执行超时
3. **编译检查**: 先编译再执行，提前发现语法错误
4. **清理状态**: 确保每次评估独立，不受之前影响

## 使用沙箱

```python
from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.sandbox import SandboxedExecutor


class SafeEvaluator(Evaluator):
    def __init__(self, test_cases: list):
        self.test_cases = test_cases
        self.executor = SandboxedExecutor(timeout=5.0)

    def evaluate_program(self, program_str: str) -> EvalResult:
        try:
            return self.executor.execute(
                program_str,
                "solve",
                [tc["input"] for tc in self.test_cases],
                expected=[tc["expected"] for tc in self.test_cases]
            )
        except Exception as e:
            return {"score": 0, "error_msg": str(e)}

    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.close()
```

## 相关文档

- [评估器](../user-guide/evaluator.md)
- [沙箱执行](../user-guide/sandbox.md)
