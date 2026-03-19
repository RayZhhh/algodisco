# Configuration Guide

This guide explains all configuration options available in AlgoDisco YAML configuration files.

## Configuration Structure

The configuration file consists of four main sections:

```yaml
method:
  # Search method configuration
llm:
  # LLM provider configuration
evaluator:
  # Evaluator configuration
logger:
  # Logger configuration
```

## Method Configuration

### Common Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `template_program_path` | `str` | Required | Path to the template program file |
| `task_description_path` | `str` | Required | Path to the task description file |
| `language` | `str` | `"python"` | Programming language of the programs |
| `num_samplers` | `int` | `4` | Number of parallel sampler threads |
| `num_evaluators` | `int` | `4` | Number of parallel evaluator threads |
| `examples_per_prompt` | `int` | `2` | Number of examples to include in prompts |
| `samples_per_prompt` | `int` | `4` | Number of samples to generate per prompt |
| `max_samples` | `int` | `1000` | Maximum number of samples to generate |
| `llm_max_tokens` | `int` | `1024` | Maximum tokens for LLM response |
| `llm_timeout_seconds` | `int` | `120` | Timeout for LLM calls |

### Database Parameters (FunSearch, OpenEvolve)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_num_islands` | `int` | `10` | Number of islands in the population |
| `db_max_island_capacity` | `int` | `null` | Maximum programs per island |
| `db_reset_period` | `int` | `14400` | Island reset period in seconds |
| `db_cluster_sampling_temperature_init` | `float` | `0.1` | Initial sampling temperature |
| `db_cluster_sampling_temperature_period` | `int` | `30000` | Temperature adjustment period |
| `db_save_frequency` | `int` | `100` | Database save frequency |

### Debug Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug_mode` | `bool` | `false` | Enable debug mode with verbose logging |
| `debug_mode_crash` | `bool` | `false` | Exit immediately on error in debug mode |

### Metadata Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `keep_metadata_keys` | `List[str]` | `["sample_time", "eval_time", "execution_time", "error_msg", "prompt", "response_text"]` | Metadata keys to preserve in logs |

## LLM Provider Configuration

### Using OpenAI

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: "your-api-key"
    base_url: "https://api.openai.com/v1"
```

### Using Claude

```yaml
llm:
  class_path: "algodisco.providers.llm.claude_api.ClaudeAPI"
  kwargs:
    model: "claude-3-opus-20240229"
    api_key: "your-api-key"
```

### Using vLLM

```yaml
llm:
  class_path: "algodisco.providers.llm.vllm_server.VLLMServer"
  kwargs:
    model: "meta-llama/Llama-2-70b-hf"
    api_url: "http://localhost:8000/v1"
```

### Using SGLang

```yaml
llm:
  class_path: "algodisco.providers.llm.sglang_server.SGLangServer"
  kwargs:
    model: "meta-llama/Llama-2-70b-hf"
    api_url: "http://localhost:30000/v1"
```

## Evaluator Configuration

### Built-in Evaluators

```yaml
evaluator:
  class_path: "your_module.YourEvaluator"
  kwargs:
    param1: "value1"
    param2: "value2"
```

The evaluator class must inherit from `algodisco.base.evaluator.Evaluator` and implement the `evaluate_program` method.

## Logger Configuration

### Pickle Logger (Default)

```yaml
logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

### Weights & Biases

```yaml
logger:
  class_path: "algodisco.providers.logger.wandb_logger.WandbLogger"
  kwargs:
    project: "my-project"
    entity: "my-team"
```

### SwanLab

```yaml
logger:
  class_path: "algodisco.providers.logger.swanlab_logger.SwanLabLogger"
  kwargs:
    project: "my-project"
    workspace: "my-workspace"
```

## Environment Variables

You can also use environment variables for sensitive configuration:

```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

Then in your config:

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: null  # Will use environment variable
```

## Complete Example

```yaml
method:
  template_program_path: "templates/max_value.py"
  task_description_path: "tasks/max_value.txt"
  language: "python"
  num_samplers: 8
  num_evaluators: 8
  examples_per_prompt: 3
  samples_per_prompt: 5
  max_samples: 500
  llm_max_tokens: 2048
  llm_timeout_seconds: 180
  db_num_islands: 20
  db_max_island_capacity: 50
  db_reset_period: 7200
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
    model: "gpt-4-turbo-preview"

evaluator:
  class_path: "evaluators.max_value_evaluator.MaxValueEvaluator"
  kwargs:
    test_size: 100

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/max_value_search"
```

## Next Steps

- [Search Methods](../user-guide/search-methods/index.md) - Learn about different search algorithms
- [LLM Providers](../user-guide/llm-providers/index.md) - Configure LLM backends
- [Developer Guide](../developer-guide/custom-evaluator.md) - Create custom evaluators
