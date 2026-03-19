# 日志系统

## 概述

algodisco 提供了灵活的日志系统，用于记录搜索过程中的各种信息。

## 核心类

### AlgoSearchLoggerBase

```python
class AlgoSearchLoggerBase(ABC):
    @abstractmethod
    async def log_dict(self, log_item: Dict, item_name: str): ...

    async def finish(self): ...

    def set_log_item_flush_frequency(self, *args, **kwargs): ...

    def log_dict_sync(self, log_item: Dict, item_name: str): ...

    def finish_sync(self): ...
```

## 日志器实现

### PickleLogger

将日志保存为 pickle 文件。

```yaml
logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

```python
from algodisco.providers.logger.pickle_logger import BasePickleLogger

logger = BasePickleLogger(logdir="logs/my_experiment")
```

### WandbLogger

集成 Weights & Biases。

```yaml
logger:
  class_path: "algodisco.providers.logger.wandb_logger.WandbLogger"
  kwargs:
    project: "my-project"
    entity: "my-team"
    name: "funsearch-run-1"
```

```python
from algodisco.providers.logger.wandb_logger import WandbLogger

logger = WandbLogger(
    project="my-project",
    entity="my-team",
    name="funsearch-run-1"
)
```

### SwanLabLogger

集成 SwanLab。

```yaml
logger:
  class_path: "algodisco.providers.logger.swanlab_logger.SwanLabLogger"
  kwargs:
    project: "my-project"
    workspace: "my-workspace"
```

## 日志内容

### algo 日志

每次采样记录一条，包含：

```python
{
    "algo_id": "uuid",
    "program": "code string",
    "language": "python",
    "score": 0.85,
    "sample_num": 100,
    "island_id": 0,
    "sample_time": 1.2,
    "eval_time": 0.5,
    "execution_time": 0.3,
    "error_msg": None,
    "prompt": "...",
    "response_text": "..."
}
```

### database 日志

定期保存数据库快照：

```python
{
    "sample_num": 100,
    "islands": [
        {"programs": [...], "best_score": 0.9},
        ...
    ]
}
```

## 使用日志

### 加载日志

```python
import pickle

# 加载 algo 日志
with open("logs/my_experiment/algo.pkl", "rb") as f:
    algos = pickle.load(f)

# 加载 database 日志
with open("logs/my_experiment/database.pkl", "rb") as f:
    databases = pickle.load(f)

# 找到最佳解
best = max(algos, key=lambda x: x.get("score", 0))
print(f"Best score: {best['score']}")
print(f"Best program:\n{best['program']}")
```

### 分析日志

```python
import pickle
import numpy as np

# 加载数据
with open("logs/my_experiment/algo", "rb") as f:
    algos = pickle.load(f)

# 绘制分数曲线
scores = [a['score'] for a in algos]
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 5))
plt.plot(scores)
plt.xlabel('Sample')
plt.ylabel('Score')
plt.title('Search Progress')
plt.savefig('progress.png')
plt.show()
```

## API 参考

### BasePickleLogger

```python
class BasePickleLogger(AlgoSearchLoggerBase):
    def __init__(self, logdir: str):
        """初始化日志器

        Args:
            logdir: 日志目录路径
        """
```

### WandbLogger

```python
class WandbLogger(AlgoSearchLoggerBase):
    def __init__(
        self,
        project: str,
        entity: str = None,
        name: str = None,
        config: dict = None,
    ):
```

### SwanLabLogger

```python
class SwanLabLogger(AlgoSearchLoggerBase):
    def __init__(
        self,
        project: str,
        workspace: str = None,
        name: str = None,
    ):
```

## 相关文档

- [配置指南](../getting-started/configuration.md)
