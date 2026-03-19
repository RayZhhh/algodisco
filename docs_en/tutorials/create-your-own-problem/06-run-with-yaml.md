# Running with YAML Configuration

This guide shows how to run algorithmic using YAML configuration files.

## YAML Configuration Structure

A complete YAML config has four main sections:

```yaml
method:
  template_program_path: "path/to/template.txt"
  task_description_path: "path/to/task.txt"
  language: "python"
  # ... method-specific parameters

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null  # Or set OPENAI_API_KEY env var

evaluator:
  class_path: "my_module.MyEvaluator"
  kwargs:
    # Evaluator parameters

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

## Complete Example

Here's a full config for Online Bin Packing with FunSearch:

```yaml
# config.yaml

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
  keep_metadata_keys: ["sample_time", "eval_time", "error_msg"]

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null  # Set OPENAI_API_KEY env var

evaluator:
  class_path: "examples.online_bin_packing.evaluator.OnlineBinPackingEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/funsearch_obp"
```

## Running the Config

```bash
python -m algodisco.methods.funsearch.main_funsearch --config config.yaml
```

## Configuration Options

### Method Section

Common parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `template_program_path` | Path to template file | Required |
| `task_description_path` | Path to task description | "" |
| `language` | Programming language | "python" |
| `num_samplers` | Parallel sampling threads | 4 |
| `num_evaluators` | Parallel evaluation threads | 4 |
| `max_samples` | Maximum samples to generate | 1000 |
| `llm_max_tokens` | Max tokens for LLM response | None |
| `llm_timeout_seconds` | LLM call timeout | 120 |

### LLM Section

Supported providers:

```yaml
# OpenAI
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null

# Anthropic Claude
llm:
  class_path: "algodisco.providers.llm.claude_api.ClaudeAPI"
  kwargs:
    model: "claude-3-haiku-20240307"
    api_key: null

# vLLM (local)
llm:
  class_path: "algodisco.providers.llm.vllm_api.VLLMAPI"
  kwargs:
    model: "llama-3-8b"
    base_url: "http://localhost:8000/v1"

# SGLang (local)
llm:
  class_path: "algodisco.providers.llm.sglang_api.SGLangAPI"
  kwargs:
    model: "llama-3-8b"
    base_url: "http://localhost:30000/v1"
```

### Using Environment Variables

Instead of hardcoding API keys:

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null  # Will use OPENAI_API_KEY env var
```

```bash
export OPENAI_API_KEY="your-api-key"
python -m algodisco.methods.funsearch.main_funsearch --config config.yaml
```

## Alternative: Run with Shell Script

We provide shell scripts for common setups:

```bash
# Run with different methods
bash examples/run_online_bin_packing.sh funsearch
bash examples/run_online_bin_packing.sh openevolve
bash examples/run_online_bin_packing.sh eoh
```

## Next Steps

Learn about [running with Python code](./07-run-with-python.md) instead.
