# Installation

This guide covers the minimum setup needed to run AlgoDisco examples.

## Requirements

- Python 3.11+
- Git
- An API key for the LLM provider you plan to use

## Clone the Repository

```bash
git clone https://github.com/RayZhhh/algodisco.git
cd algodisco
```

## Install the Package

Install AlgoDisco in editable mode:

```bash
pip install -e .
```

Install optional extras only when you need them:

```bash
# Claude support
pip install -e ".[claude]"

# vLLM support
pip install -e ".[vllm]"

# SGLang support
pip install -e ".[sglang]"

# Logging integrations
pip install -e ".[wandb,swanlab]"

# Ray-based sandbox executor
pip install -e ".[ray]"
```

## Set Environment Variables

Set the API key for the provider you want to use:

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

If you use the Python API directly and do not pass `base_url` in code, also set:

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

## Optional External Setup

Some advanced workflows may rely on extra assets or submodules:

```bash
git submodule update --init --recursive
```

## Verify Installation

Run a simple import check:

```bash
python -c "from algodisco.methods.funsearch.config import FunSearchConfig; from algodisco.base.algo import AlgoProto; print('Installation successful!')"
```

## Next Steps

- [Quick Start](quickstart.md) - Run your first algorithm search
- [Configuration Guide](configuration.md) - Understand config structure
