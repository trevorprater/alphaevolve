# AlphaEvolve Project - Consolidated TODO & Roadmap

This document outlines the planned features and enhancements to build a cutting-edge AlphaEvolve implementation, drawing inspiration from the original paper, aiming to surpass existing open-source versions, and incorporating comprehensive best practices.

---

## Phase 1: Achieving Parity and Robust Core Functionality

_(Focus: Make the system reliable and fully functional with real components for standard evolutionary runs)_

- **[P0] Real LLM Integration & Advanced LLM Management:**

  - [ ] Integrate multiple LLM APIs (e.g., Gemini, OpenAI, Anthropic, and other providers from OpenRouter/Fireworks etc.).
  - [ ] Implement robust API key management (env variables, secure config, consider secrets management).
  - [ ] Advanced error handling for LLM calls (retries, exponential backoff, circuit breakers).
  - [ ] Implement rate limiting and request batching for LLM APIs.
  - [ ] **Surpass OpenEvolve:** True `LLMEnsemble` not just for weighted sampling during generation, but also for critique/scoring of programs/prompts. Allow dynamic selection of LLMs based on task complexity, evolutionary stage, or available budget.
  - [ ] Implement support for local LLMs via standardized APIs (e.g., Ollama, vLLM, LiteLLM).

- **[P0] Production-Grade Evaluation Engine:**

  - [ ] **Robust Sandboxing (Critical):** Implement strong, configurable sandboxing for executing evolved code (e.g., Docker containers, gVisor, Firejail, nsjail, or WebAssembly runtimes) to prevent system-level risks.
  - [ ] **Resource Limiting:** Enforce CPU, memory, and execution time limits per evaluation run.
  - [ ] **Evaluation Cascades:** Fully implement `_apply_evaluation_cascades` for multi-stage evaluation with configurable thresholds and early exits (as seen in OpenEvolve's config).
  - [ ] **Fitness Approximation:** Support fitness approximation techniques for computationally expensive evaluation functions.
  - [ ] **Clear Evaluation API:** Develop a clear API for users to define how their specific `user_evaluate_fn` integrates with the (potentially sandboxed) execution of evolved code snippets or full programs. Address how evolved snippets are combined with non-evolved skeleton code for holistic evaluation.

- **[P0] Persistent and Scalable Program Database:**

  - [ ] Implement robust persistence for `ProgramDatabase` (e.g., SQLite, TinyDB, or a lightweight NoSQL solution like DuckDB for OLAP, with options for file-per-program for very large codebases).
  - [ ] **Checkpointing & Resumption:** Implement comprehensive checkpointing for long evolutionary runs, saving the full state of the `ProgramDatabase`, `MAPElitesArchive`, and `DistributedController` (generation number, random states, etc.). Ensure runs can be reliably resumed. (OpenEvolve's CLI suggests this is important).
  - [ ] Optimize database queries, updates, and data structures for handling very large populations and archives efficiently.

- **[P1] Sophisticated Configuration Management:**

  - [ ] Transition all hardcoded configurations (from `main.py`, class defaults) to a hierarchical YAML-based system using typed dataclasses (e.g., Pydantic for validation) for all configurable aspects of the system.
  - [ ] Allow command-line overrides for all key configuration parameters.
  - [ ] Provide clear documentation for all configuration options.

- **[P1] Comprehensive Command-Line Interface (CLI):**
  - [ ] Develop a full-featured CLI (e.g., using `click` or `typer`) for:
    - Starting new evolutionary runs.
    - Resuming from specific checkpoints.
    - Specifying custom configuration files.
    - Listing and inspecting database/archive contents (e.g., top N programs, specific elites).
    - Potentially re-evaluating specific programs or exporting them.
    - Managing multiple experiments or projects.

---

## Phase 2: Advanced Evolutionary Mechanisms & AlphaEvolve Paper Alignment

_(Focus: Implementing the more unique and powerful aspects of AlphaEvolve for superior discovery capabilities)_

- **[P1] Advanced MAP-Elites & Diversity Maintenance:**

  - [ ] Implement more sophisticated, user-configurable feature descriptors (e.g., AST-based complexity, cyclomatic complexity, execution path counts, I/O patterns, specific behavioral characteristics extracted from program output, LLM-assessed code style/maintainability).
  - [ ] Allow users to easily define their own feature functions.
  - [ ] Research and implement advanced MAP-Elites variations if beneficial (e.g., CVT-MAP-Elites, sliding boundary bins, adaptive binning).
  - [ ] **Surpass OpenEvolve:** Develop and test more nuanced diversity metrics (beyond basic edit distance or simple feature-based). Implement adaptive sampling strategies from the archive that dynamically balance exploration (novelty) and exploitation (quality improvement).
  - [ ] Add mechanisms to explicitly prevent premature convergence in the archive.

- **[P1] Full Island Model Implementation:**

  - [ ] Implement actual `trigger_migration` logic in `ProgramDatabase` with various strategies (e.g., best-N, random, elite-exchange).
  - [ ] Design for (and optionally implement) running multiple `DistributedController` instances as separate islands, possibly with network communication for migration.
  - [ ] Allow configurable migration topologies (e.g., ring, star, fully connected) and intervals.

- **[P2] LLM-Generated Evaluation Feedback:**

  - [ ] Fully implement the `_get_llm_feedback` placeholder in `EvaluationEngine`.
  - [ ] Use an LLM to provide structured, qualitative feedback on generated code concerning aspects like correctness, simplicity, efficiency, potential bugs, adherence to constraints, or security vulnerabilities.
  - [ ] Integrate this LLM feedback as additional scores, features, or even as direct input for the next round of prompt engineering to guide the generative LLM.

- **[P2] Advanced Prompt Engineering & Meta-Prompts:**
  - [ ] Implement planned "stochastic formatting" for prompts in `PromptSampler` to enhance diversity.
  - [ ] **Surpass OpenEvolve:** Fully implement the "meta-prompt" evolution concept (as hinted in the AlphaEvolve paper and OpenEvolve's config):
    - Maintain a separate database of prompt components, templates, or instructions.
    - Use an evolutionary process or LLM-driven suggestions to evolve these prompt components.
    - Evaluate prompts based on the aggregate quality/diversity of the solutions they help generate over time.
  - [ ] Allow for dynamic construction and ranking of few-shot examples for prompts, selected strategically from the `ProgramDatabase`.

---

## Phase 3: Cutting-Edge Features, Usability & Research Impact

_(Focus: Making the system a leading research tool, highly usable, and pushing the boundaries)_

- **[P2] Interactive Dashboard & Advanced Visualization:**

  - [ ] Develop a comprehensive web-based dashboard (e.g., Streamlit, Dash, or a custom solution) for:
    - Real-time monitoring of evolutionary runs: score progression, archive fill rate, diversity metrics, LLM API usage/costs, evaluation times.
    - Dynamic, interactive visualization of the MAP-Elites archive (e.g., heatmaps, explorable grids).
    - Detailed inspection of individual programs: code, scores, features, lineage, diffs from parent.
    - Comparison tools for different evolutionary runs or configurations.
  - **Surpass OpenEvolve:** Focus on highly interactive visualizations that offer deep insights into the evolutionary dynamics and solution space.

- **[P2] Human-in-the-Loop (HITL) Capabilities:**

  - [ ] Design interfaces for expert users to inspect promising candidates during a run.
  - [ ] Allow users to provide feedback, manually edit code (with versioning), or approve/reject candidates.
  - [ ] Enable users to inject new "seed" programs or prompt suggestions mid-evolution to guide the search.

- **[P3] Advanced Program Analysis & Representation:**

  - [ ] Integrate static analysis tools (e.g., for detailed complexity metrics, style conformance, early detection of common bugs/inefficiencies in generated code snippets).
  - [ ] Explore Abstract Syntax Tree (AST) based analysis for deeper code understanding and more structured manipulation by LLMs (e.g., LLM suggests AST transformations rather than just text diffs).
  - [ ] **Research Area:** LLM-driven understanding of code semantics to guide more meaningful evolutionary operators (e.g., context-aware mutations, functional crossovers).

- **[P3] Automated Experiment Management & Hyperparameter Optimization:**

  - [ ] Integrate with experiment tracking platforms (e.g., MLflow, Weights & Biases) for logging parameters, metrics, and artifacts.
  - [ ] Implement mechanisms for automated hyperparameter optimization of AlphaEvolve itself (e.g., tuning learning rates for meta-prompts, selection pressures, LLM temperature/model choices for different stages).

- **[P3] Explainability & Interpretability (XAI for Evo-LLMs):**

  - [ ] Develop methods to help users understand _why_ certain evolutionary paths were successful or why specific programs were favored.
  - [ ] If LLMs are used for critique/feedback, surface their reasoning in an understandable format.
  - [ ] For LLM-generated code, attempt to have the LLM provide a "chain-of-thought" or explanation for its modifications.

- **[P3] Enhanced Task Definition and System Adaptability:**
  - [ ] Simplify the process for users to define new, complex problems, potentially involving multiple interacting code files or blocks.
  - [ ] Provide tools or wizards to help users design effective evaluation functions and feature descriptors for novel tasks.
  - [ ] **Research Area:** Enable the system to learn or adapt its evolutionary strategy (e.g., choice of LLMs, prompt templates, diversity mechanisms) based on the problem domain or observed progress.

---

## Project Infrastructure & Developer Experience (DX)

_(Continuous Improvement to match/surpass well-structured projects like OpenEvolve)_

- [ ] **Comprehensive Documentation:** Generate Sphinx-based (or similar) official documentation with:
  - Installation guides.
  - In-depth tutorials for applying AlphaEvolve to new problems.
  - Full API references for all modules and classes.
  - Architectural overview and diagrams.
  - Best practices for designing evaluators and feature descriptors.
- [ ] **CI/CD Enhancements:**
  - Implement automated linting (e.g., Ruff, Black, MyPy) in CI.
  - Expand test suite with more extensive integration tests covering interactions between all components.
  - Add performance regression tests.
  - Automate build and potentially release processes.
- [ ] **Rich Example Suite:**
  - Develop a diverse collection of examples showcasing AlphaEvolve's capabilities on various problem types (e.g., algorithmic puzzles, scientific code optimization, machine learning model tuning, shader generation, etc.). Aim for examples that clearly demonstrate unique strengths.
- [ ] **Packaging and Distribution:**
  - Ensure the project is easily installable as a Python package (e.g., via `pip install .`).
  - Prepare for eventual publication on PyPI if desired.
- [ ] **Community Building (If Open Sourcing):**
  - Establish clear contribution guidelines (`CONTRIBUTING.md`).
  - Set up a Code of Conduct.
  - Define communication channels (e.g., GitHub Discussions, Discord).
- [ ] **Refine `CLAUDE.md` and `README.md`:** Keep these up-to-date as the project evolves.
- [ ] **Containerization:** Develop and maintain a `Dockerfile` (like OpenEvolve's) for easy deployment and reproducible environments.
- [ ] **Build/Task Automation:** Implement a `Makefile` or `pyproject.toml` scripts for common development tasks (testing, linting, building docs, etc.).

---

This consolidated list is ambitious but provides a clear roadmap. Prioritize based on your specific goals for the project!

