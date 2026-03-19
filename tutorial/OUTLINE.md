# AlgoDisco Tutorial Outline

This tutorial is designed to take you from a complete beginner to proficient user of the AlgoDisco algorithm search/optimization framework. AlgoDisco uses LLMs to discover and optimize algorithms through various evolutionary search methods (similar to AlphaEvolve).

## Learning Objectives Summary

By completing this tutorial series, you will:
- Understand the AlgoDisco architecture and core components
- Run different search methods (FunSearch, OpenEvolve, (1+1)-EPS, etc.)
- Create custom evaluators for your own problems
- Configure LLM providers and execution environments
- Debug and optimize your searches

---

## Phase 1: Getting Started (Notebooks 1-2)

**Prerequisites:** Basic Python knowledge, familiarity with algorithm concepts

### Notebook 1: 01_introduction.ipynb - Introduction to AlgoDisco

**Learning Objectives:**
- Understand what AlgoDisco is and its purpose
- Recognize the key components of the framework
- Trace the flow from configuration to search execution

**Topics Covered:**
- What is algorithm discovery/optimization and why it matters
- AlgoDisco architecture overview (configuration, search methods, LLM, evaluator, iteration loop)
- Key terminology: AlgoProto, IterativeSearchBase, Evaluator, ProgramsDatabase
- The search workflow: Initialize -> Select -> Generate -> Evaluate -> Register
- Overview of available search methods

---

### Notebook 2: 02_quickstart.ipynb - Quick Start Guide

**Learning Objectives:**
- Set up environment and run your first search
- Understand YAML configuration structure
- Interpret search output and logs

**Topics Covered:**
- Environment setup and dependencies
- YAML configuration file structure (method, llm, evaluator, logger sections)
- Running your first search with a simple example
- Understanding terminal output format
- Introduction to logging and result storage

---

## Phase 2: Core Concepts (Notebooks 3-4)

**Prerequisites:** Completion of Phase 1

### Notebook 3: 03_understanding_search_methods.ipynb - Understanding Search Methods

**Learning Objectives:**
- Compare different search strategies
- Choose the right method for your problem
- Understand how each method generates and selects candidates

**Topics Covered:**
- Overview of all available search methods:
  - **FunSearch**: Island-based evolutionary search with prompt-based sampling
  - **OpenEvolve**: Mutation-based evolution with modular prompts
  - **(1+1)-EPS**: Simple (1+1) evolutionary strategy with epsilon-sampling
  - **Random Sampling**: Baseline random generation
  - **EoH**: Evolution of Heuristics with multiple operators
  - **BehaveSim**: Behavior-based similarity search
  - **AlgoBLEU**: BLEU-score based similarity search
- When to use each method (exploration vs exploitation, problem characteristics)
- Comparing method characteristics (population size, selection strategy, mutation)

---

### Notebook 4: 04_evaluator_deep_dive.ipynb - Evaluators and Scoring

**Learning Objectives:**
- Understand the Evaluator interface
- Create evaluators that measure algorithm performance
- Handle different score types and metrics

**Topics Covered:**
- The Evaluator base class and interface
- Evaluation return types (EvalResult TypedDict)
- Score handling and interpretation
- Built-in evaluator patterns
- Common evaluation metrics (accuracy, runtime, correctness)

---

## Phase 3: Customization (Notebooks 5-6)

**Prerequisites:** Completion of Phase 2

### Notebook 5: 05_defining_custom_problems.ipynb - Defining Custom Problems

**Learning Objectives:**
- Create a complete problem definition for AlgoDisco
- Write a custom Evaluator class
- Design template programs and task descriptions

**Topics Covered:**
- Problem definition components:
  - Template program structure
  - Task description writing
  - Search space definition
- Writing custom Evaluator classes
- Integrating evaluators with YAML configuration
- Testing your custom problem
- Best practices for problem formulation

---

### Notebook 6: 06_using_toolkit.ipynb - Using the Toolkit

**Learning Objectives:**
- Use sandbox execution for safe program evaluation
- Configure different LLM providers
- Understand program parsing utilities

**Topics Covered:**
- **Sandbox Execution** (`algodisco/toolkit/sandbox/`):
  - SandboxExecutor for isolated execution
  - Timeout handling and resource limits
  - Secure execution with process isolation
