# Configuration Guide

This guide explains the YAML structure used by AlgoDisco and shows the most common configuration patterns.

## Configuration Structure

Most runnable configs have four top-level sections:

```yaml
method:
  # Search method settings
llm:
  # LLM provider instance
evaluator:
  # Evaluator instance
logger:
  # Logger instance
```

## Method Section

The `method` section configures the search algorithm itself.

Common keys:

| Key | Description |
|-----|-------------|
| `template_program_path` | Path to the template program file |
| `task_description_path` | Path to the task description file |
| `language` | Programming language of the generated programs |
| `num_samplers` | Number of sampling workers |
| `num_evaluators` | Number of evaluation workers |
| `examples_per_prompt` | Number of previous examples included in prompts |
| `samples_per_prompt` | Number of candidates generated per prompt |
| `max_samples` | Total number of candidates to generate |
| `llm_max_tokens` | Maximum output tokens per LLM call |
| `llm_timeout_seconds` | Timeout for each LLM call |

Additional keys such as `db_num_islands`, `db_reset_period`, and `keep_metadata_keys` are method-specific or logging-related.

## Path Resolution

Relative paths are resolved from the project root when AlgoDisco loads the config. For example:

```yaml
method:
  template_program_path: "examples/online_bin_packing/template_algo.txt"
  task_description_path: "examples/online_bin_packing/task_description.txt"
```

## LLM Provider Configuration

### OpenAI

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null
    base_url: "https://api.openai.com/v1"
```

### Claude

```yaml
llm:
  class_path: "algodisco.providers.llm.claude_api.ClaudeAPI"
  kwargs:
    model: "claude-3-5-sonnet-20241022"
    api_key: null
```

### vLLM Server Launcher

```yaml
llm:
  class_path: "algodisco.providers.llm.vllm_server.VLLMServer"
  kwargs:
    model_path: "meta-llama/Meta-Llama-3-8B-Instruct"
    port: 8000
    gpus: 0
    launch_vllm_in_init: true
```

### SGLang Server Launcher

```yaml
llm:
  class_path: "algodisco.providers.llm.sglang_server.SGLangServer"
  kwargs:
    model_path: "meta-llama/Meta-Llama-3-8B-Instruct"
    port: 30000
    gpus: 0
    launch_sglang_in_init: true
```

## Evaluator Configuration

You can reference an evaluator either by Python import path or by `path/to/file.py:ClassName`.

```yaml
evaluator:
  class_path: "examples/online_bin_packing/evaluator.py:OnlineBinPackingEvaluator"
  kwargs:
    capacity: 100
```

For your own project code:

```yaml
evaluator:
  class_path: "my_package.my_evaluator.MyEvaluator"
  kwargs: {}
```

The evaluator class must inherit from `algodisco.base.evaluator.Evaluator` and implement `evaluate_program`.

## Logger Configuration

### Pickle Logger

```yaml
logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

### Weights & Biases

```yaml
logger:
  class_path: "algodisco.providers.logger.wandb_logger.BaseWandbLogger"
  kwargs:
    project: "my-project"
    logdir: "logs/my_wandb_run"
```

### SwanLab

```yaml
logger:
  class_path: "algodisco.providers.logger.swanlab_logger.BaseSwanLabLogger"
  kwargs:
    project: "my-project"
    logdir: "logs/my_swanlab_run"
    swanlab_logdir: "logs/my_swanlab_meta"
```

## Environment Variables

Use environment variables for secrets whenever possible:

```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

Then in your config:

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null
    base_url: "https://api.openai.com/v1"
```

## Complete Example

```yaml
method:
  template_program_path: "examples/online_bin_packing/template_algo.txt"
  task_description_path: "examples/online_bin_packing/task_description.txt"
  language: "python"
  num_samplers: 2
  num_evaluators: 2
  examples_per_prompt: 2
  samples_per_prompt: 2
  max_samples: 100
  llm_max_tokens: 1024
  llm_timeout_seconds: 120
  db_num_islands: 5
  db_reset_period: 14400
  db_save_frequency: 50
  keep_metadata_keys:
    - "sample_time"
    - "eval_time"
    - "execution_time"
    - "error_msg"
  debug_mode: false

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null
    base_url: "https://api.openai.com/v1"

evaluator:
  class_path: "examples/online_bin_packing/evaluator.py:OnlineBinPackingEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/online_bin_packing_funsearch"
```

## Next Steps

- [Search Methods](../user-guide/search-methods/index.md) - Learn about different search algorithms
- [LLM Providers](../user-guide/llm-providers/index.md) - Configure LLM backends
- [Developer Guide](../developer-guide/custom-evaluator.md) - Create custom evaluators
