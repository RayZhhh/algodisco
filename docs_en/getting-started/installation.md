# Installation

This guide covers the installation requirements and setup for AlgoDisco.

## Requirements

- Python 3.10+
- OpenAI API key (or other LLM provider)
- Git (for cloning the repository)

## Clone the Repository

```bash
git clone https://github.com/your-org/adlab.git
cd `algodisco`
```

## Install Dependencies

The project requires several dependencies. You can install them using pip:

```bash
# Core dependencies
pip install openai anthropic

# Optional: For vLLM backend
pip install vllm

# Optional: For SGLang backend
pip install sglang

# Optional: For logging integrations
pip install wandb swanlab

# Optional: For Ray-based sandbox execution
pip install ray
```

## Environment Variables

Set up your API keys as environment variables:

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# Anthropic (Claude)
export ANTHROPIC_API_KEY="your-api-key"

# Or set custom base URLs for proxy usage
export OPENAI_BASE_URL="https://api.openai.com/v1"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

## External Dependencies

Some search methods may require external dependencies located in the `temp/` directory:

```bash
# Initialize git submodules if present
git submodule update --init --recursive
```

## Verify Installation

You can verify the installation by running a simple test:

```bash
python -c "from algodisco.base import AlgoProto, IterativeSearchBase; print('Installation successful!')"
```

## Next Steps

- [Quick Start](quickstart.md) - Run your first algorithm search
- [Configuration Guide](configuration.md) - Understand configuration options
