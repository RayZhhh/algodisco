# Quick Start

This guide helps you run your first AlgoDisco search with the built-in Online Bin Packing example.

## Overview

The shortest beginner path is:

1. Install the package
2. Set your API key
3. Run the provided FunSearch example
4. Inspect the generated logs

Once that works, move on to writing your own evaluator and template.

## Step 1: Install AlgoDisco

```bash
git clone https://github.com/RayZhhh/algodisco.git
cd algodisco
pip install -e .
```

## Step 2: Set Your API Key

The default example uses the OpenAI provider:

```bash
export OPENAI_API_KEY="your-api-key"
```

The bundled YAML config already sets `base_url: "https://api.openai.com/v1"`, so that variable is enough for this path.

## Step 3: Run the Example

Recommended command:

```bash
bash examples/run_online_bin_packing.sh funsearch
```

Equivalent direct entry point:

```bash
algodisco run funsearch --config examples/online_bin_packing/configs/funsearch.yaml
```

This example uses:

- Template program: `examples/online_bin_packing/template_algo.txt`
- Task description: `examples/online_bin_packing/task_description.txt`
- Evaluator: `examples/online_bin_packing/evaluator.py:OnlineBinPackingEvaluator`
- Logger: `algodisco.providers.logger.pickle_logger.BasePickleLogger`

## Step 4: Inspect the Output

The default FunSearch config writes logs to:

```text
logs/online_bin_packing_funsearch/
```

After a successful run, you should see logged candidates and other search artifacts under that directory.

## Step 5: Make a Small Change (Without Editing Config Files)

AlgoDisco supports **CLI overrides** via OmegaConf. You can override any YAML value directly from the command line:

```bash
# Quick smoke test: only 5 samples
algodisco run funsearch --config examples/online_bin_packing/configs/funsearch.yaml \
  method.max_samples=5

# Try a different model
algodisco run funsearch --config examples/online_bin_packing/configs/funsearch.yaml \
  llm.kwargs.model="gpt-4o"

# Combine multiple overrides
algodisco run funsearch --config examples/online_bin_packing/configs/funsearch.yaml \
  method.max_samples=50 \
  method.samples_per_prompt=4 \
  llm.kwargs.model="gpt-4o"
```

The override syntax is `key.subkey=value`, matching the YAML structure. This works with the shell wrapper too:

```bash
bash examples/run_online_bin_packing.sh funsearch method.max_samples=5
```

Alternatively, you can copy and edit the config file directly:

```bash
cp examples/online_bin_packing/configs/funsearch.yaml my_config.yaml
# Edit my_config.yaml, then:
algodisco run funsearch --config my_config.yaml
```

You can also try another method such as `openevolve`, `mcts_ahd`, `partevo`, or `reevo`.

## What the YAML Config Looks Like

```yaml
method:
  template_program_path: "examples/online_bin_packing/template_algo.txt"
  task_description_path: "examples/online_bin_packing/task_description.txt"
  language: "python"
  max_samples: 100

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

## Next Step: Create Your Own Problem

After you can run the bundled example, follow the tutorial sequence:

- [Introduction](../tutorials/create-your-own-problem/01-intro.md)
- [Create an Evaluator](../tutorials/create-your-own-problem/03-create-evaluator.md)
- [Create a Template](../tutorials/create-your-own-problem/04-create-template.md)
- [Run with YAML](../tutorials/create-your-own-problem/06-run-with-yaml.md)

## Notes

- `examples/run_max_value.py` is a lightweight evaluator demo. It is useful for understanding the evaluation pattern, but it is not the main end-to-end search example.
- If you want a lower-level workflow without YAML, see [Run with Python](../tutorials/create-your-own-problem/07-run-with-python.md).
