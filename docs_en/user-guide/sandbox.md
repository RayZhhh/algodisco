# 沙箱执行

## 概述

algodisco 提供沙箱执行功能，用于安全地运行不受信任的代码。

## 沙箱实现

### SimpleSandboxExecutor

简单沙箱，使用 Python 内置的 `exec()` 执行。

```python
from algodisco.toolkit.sandbox.sandbox_executor_simple import SimpleSandboxExecutor

executor = SimpleSandboxExecutor()

result = executor.execute("print('hello')")
print(result)  # {'output': 'hello', 'error': None}
```

### RaySandboxExecutor

基于 Ray 的沙箱，提供更好的隔离。

```python
from algodisco.toolkit.sandbox.sandbox_executor_ray import RaySandboxExecutor

executor = RaySandboxExecutor()

result = executor.execute(
    "def solve(arr): return max(arr)",
    "solve",
    [[1, 2, 3]],
    timeout=5.0
)
```

## 执行函数

### execute()

```python
def execute(
    self,
    program_str: str,
    function_name: str,
    test_inputs: list,
    timeout: float = 5.0,
) -> dict:
    """执行程序

    Args:
        program_str: 程序源代码
        function_name: 要执行的函数名
        test_inputs: 测试输入列表
        timeout: 超时时间（秒）

    Returns:
        {
            "score": float,
            "output": str,
            "error_msg": str,
            "execution_time": float
        }
    """
```

## 配置

### 使用沙箱评估器

```yaml
evaluator:
  class_path: "algodisco.toolkit.sandbox.SandboxedEvaluator"
  kwargs:
    test_cases:
      - input: [1, 2, 3]
        expected: 3
    timeout: 5.0
```

## 装饰器

algodisco 提供装饰器用于限制执行资源：

```python
from algodisco.toolkit.sandbox.decorators import resource_limit, time_limit


@time_limit(5.0)  # 5秒超时
@resource_limit(memory_mb=512)  # 512MB 内存限制
def run_code(code: str):
    exec(code)
```

## 安全考虑

1. **超时设置**: 始终设置合理的超时时间
2. **资源限制**: 使用资源限制防止恶意代码
3. **网络隔离**: 沙箱不应有网络访问
4. **文件系统隔离**: 限制文件系统访问

## API 参考

### SandboxExecutor 基类

```python
class SandboxExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        program_str: str,
        function_name: str,
        test_inputs: list,
        timeout: float = 5.0,
    ) -> dict:
        pass

    def close(self):
        pass
```

### SimpleSandboxExecutor

```python
class SimpleSandboxExecutor(SandboxExecutor):
    def __init__(self):
        pass
```

### RaySandboxExecutor

```python
class RaySandboxExecutor(SandboxExecutor):
    def __init__(
        self,
        num_workers: int = 4,
        max_runtime: int = 30,
    ):
```

## 相关文档

- [评估器](evaluator.md)
- [自定义评估器](../developer-guide/custom-evaluator.md)
