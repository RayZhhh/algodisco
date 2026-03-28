# Running with YAML Configuration

This guide shows how to run AlgoDisco with a YAML config file.

## YAML Structure

A typical config has four sections:

```yaml
method:
  template_program_path: "path/to/template.txt"
  task_description_path: "path/to/task.txt"
  language: "python"

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null
    base_url: "https://api.openai.com/v1"

evaluator:
  class_path: "my_module.MyEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

## Complete Example

Here is a complete FunSearch config based on the bundled Online Bin Packing example:

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

## Run the Config

```bash
python -m algodisco.methods.funsearch.main_funsearch --config config.yaml
```

## Reusing the Bundled Example

Instead of writing a config from scratch, start from an existing one:

```bash
cp examples/online_bin_packing/configs/funsearch.yaml my_config.yaml
python -m algodisco.methods.funsearch.main_funsearch --config my_config.yaml
```

## Common Provider Configs

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
```

### SGLang Server Launcher

```yaml
llm:
  class_path: "algodisco.providers.llm.sglang_server.SGLangServer"
  kwargs:
    model_path: "meta-llama/Meta-Llama-3-8B-Instruct"
    port: 30000
    gpus: 0
```

## Using Environment Variables

For OpenAI:

```bash
export OPENAI_API_KEY="your-api-key"
```

Then keep `api_key: null` in YAML.

## Convenience Script

The repository includes a shell wrapper for the Online Bin Packing configs:

```bash
bash examples/run_online_bin_packing.sh funsearch
bash examples/run_online_bin_packing.sh openevolve
bash examples/run_online_bin_packing.sh eoh
```

That script is just a convenience wrapper around the `python -m algodisco.methods...` entry points.

## Next Steps

If you want more control or easier debugging, continue with [running through Python code](./07-run-with-python.md).
