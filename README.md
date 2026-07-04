<p align="center">
  <img src="assets/algodisco.jpg" alt="algodisco"/>
</p>

<h1 align="center">
  AlgoDisco: Method Implementations and Tools for<br/>LLM-driven Automated Algorithm Design
</h1>

<p align="center">
  <a href="https://github.com/RayZhhh/algodisco"><img src="https://img.shields.io/github/stars/RayZhhh/algodisco" alt="Stars"></a>
  <a href="https://github.com/RayZhhh/algodisco"><img src="https://img.shields.io/github/forks/RayZhhh/algodisco" alt="Forks"></a>
  <a href="https://github.com/RayZhhh/algodisco/blob/main/LICENSE"><img src="https://img.shields.io/github/license/RayZhhh/algodisco" alt="License"></a>
  <a href="https://deepwiki.com/RayZhhh/algodisco/"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>

## ✨ Key Features

- **Multiple Search Methods**: FunSearch, OpenEvolve, EoH, (1+1)-EPS, MCTS-AHD, PartEvo, RandSample, ReEvo
- **Multiple LLM Providers**: OpenAI, Claude, vLLM, SGLang
- **Sandboxed Execution**: Safe evaluation of generated algorithms
- **Flexible Configuration**: YAML-based configuration with CLI overrides via OmegaConf

## 🛠️ Requirements

- Python >= 3.11 (recommended: 3.12)

## 🚀 Quick Start

```bash
git clone https://github.com/RayZhhh/algodisco.git
cd algodisco
pip install -e .
```

Set your API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

Run the bundled Online Bin Packing example:

```bash
# Via the shell wrapper
bash examples/run_online_bin_packing.sh funsearch

# Or directly via the CLI
algodisco run funsearch --config examples/online_bin_packing/configs/funsearch.yaml
```

For more details, see [Quick Start](docs_en/getting-started/quickstart.md).

## ⚡ CLI Overrides

AlgoDisco uses [OmegaConf](https://omry.github.io/omegaconf/) for configuration loading. Any YAML value can be overridden directly from the command line without editing config files.

**Syntax**: `key.subkey=value` — the key path is dot-separated, matching the YAML structure.

```bash
# Override a single value
algodisco run funsearch --config my_config.yaml method.max_samples=50

# Override multiple values
algodisco run funsearch --config my_config.yaml \
  method.max_samples=200 \
  method.num_samplers=4 \
  method.llm_max_tokens=2048 \
  llm.kwargs.model="gpt-4o"

# Change the LLM provider entirely
algodisco run funsearch --config my_config.yaml \
  llm.class_path="algodisco.providers.llm.claude_api.ClaudeAPI" \
  llm.kwargs.model="claude-sonnet-4-20250514"

# Change the logger
algodisco run funsearch --config my_config.yaml \
  logger.class_path="algodisco.providers.logger.swanlab_logger.BaseSwanLabLogger" \
  logger.kwargs.project="my-project"
```

This is especially useful for:

- **Hyperparameter sweeps**: vary `max_samples`, `samples_per_prompt`, or `num_samplers` across runs
- **Model comparison**: swap `llm.kwargs.model` without duplicating configs
- **Quick debugging**: set `method.debug_mode=true` and `method.max_samples=5` on the fly

The same override syntax works with the shell wrapper too:

```bash
bash examples/run_online_bin_packing.sh funsearch method.max_samples=50 llm.kwargs.model="gpt-4o"
```

## 📖 Configuration

Configs are YAML files with four top-level sections:

```yaml
method:      # Search method parameters (max_samples, num_samplers, etc.)
llm:         # LLM provider (class_path + kwargs)
evaluator:   # Evaluator (class_path + kwargs)
logger:      # Logger backend (Pickle, SwanLab, or WandB)
```

See [Configuration Guide](docs_en/getting-started/configuration.md) for the full reference.

### LLM Providers

| Provider | class_path |
|----------|-----------|
| OpenAI | `algodisco.providers.llm.openai_api.OpenAIAPI` |
| Claude | `algodisco.providers.llm.claude_api.ClaudeAPI` |
| vLLM | `algodisco.providers.llm.vllm_server.VLLMServer` |
| SGLang | `algodisco.providers.llm.sglang_server.SGLangServer` |

### Loggers

| Logger | class_path |
|--------|-----------|
| Pickle (default) | `algodisco.providers.logger.pickle_logger.BasePickleLogger` |
| SwanLab | `algodisco.providers.logger.swanlab_logger.BaseSwanLabLogger` |
| WandB | `algodisco.providers.logger.wandb_logger.BaseWandbLogger` |

## 🔍 Available Search Methods

| Method | CLI name | Description |
|--------|----------|-------------|
| FunSearch | `funsearch` | LLM-guided program search with a scored database |
| OpenEvolve | `openevolve` | Evolutionary search with island-based population |
| EoH | `eoh` | Evolution of Heuristics |
| (1+1)-EPS | `one_plus_one_eps` | Single-parent evolutionary strategy |
| MCTS-AHD | `mcts_ahd` | Monte Carlo Tree Search for heuristic design |
| PartEvo | `partevo` | Partial evolutionary search |
| RandSample | `randsample` | Random sampling baseline |
| ReEvo | `reevo` | Rejection-based evolutionary optimization |

## 📂 Project Structure

```
algodisco/
├── base/                    # Core abstractions (AlgoProto, Evaluator, LLM interfaces)
├── methods/                 # Search method implementations
│   ├── funsearch/
│   ├── openevolve/
│   ├── eoh/
│   └── ...
├── providers/               # LLM and logger providers
│   ├── llm/
│   └── logger/
├── common/                  # Config loading, runner utilities
└── toolkit/                 # Sandbox execution and program parsing
examples/
├── online_bin_packing/      # Ready-to-run example
│   ├── configs/             # YAML configs for each method
│   └── ...
└── run_online_bin_packing.sh
docs_en/                     # Documentation
```

## 📖 Documentation

- [Installation](docs_en/getting-started/installation.md)
- [Quick Start](docs_en/getting-started/quickstart.md)
- [Configuration Guide](docs_en/getting-started/configuration.md)
- [Search Methods](docs_en/user-guide/search-methods/index.md)
- [LLM Providers](docs_en/user-guide/llm-providers/index.md)
- [API Reference](docs_en/api/base-classes.md)
- [Tutorial: Create Your Own Problem](docs_en/tutorials/create-your-own-problem/01-intro.md)

## 📝 Citation

If you use AlgoDisco in your research, please cite:

```bibtex
@misc{algodisco,
  title = {AlgoDisco: Method Implementations and Tools for LLM-driven Automated Algorithm Design},
  author = {Rui Zhang},
  year = {2026},
  url = {https://github.com/RayZhhh/algodisco},
}
```

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.
