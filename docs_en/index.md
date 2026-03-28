# AlgoDisco Documentation

AlgoDisco is an LLM-driven framework for algorithm discovery and optimization. It helps you run repeatable search experiments in which a language model proposes candidate programs, an evaluator scores them, and a search method decides what to keep, mutate, or discard.

## Who This Documentation Is For

This documentation is intended for:

- Researchers prototyping algorithm search workflows
- Engineers evaluating LLM-based program optimization
- Contributors extending AlgoDisco with new methods, evaluators, or providers

## What You Can Do With AlgoDisco

AlgoDisco currently includes the following search methods:

- FunSearch
- OpenEvolve
- EoH
- (1+1)-EPS
- RandSample
- BehaveSim

Supported LLM backends include:

- OpenAI
- Claude
- vLLM
- SGLang

The framework is built around a small set of composable parts:

- A search method that proposes and evolves candidate programs
- An evaluator that executes and scores those candidates
- An LLM backend that generates new implementations
- A logger that records progress and artifacts

## Recommended Workflow

For most users, the fastest path is:

1. Install the package and optional dependencies.
2. Run one of the bundled example configurations.
3. Inspect the generated logs and best-performing programs.
4. Replace the example template and evaluator with your own problem.

## Documentation Map

- [Installation](getting-started/installation.md): environment setup, extras, and API keys
- [Quick Start](getting-started/quickstart.md): run the bundled online bin packing example
- [Configuration Guide](getting-started/configuration.md): understand the YAML structure and path resolution rules
- [Search Methods](user-guide/search-methods/index.md): method-specific behavior and tradeoffs
- [LLM Providers](user-guide/llm-providers/index.md): backend-specific setup
- [Sandbox](user-guide/sandbox.md): safe execution considerations
- [API Reference](api/base-classes.md): core abstractions such as evaluators and search configs

## Typical Runtime Flow

```text
YAML config
    |
    +--> method config
    +--> llm provider
    +--> evaluator
    +--> logger
              |
              v
search loop: prompt -> generate -> evaluate -> register -> repeat
```

## Where To Start

If you are new to the project, read [Installation](getting-started/installation.md) and then follow [Quick Start](getting-started/quickstart.md). If you already know the framework and want to integrate your own task, jump to [Configuration Guide](getting-started/configuration.md) and the developer guides.
