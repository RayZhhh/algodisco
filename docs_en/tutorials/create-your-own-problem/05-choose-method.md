# Choosing a Search Method

algodisco provides multiple search methods. Here's how to choose the right one for your problem.

## Overview of Methods

| Method | Best For | Complexity |
|--------|----------|------------|
| FunSearch | General purpose, exploration | Medium |
| OpenEvolve | When you have good seed solutions | Medium |
| EoH | Evolution of heuristics | Medium |
| (1+1)-EPS | Simple evolutionary strategy | Low |
| RandSample | Baseline, quick testing | Low |

## Method Details

### FunSearch

**Best for**: Most use cases, especially when exploring new problem spaces

**How it works**:
- Uses MAP-Elites with islands
- Maintains diverse population across islands
- Good balance of exploration and exploitation

**When to use**:
- Default choice for new problems
- When you need diverse solutions
- When the problem space is not well understood

**Key parameters**:
- `num_samplers`: Parallel sampling threads
- `num_evaluators`: Parallel evaluation threads
- `db_num_islands`: Number of islands (more = more diversity)
- `max_samples`: Total samples to generate

```python
config = FunSearchConfig(
    template_program=template,
    task_description=task_desc,
    num_samplers=4,
    num_evaluators=4,
    db_num_islands=10,
    max_samples=1000,
)
```

### OpenEvolve

**Best for**: When you have good seed solutions to start from

**How it works**:
- Evolution based on existing programs
- Uses diff-based evolution (SEARCH/REPLACE)
- Good for refining existing heuristics

**When to use**:
- You have a baseline algorithm to improve
- Problem has known good solutions
- Incremental improvement is desired

**Key parameters**:
- `num_top_programs`: Best programs to include in prompt
- `diff_based_evolution`: Use SEARCH/REPLACE mode

### EoH (Evolution of Heuristics)

**Best for**: Evolving heuristic functions

**How it works**:
- Population-based evolutionary algorithm
- Multiple evolution operators
- Good for parameter tuning

**When to use**:
- Optimizing heuristic parameters
- Combining multiple heuristics
- Known heuristic structure to optimize

**Key parameters**:
- `pop_size`: Population size
- `selection_num`: Number selected each generation

### (1+1)-EPS

**Best for**: Simple, fast experimentation

**How it works**:
- (1+1) evolutionary strategy
- One parent, one offspring per iteration
- Very simple, fast to run

**When to use**:
- Quick baseline experiments
- Simple problems
- When you need fast results

**Key parameters**:
- `samples_per_prompt`: Variations per iteration

### RandSample

**Best for**: Baseline comparison

**How it works**:
- Random sampling without evolution
- Pure exploration
- No exploitation

**When to use**:
- Baseline to compare other methods
- When diversity is not important
- Quick sanity check

## Decision Guide

### Start Here

```
Do you have a good seed solution?
├─ Yes → Try OpenEvolve
└─ No → Is this a simple problem?
         ├─ Yes → Try (1+1)-EPS or RandSample
         └─ No → Try FunSearch (default)
```

### Quick Reference

| Scenario | Recommended Method |
|----------|-------------------|
| First time trying | FunSearch |
| Have baseline to improve | OpenEvolve |
| Need fast results | (1+1)-EPS |
| Need baseline to compare | RandSample |
| Heuristic optimization | EoH |

## Next Steps

Now let's learn how to [run with YAML configuration](./06-run-with-yaml.md).
