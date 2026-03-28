# 日志系统

AlgoDisco 提供了本地日志器和实验跟踪日志器。内置日志器的目标很明确：既能保存搜索过程中的关键产物，也能在需要时把汇总指标同步到外部平台。

## 基础接口

所有日志器都基于 `algodisco.base.logger.AlgoSearchLoggerBase`。

一个日志器至少需要支持：

- `log_dict(log_item, item_name)`：记录一条结构化数据
- `finish()`：在进程退出前刷新未落盘内容
- `set_log_item_flush_frequency(...)`：按 item 类型控制刷盘频率

## 内置日志器

### BasePickleLogger

`BasePickleLogger` 会把日志按批次写入本地 pickle 文件。

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

### BaseWandbLogger

`BaseWandbLogger` 在保留本地 pickle 日志的同时，会把汇总指标同步到 Weights & Biases。

```yaml
logger:
  class_path: "algodisco.providers.logger.wandb_logger.BaseWandbLogger"
  kwargs:
    logdir: "logs/my_experiment"
    project: "algodisco"
    experiment_name: "funsearch-run-1"
```

### BaseSwanLabLogger

`BaseSwanLabLogger` 在保留本地 pickle 日志的同时，会把汇总指标同步到 SwanLab。

```yaml
logger:
  class_path: "algodisco.providers.logger.swanlab_logger.BaseSwanLabLogger"
  kwargs:
    logdir: "logs/my_experiment"
    project: "algodisco"
    experiment_name: "funsearch-run-1"
```

## 日志目录结构

当前的 pickle 日志器不是把所有结果塞进单个 `algo.pkl` 文件，而是按 item 类型创建目录，并按批次写成编号文件：

```text
logs/my_experiment/
├── algo/
│   ├── 1.pkl
│   ├── 2.pkl
│   └── ...
└── database/
    ├── 1.pkl
    └── ...
```

这种设计更适合长时间运行的实验，能够边跑边刷盘。

## 常见日志内容

不同搜索方法记录的字段会略有差异，但 `algo` 类日志通常会包含：

```python
{
    "program": "...",
    "score": 0.85,
    "sample_time": 1.2,
    "eval_time": 0.5,
    "execution_time": 0.3,
    "error_msg": None,
    "prompt": "...",
    "response_text": "...",
}
```

数据库或归档快照通常会作为另一类 item，例如 `database`。

## 如何读取日志

因为日志是按批次写入的，所以需要遍历子目录下的所有 pickle 文件：

```python
from pathlib import Path
import pickle

all_algos = []
for batch_path in sorted(Path("logs/my_experiment/algo").glob("*.pkl")):
    with open(batch_path, "rb") as f:
        all_algos.extend(pickle.load(f))

best = max(all_algos, key=lambda item: item.get("score", float("-inf")))
print(best["score"])
```

## 推荐实践

- 每次实验使用独立的 `logdir`。
- 本地调试和结果复盘时，优先使用 `BasePickleLogger`。
- 只有在确实需要在线实验跟踪时，再启用 `BaseWandbLogger` 或 `BaseSwanLabLogger`。
- 不要把 `WANDB_API_KEY` 等敏感信息直接写进提交到仓库的配置文件。

## 相关页面

- [配置指南](../getting-started/configuration.md)
- [Sandbox](sandbox.md)
