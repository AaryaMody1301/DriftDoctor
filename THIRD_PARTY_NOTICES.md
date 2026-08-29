# Third-party notices

DriftDoctor is licensed under the MIT License. The project depends on or interoperates with the components below. No third-party model weights or package source code are vendored in this repository; users install them from their official distribution channels.

| Component | Use in DriftDoctor | License / terms source |
|---|---|---|
| dbt Core | Parses, builds, and tests local dbt projects | Apache License 2.0 — https://github.com/dbt-labs/dbt-core/blob/main/LICENSE |
| dbt-duckdb | dbt adapter for the local benchmark | Apache License 2.0 — https://github.com/duckdb/dbt-duckdb/blob/master/LICENSE |
| DuckDB | Local disposable analytical database | MIT License — https://github.com/duckdb/duckdb/blob/main/LICENSE |
| PyYAML | Safely reads the project-local dbt profile for CLI guardrails | MIT License — https://github.com/yaml/pyyaml/blob/main/LICENSE |
| Ollama | Optional local inference runtime for the bounded ambiguity agent and historical experiments | MIT License — https://github.com/ollama/ollama/blob/main/LICENSE |
| Qwen2.5-Coder 1.5B Instruct | Optional local comparison/ambiguity model | Apache License 2.0, as declared by the official model card — https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct |
| actions/checkout | GitHub Actions checkout step | MIT License — https://github.com/actions/checkout/blob/main/LICENSE |
| actions/setup-python | GitHub Actions Python setup step | MIT License — https://github.com/actions/setup-python/blob/main/LICENSE |
| actions/upload-artifact | GitHub Actions evidence upload step | MIT License — https://github.com/actions/upload-artifact/blob/main/LICENSE |

## Data and credentials

- All benchmark data is synthetic and generated locally.
- The repository contains no warehouse credentials, private customer data, or API keys.
- The judge-facing CLI accepts only a project-local DuckDB profile and refuses non-DuckDB targets.
- Model-based runs use a local Ollama endpoint; no paid model API credential is required.

## Responsibility

Licenses and service terms can change. Anyone redistributing or deploying DriftDoctor should verify the current upstream terms for the exact versions they use. This notice is an inventory for the hackathon submission, not legal advice.
