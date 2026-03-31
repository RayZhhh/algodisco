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

## ✨ Key features

- **Multiple Search Methods**: FunSearch, OpenEvolve, EoH, (1+1)-EPS, RandSample
- **Multiple LLM Providers**: OpenAI, Claude, vLLM, SGLang
- **Sandboxed Execution**: Safe evaluation of generated algorithms
- **Flexible Configuration**: YAML-based configuration system

## 🛠️ Requirements

- Python >= 3.11 (recommended: 3.12)

## 🚀 Quick start

```bash
# Install the package in editable mode
pip install -e .
```

If you want to use the default OpenAI path, export your API key first:

```bash
export OPENAI_API_KEY="your-api-key"
```

We provide two practical starting points:

1. **Python API example**:
   ```bash
   python examples/online_bin_packing/run_funsearch.py
   ```

2. **YAML example** (recommended for learning the config system):
   ```bash
   bash examples/run_online_bin_packing.sh funsearch
   ```

For more details, see [Quick Start](docs_en/getting-started/quickstart.md).

## 📖 Documentation

- [Installation](docs_en/getting-started/installation.md)
- [Search Methods](docs_en/user-guide/search-methods/index.md)
- [LLM Providers](docs_en/user-guide/llm-providers/index.md)
- [API Reference](docs_en/api/base-classes.md)
- [Tutorial: Create Your Own Problem](docs_en/tutorials/create-your-own-problem/01-intro.md)

## 🔍 Available search methods

- FunSearch
- OpenEvolve
- EoH
- (1+1)-EPS
- RandSample

## 💡 Quick example

Want to run a search? Here's how:

### Option 1: Use provided example (Online Bin Packing)

We provide a ready-to-use example in `examples/online_bin_packing/`.

#### Python-style (direct code):
```bash
python examples/online_bin_packing/run_funsearch.py
```
Set your API key first:
```bash
export OPENAI_API_KEY="your-api-key"
```

#### YAML-style (recommended):
Configs for each method are in `examples/online_bin_packing/configs/`:

| Method | Config File |
|--------|-------------|
| FunSearch | `configs/funsearch.yaml` |
| OpenEvolve | `configs/openevolve.yaml` |
| EoH | `configs/eoh.yaml` |
| (1+1)-EPS | `configs/one_plus_one_eps.yaml` |
| RandSample | `configs/randsample.yaml` |

1. Copy and edit the config:
   ```bash
   cp examples/online_bin_packing/configs/funsearch.yaml examples/online_bin_packing/configs/my_config.yaml
   ```

2. Open `my_config.yaml` and replace:
   - `api_key: null` → `api_key: "your-openai-key"` (or set `OPENAI_API_KEY` env var)

3. Run with any method (just change the argument):
   ```bash
   # Run with FunSearch
   bash examples/run_online_bin_packing.sh funsearch

   # Run with OpenEvolve
   bash examples/run_online_bin_packing.sh openevolve

   # Run with EoH
   bash examples/run_online_bin_packing.sh eoh

   # Run with (1+1)-EPS
   bash examples/run_online_bin_packing.sh one_plus_one_eps

   # Run with RandSample
   bash examples/run_online_bin_packing.sh randsample
   ```

Available methods: `funsearch`, `openevolve`, `eoh`, `one_plus_one_eps`, `randsample`

For SwanLab integration, use `funsearch_swanlab`:
   ```bash
   bash examples/run_online_bin_packing.sh funsearch_swanlab
   ```

### Option 2: Create your own experiment

1. Choose a method (e.g., FunSearch) and copy one of the example configs:
   ```bash
   cp examples/online_bin_packing/configs/funsearch.yaml my_experiment.yaml
   ```

2. Edit `my_experiment.yaml` to set your:
   - `template_program_path`: Your algorithm template
   - `task_description_path`: Problem description
   - `evaluator.class_path`: Your evaluator class
   - LLM provider settings (API key, model, etc.)

3. Run:
   ```bash
   python -m algodisco.methods.funsearch.main_funsearch --config my_experiment.yaml
   ```

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
