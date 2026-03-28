# Tips and Tricks

This guide covers common pitfalls and best practices for using AlgoDisco.

## Debugging Generated Code

### Check the Logs

Logs are written to the directory configured in your logger:

```yaml
logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

Look for:

- Generated code
- Error messages
- Scores and timing metadata

### Enable Debug Mode

```yaml
method:
  debug_mode: true
  debug_mode_crash: true
```

This keeps more information and stops early when something breaks.

## Common Failure Modes

### Function Not Found

```text
error_msg: "solve function not found"
```

Your template function name must match what the evaluator expects.

### Timeout

```text
error_msg: "Execution timeout"
```

Increase the sandbox timeout in your evaluator:

```python
@sandbox_run(timeout=60)
def evaluate_program(self, program_str: str) -> EvalResult:
    ...
```

### Import Error

```text
ModuleNotFoundError: No module named 'numpy'
```

Either keep generated code within the packages available to the sandbox or update your execution environment accordingly.

## Score Design

AlgoDisco always treats **higher scores as better**.

For minimization problems:

```python
score = -mean_bins_used
```

For multiple metrics:

```python
return {
    "score": 0.7 * accuracy + 0.3 * speed_score,
    "accuracy": accuracy,
    "speed_score": speed_score,
}
```

## Performance Tuning

Start small:

```python
config = FunSearchConfig(
    max_samples=20,
    num_samplers=2,
    num_evaluators=2,
)
```

Then scale up:

```python
config = FunSearchConfig(
    max_samples=500,
    num_samplers=8,
    num_evaluators=8,
    db_num_islands=20,
)
```

## Evaluator Patterns

### Load Data Once

```python
class MyEvaluator(Evaluator):
    def __init__(self, data_path: str):
        super().__init__()
        with open(data_path, "rb") as f:
            self.data = pickle.load(f)
```

### Return Helpful Metadata

```python
return {
    "score": score,
    "execution_time": elapsed,
    "error_msg": None,
}
```

### Fail Gracefully

```python
try:
    ...
except Exception as e:
    return {"score": 0, "error_msg": str(e)}
```

## Practical Checklist

- Is the API key set correctly?
- Does the template function name match the evaluator?
- Does the evaluator load its test data correctly?
- Is the score direction correct?
- Is the timeout high enough?
- Are the required imports available in the execution environment?

## Getting Help

- Check the examples in `examples/`
- Read the search-method docs in `docs_en/user-guide/`
- Open an issue if you find a docs/code mismatch
