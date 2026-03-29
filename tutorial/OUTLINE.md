# AlgoDisco Tutorial Outline

This outline describes the current tutorial notebook set in `tutorial/`.

## Goal

After finishing the notebooks, a reader should be able to:

- Understand the core objects used during search
- Write a custom evaluator
- Run AlgoDisco through YAML or the Python API
- Configure different LLM backends
- Debug common execution and parsing issues

## Current Notebook Path

### 1. `01_algo_proto_tutorial.ipynb`

Focus:
- What `AlgoProto` stores
- How to create it from strings and dictionaries
- How metadata and copying behave

### 2. `02_evaluator_tutorial.ipynb`

Focus:
- What `EvalResult` looks like
- The `Evaluator` interface
- How to write a minimal custom evaluator

### 3. `03_sandbox_tutorial.ipynb`

Focus:
- Safe execution of generated code
- Timeouts and isolation
- Integrating sandbox execution into evaluation

### 4. `04_parser_tutorial.ipynb`

Focus:
- Parsing generated code into a structured representation
- Syntax validation
- Extracting code from model responses

### 5. `05_llm_provider_tutorial.ipynb`

Focus:
- `LanguageModel` interface
- OpenAI and Claude providers
- Local vLLM and SGLang server launchers
- YAML snippets for provider configuration

### 6. `06_complete_example_tutorial.ipynb`

Focus:
- Template program design
- Task description design
- Evaluator construction
- YAML wiring and running an end-to-end search

### 7. `07_python_run_tutorial.ipynb`

Focus:
- `FunSearchConfig` setup in code
- Python-side provider and evaluator construction
- Running searches without YAML

## Suggested Reading Order

If the reader is new:

1. `06_complete_example_tutorial.ipynb`
2. `01_algo_proto_tutorial.ipynb`
3. `02_evaluator_tutorial.ipynb`
4. `03_sandbox_tutorial.ipynb`
5. `04_parser_tutorial.ipynb`
6. `05_llm_provider_tutorial.ipynb`
7. `07_python_run_tutorial.ipynb`

If the reader already understands the framework basics:

1. `05_llm_provider_tutorial.ipynb`
2. `03_sandbox_tutorial.ipynb`
3. `04_parser_tutorial.ipynb`
4. `07_python_run_tutorial.ipynb`
