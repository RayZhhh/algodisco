# Tips and Tricks

This guide covers common pitfalls and best practices for using algorithmic.

## Debugging Generated Code

### Check the Logs

Logs are saved to the configured logger directory:

```python
# In your config
logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

Check the output for:
- Generated code
- Error messages
- Execution results

### Enable Debug Mode

```yaml
method:
  debug_mode: true
  debug_mode_crash: true
```

This saves more details and crashes on errors for easier debugging.

## Handling Errors

### Common Error: Function Not Found

```
error_msg: "solve function not found"
```

**Solution**: Make sure your template has the exact function name the evaluator expects.

### Common Error: Timeout

```
error_msg: "Execution timeout"
```

**Solution**: Increase timeout in your evaluator:

```python
@sandbox_run(timeout=60)  # Increase from 30 to 60
def evaluate_program(self, program_str: str) -> EvalResult:
    ...
```

### Common Error: Import Error

```
ModuleNotFoundError: No module named 'numpy'
```

**Solution**: The sandbox has limited packages. Either:
1. Use only standard library in generated code
2. Add required packages to the sandbox

## Score Normalization

### Problem: Scores Vary Widely

If your scores are very large or negative, consider normalizing:

```python
def evaluate_program(self, program_str: str) -> EvalResult:
    raw_score = compute_score()

    # Normalize to 0-1 range
    normalized = (raw_score - min_possible) / (max_possible - min_possible)

    return {"score": normalized}
```

### Problem: Minimization vs Maximization

Remember: **higher is always better**

```python
# Bad: Returning positive for minimization
score = mean_bins_used  # Higher = more bins = worse

# Good: Returning negative for minimization
score = -mean Higher = fewer bins_bins_used  # = better
```

## Improving Performance

### Increase Parallelism

```python
config = FunSearchConfig(
    num_samplers=8,     # More parallel sampling
    num_evaluators=8,   # More parallel evaluation
)
```

### Tune Island Parameters

```python
config = FunSearchConfig(
    db_num_islands=20,           # More islands = more diversity
    db_max_island_capacity=50,   # Smaller islands = more specialization
)
```

### Use Better Models

```python
llm = OpenAIAPI(
    model="gpt-4o",  # Better quality but slower/expensive
)
```

## Common Patterns

### Pattern 1: Loading Test Data

```python
class MyEvaluator(Evaluator):
    def __init__(self, data_path=None):
        super().__init__()
        if data_path:
            self.data = self._load_data(data_path)
        else:
            self.data = self._generate_data()

    def _load_data(self, path):
        with open(path, 'rb') as f:
            return pickle.load(f)
```

### Pattern 2: Multiple Metrics

```python
def evaluate_program(self, program_str: str) -> EvalResult:
    # Compute multiple metrics
    accuracy = compute_accuracy()
    speed = compute_speed()

    # Weighted combination
    score = 0.7 * accuracy + 0.3 * (1.0 / (1.0 + speed))

    return {
        "score": score,
        "accuracy": accuracy,
        "speed": speed,
    }
```

### Pattern 3: Retry Logic

```python
def evaluate_program(self, program_str: str) -> EvalResult:
    for attempt in range(3):
        try:
            return self._evaluate_once(program_str)
        except Exception as e:
            if attempt == 2:
                return {"score": 0, "error_msg": str(e)}
            continue
```

## Best Practices

1. **Start simple**: Begin with a small `max_samples` to test quickly
2. **Use good templates**: Clear docstrings and type hints help the LLM
3. **Handle edge cases**: Include empty inputs, single elements, etc. in tests
4. **Log everything**: Use the logger to track experiments
5. **Iterate**: Start with simple baselines, then improve

## Troubleshooting Checklist

- [ ] API key set correctly?
- [ ] Template function name matches evaluator expectation?
- [ ] Test data loaded correctly?
- [ ] Score interpretation correct (higher = better)?
- [ ] Timeout sufficient for evaluation?
- [ ] Imports in template for required libraries?

## Getting Help

- Check existing examples in `examples/`
- Review search method documentation in `docs_en/user-guide/`
- Open an issue on GitHub
