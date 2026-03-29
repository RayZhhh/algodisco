# AlgoDisco Tutorial

This directory contains the English Jupyter notebook tutorial for AlgoDisco.

## Notebook Index

| Notebook | File | Focus |
|----------|------|-------|
| 01 | `01_algo_proto_tutorial.ipynb` | Understand the `AlgoProto` data structure |
| 02 | `02_evaluator_tutorial.ipynb` | Learn how evaluators score generated programs |
| 03 | `03_sandbox_tutorial.ipynb` | Execute untrusted code safely |
| 04 | `04_parser_tutorial.ipynb` | Parse and validate generated code |
| 05 | `05_llm_provider_tutorial.ipynb` | Configure OpenAI, Claude, vLLM, and SGLang |
| 06 | `06_complete_example_tutorial.ipynb` | Walk through a full end-to-end setup |
| 07 | `07_python_run_tutorial.ipynb` | Run AlgoDisco directly from Python |

## Recommended Order

1. Start with `06_complete_example_tutorial.ipynb` if you want the fastest path to a runnable mental model.
2. Read `01_algo_proto_tutorial.ipynb` and `02_evaluator_tutorial.ipynb` to understand the core data structures.
3. Continue with `03_sandbox_tutorial.ipynb` and `04_parser_tutorial.ipynb` for the execution and parsing toolchain.
4. Use `05_llm_provider_tutorial.ipynb` when you want to swap providers or run local backends.
5. Finish with `07_python_run_tutorial.ipynb` if you prefer the Python API over YAML.

## Quick Start

Install the package in editable mode:

```bash
pip install -e .
```

If you want to run the OpenAI-based examples, export your API key first:

```bash
export OPENAI_API_KEY="your-api-key"
```

For YAML-based runs, the quickest working example is:

```bash
bash examples/run_online_bin_packing.sh funsearch
```

For direct Python execution, see:

```bash
python examples/online_bin_packing/run_funsearch.py
```

## Related Documentation

- [docs_en/getting-started/quickstart.md](../docs_en/getting-started/quickstart.md)
- [docs_en/getting-started/configuration.md](../docs_en/getting-started/configuration.md)
- [docs_en/tutorials/create-your-own-problem/01-intro.md](../docs_en/tutorials/create-your-own-problem/01-intro.md)
