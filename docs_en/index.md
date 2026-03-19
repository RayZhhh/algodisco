# algodisco Documentation

algodisco is an **algorithm search and optimization framework** that uses Large Language Models (LLMs) to discover and optimize algorithms through various evolutionary search methods. Inspired by AlphaEvolve, the system generates, evaluates, and evolves algorithm implementations to solve computational problems.

## Overview

algodisco supports the following search methods:

- FunSearch
- OpenEvolve
- EoH
- (1+1)-EPS
- RandSample
- BehaveSim

## Key Features

- **Multiple LLM Providers**: Support for OpenAI, Claude, vLLM, and SGLang
- **Sandboxed Execution**: Safe evaluation of generated algorithms
- **Flexible Configuration**: YAML-based configuration system
- **Logging & Tracking**: Comprehensive logging with pickle, WandB, and SwanLab support
- **Extensible Design**: Easy to add new search methods and evaluators

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [Configuration Guide](getting-started/configuration.md)
- [Search Methods](user-guide/search-methods/index.md)
- [LLM Providers](user-guide/llm-providers/index.md)
- [Sandbox](user-guide/sandbox.md)
- [API Reference](api/base-classes.md)

## Architecture

```
                    +------------------+
                    |     Config       |
                    |   (YAML file)   |
                    +--------+---------+
                             |
                             v
+------------------+  +-------v--------+  +------------------+
|   LLM Provider  |<->| Search Method |<->|    Evaluator    |
| (OpenAI/Claude/ |  | (FunSearch/    |  |  (Sandboxed     |
|  vLLM/SGLang)   |  |  OpenEvolve/   |  |   Execution)    |
+------------------+  |  ...)         |  +------------------+
                      +-------+--------+
                              |
                              v
                      +-------+--------+
                      |    Logger     |
                      | (Pickle/WandB/|
                      |   SwanLab)    |
                      +---------------+
```

## Citation

If you use algodisco in your research, please cite the project.
