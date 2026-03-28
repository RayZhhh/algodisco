# Contributing

Contributions are welcome. This guide describes the minimum setup and the expected contribution workflow for AlgoDisco.

## Development Setup

```bash
git clone https://github.com/RayZhhh/algodisco.git
cd algodisco

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Install additional extras only if your change needs them, for example:

```bash
pip install -e ".[claude]"
pip install -e ".[wandb]"
pip install -e ".[ray]"
```

## Repository Layout

```text
algodisco/
├── algodisco/               # Core package
│   ├── base/                # Base abstractions
│   ├── common/              # Shared config and utility code
│   ├── methods/             # Search method implementations
│   ├── providers/           # LLM and logger providers
│   └── toolkit/             # Sandboxing and parsing utilities
├── docs_en/                 # English documentation
├── docs_ch/                 # Chinese documentation
├── examples/                # Runnable example tasks and configs
└── tutorial/                # Notebook-based tutorials
```

## Common Contribution Types

### Add a Search Method

Typical work includes:

1. Add a new module under `algodisco/methods/`.
2. Define a config dataclass for the method.
3. Implement the search loop and registration logic.
4. Add an executable entry module.
5. Provide an example config and documentation.

### Add an LLM Provider

Typical work includes:

1. Add a provider under `algodisco/providers/llm/`.
2. Implement the required `LanguageModel` interface.
3. Document constructor arguments and environment requirements.

### Add or Extend an Evaluator

Evaluators must inherit from `algodisco.base.evaluator.Evaluator` and return a result containing at least `score`.

## Quality Expectations

Before opening a pull request:

- keep the change focused and scoped
- add or update tests when behavior changes
- update the relevant documentation
- avoid introducing placeholder paths, fake repository names, or unverified commands

## Pull Request Checklist

1. Fork the repository and create a feature branch.
2. Implement the change and verify it locally.
3. Update docs, configs, or examples if the user-facing workflow changed.
4. Submit a pull request with a concise description of the problem and the fix.

## Reporting Issues

Use GitHub Issues for bug reports, regressions, and feature requests.
