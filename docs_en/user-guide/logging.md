# Logging

AlgoDisco includes local and experiment-tracking loggers. All built-in loggers are designed to persist search artifacts while optionally forwarding summary metrics to external platforms.

## Base Interface

All loggers implement `algodisco.base.logger.AlgoSearchLoggerBase`.

At minimum, a logger should support:

- `log_dict(log_item, item_name)`: record one structured item
- `finish()`: flush outstanding data before process exit
- `set_log_item_flush_frequency(...)`: optionally control flush cadence per item type

## Built-in Loggers

### BasePickleLogger

`BasePickleLogger` writes items to the local filesystem in pickle batches.

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

`BaseWandbLogger` extends the pickle logger and also reports summary metrics to Weights & Biases.

```yaml
logger:
  class_path: "algodisco.providers.logger.wandb_logger.BaseWandbLogger"
  kwargs:
    logdir: "logs/my_experiment"
    project: "algodisco"
    experiment_name: "funsearch-run-1"
```

### BaseSwanLabLogger

`BaseSwanLabLogger` extends the pickle logger and also reports summary metrics to SwanLab.

```yaml
logger:
  class_path: "algodisco.providers.logger.swanlab_logger.BaseSwanLabLogger"
  kwargs:
    logdir: "logs/my_experiment"
    project: "algodisco"
    experiment_name: "funsearch-run-1"
```

## Log Output Layout

The pickle logger does not write a single `algo.pkl` file. Instead, it creates one directory per item type and stores batches as numbered pickle files:

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

This structure allows the logger to flush incrementally during long runs.

## Typical Logged Items

The exact payload depends on the search method, but `algo` items commonly include fields such as:

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

Database or archive snapshots are typically logged under a separate item name such as `database`.

## Reading Logged Results

Because data is stored in batches, load every pickle file in a log subdirectory:

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

## Recommended Practices

- Use a dedicated `logdir` per run.
- Prefer `BasePickleLogger` for local debugging and deterministic artifact inspection.
- Use `BaseWandbLogger` or `BaseSwanLabLogger` only when online experiment tracking is actually needed.
- Keep credentials such as `WANDB_API_KEY` outside committed config files.

## Related Pages

- [Configuration Guide](../getting-started/configuration.md)
- [Sandbox](sandbox.md)