- **Program Parser** (`algodisco/toolkit/program_parser/`):
  - Code extraction from LLM responses
  - Handling different code formats
- **LLM Providers** (`algodisco/providers/llm/`):
  - OpenAI API configuration
  - Claude API configuration
  - vLLM server setup
  - SGLang server setup
- **Configuration System**:
  - YAML config loading
  - Dynamic class instantiation
  - Path resolution

---

## Phase 4: Advanced Topics (Notebooks 7-9)

**Prerequisites:** Completion of Phase 3

### Notebook 7: 07_funsearch_in_depth.ipynb - FunSearch Deep Dive

**Learning Objectives:**
- Understand the island model architecture
- Configure FunSearch parameters for optimal performance
- Interpret database statistics

**Topics Covered:**
- Island model architecture:
  - ProgramsDatabase structure
  - Island and Cluster organization
  - Selection with softmax temperature
  - Island reset and migration
- Configuring FunSearch parameters:
  - num_samplers, num_evaluators
  - examples_per_prompt, samples_per_prompt
  - db_num_islands, db_reset_period
  - cluster_sampling_temperature
- Database management and statistics
- Prompt construction internals

---

### Notebook 8: 08_openevolve_in_depth.ipynb - OpenEvolve Deep Dive

**Learning Objectives:**
- Understand OpenEvolve's mutation-based approach
- Configure modular prompts for different tasks
- Optimize OpenEvolve for your problem

**Topics Covered:**
- OpenEvolve methodology:
  - Single parent selection
  - Modular prompt construction
  - Diff-based mutation
  - Top programs and inspirations
- Configuring OpenEvolve:
  - num_top_programs, num_diverse_programs
  - Migration interval
  - Prompt constructor options
- Best practices and common issues

---

### Notebook 9: 09_advanced_topics.ipynb - Advanced Topics

**Learning Objectives:**
- Debug complex issues in search runs
- Optimize performance for large-scale searches
- Extend AlgoDisco with custom components

**Topics Covered:**
- **Debugging Strategies**:
  - Debug mode configuration
  - Interpreting error messages
  - Logging and tracing
- **Performance Optimization**:
  - Balancing samplers and evaluators
  - Database management
  - Memory and CPU considerations
- **Scaling**:
  - Multi-machine considerations
  - Logger configurations (Pickle, W&B, SwanLab)
- **Extending AlgoDisco**:
  - Creating custom search methods
  - Adding new LLM providers
  - Custom database implementations
- **Common Pitfalls**:
  - Template program errors
  - LLM API issues
  - Evaluation timeouts

---

## Phase 5: Reference (Notebook 10)

### Notebook 10: 10_api_reference.ipynb - API Reference

**Learning Objectives:**
- Quickly look up API components
- Find configuration options
- Troubleshoot common issues

**Topics Covered:**
- **Core Classes**:
  - AlgoProto API
  - IterativeSearchBase interface
  - Evaluator base class
  - LanguageModel interface
- **Configuration Reference**:
  - All method configs (FunSearch, OpenEvolve, etc.)
  - LLM provider options
  - Logger configurations
- **Search Method Details**:
  - Entry points (main_*.py files)
  - Database internals
  - Prompt construction
- **Troubleshooting Guide**:
  - Common errors and solutions
  - FAQ
  - Getting help

---

## Suggested Learning Order

```
Week 1:
├── Day 1-2: Read CLAUDE.md and Notebook 1 (Introduction)
├── Day 3-4: Notebook 2 (Quick Start) - Run a demo
└── Day 5: Notebook 3 (Search Methods Overview)

Week 2:
├── Day 1-2: Notebook 4 (Evaluators)
├── Day 3-4: Notebook 5 (Custom Problems)
└── Day 5: Notebook 6 (Toolkit)

Week 3:
├── Day 1-2: Notebook 7 (FunSearch Deep Dive)
├── Day 3-4: Notebook 8 (OpenEvolve Deep Dive)
└── Day 5: Notebook 9 (Advanced Topics)

Week 4:
└── Notebook 10 (API Reference) - Use as needed
```

---

## Additional Resources

- **Example Problems**: Check the `configs/` directory for example configurations
- **Code Examples**: Reference implementations in `algodisco/methods/*/`
- **API Documentation**: Use Notebook 10 as a quick reference
