# 评估器 (Evaluator)

## 概述

评估器负责执行并评估生成的算法程序。algodisco 使用抽象基类 `Evaluator` 来定义评估接口。

## 核心类

### Evaluator 基类

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class Evaluator(ABC, Generic[T]):
    @abstractmethod
    def evaluate_program(self, program_str: str) -> EvalResult:
        """评估程序并返回结果"""
        pass
```

### EvalResult 类型

```python
class EvalResult(TypedDict):
    score: float
    execution_time: Optional[float]
    error_msg: Optional[str]
```

## 自定义评估器

### 基本结构

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class MyEvaluator(Evaluator):
    def __init__(self, param1: str = "default"):
        self.param1 = param1

    def evaluate_program(self, program_str: str) -> EvalResult:
        try:
            # 执行程序
            local_ns = {}
            exec(program_str, {}, local_ns)

            # 检查函数存在
            if "solve" not in local_ns:
                return {"score": 0, "error_msg": "solve function not found"}

            solve_fn = local_ns["solve"]

            # 运行测试
            test_cases = [
                {"input": [1, 2, 3], "expected": 3},
                {"input": [], "expected": 0},
            ]

            correct = 0
            for tc in test_cases:
                result = solve_fn(tc["input"])
                if result == tc["expected"]:
                    correct += 1

            score = correct / len(test_cases)
            return {"score": score}

        except Exception as e:
            return {"score": 0, "error_msg": str(e)}
```

### 配置方式

```yaml
evaluator:
  class_path: "my_evaluator.MyEvaluator"
  kwargs:
    param1: "value"
```

## 评估器实现示例

### 简单评估器

```python
from algodisco.base.evaluator import Evaluator, EvalResult
import time


class SimpleEvaluator(Evaluator):
    def __init__(self, test_cases: list):
        self.test_cases = test_cases

    def evaluate_program(self, program_str: str) -> EvalResult:
        start_time = time.time()
        try:
            # 编译检查
            compile(program_str, "<string>", "exec")

            # 执行并测试
            local_ns = {}
            exec(program_str, {}, local_ns)

            if "solve" not in local_ns:
                return {
                    "score": 0,
                    "error_msg": "solve function not found",
                    "execution_time": time.time() - start_time
                }

            # 运行测试
            correct = 0
            for tc in self.test_cases:
                result = local_ns["solve"](tc["input"])
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

### 使用沙箱的评估器

```python
from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.sandbox.sandbox_executor import SandboxedExecutor


class SandboxedEvaluator(Evaluator):
    def __init__(self, test_cases: list, timeout: float = 5.0):
        self.test_cases = test_cases
        self.timeout = timeout
        self.executor = SandboxedExecutor()

    def evaluate_program(self, program_str: str) -> EvalResult:
        try:
            result = self.executor.execute(
                program_str,
                "solve",
                self.test_cases,
                timeout=self.timeout
            )
            return result
        except Exception as e:
            return {"score": 0, "error_msg": str(e)}

    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.close()
```

## 最佳实践

1. **总是返回 score**: 即使程序出错，也要返回带有 score 的结果
2. **设置超时**: 使用沙箱执行防止无限循环
3. **清理状态**: 确保每次评估都是独立的
4. **详细错误信息**: 在 error_msg 中提供有用的调试信息

## API 参考

### Evaluator 类

```python
class Evaluator(ABC, Generic[T]):
    @abstractmethod
    def evaluate_program(self, program_str: str) -> T:
        """评估程序

        Args:
            program_str: 程序源代码

        Returns:
            包含至少 'score' 键的字典
        """
        pass
```

## 相关文档

- [沙箱执行](sandbox.md)
- [自定义评估器](../developer-guide/custom-evaluator.md)
