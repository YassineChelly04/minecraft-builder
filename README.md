# Minecraft Builder

A modern AI-assisted toolkit for generating buildings, city layouts, and factory plans for Minecraft using validated command pipelines.

> ⚠️ **Work in progress:** This project is **not finished yet**. I’m still actively working on the engine responsible for generating buildings inside Minecraft.

## Overview

Minecraft Builder turns natural-language prompts into Minecraft commands through a multi-stage pipeline. It combines deterministic geometry logic, LLM-assisted planning/furnishing, validation/repair safeguards, and execution/export workflows.

## Current Capabilities

- Generate single buildings from text prompts
- Generate city-scale layouts with roads, zoning, and QA scoring
- Generate factory layouts with industry-aware planning
- Export generated commands as datapacks
- Execute commands through keyboard automation or RCON (when configured)
- Validate and repair command output before execution

## Project Architecture

High-level flow:

1. Prompt intake and clarification
2. Intent and planning
3. Structure/shell generation
4. Interior/exterior enhancement
5. Command normalization, repair, and validation
6. Execution or datapack export

Key modules:

- `app.py` – Flask API + UI endpoints
- `pipeline.py` – Single-building pipeline
- `city_pipeline.py` – City generation pipeline
- `factory_pipeline.py` – Factory generation pipeline
- `architecture/` – Geometry, shell, archetypes
- `placers/` – Furniture and lighting placement logic
- `execution/` – Datapack and RCON execution utilities
- `tests/` – Pytest suite

## Tech Stack

- Python
- Flask
- Pytest
- Groq-compatible LLM integration

## Getting Started

### 1) Prerequisites

- Python 3.10+
- pip
- (Optional) Groq API key for live LLM calls

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment

```bash
cp .env.example .env
```

Then edit `.env` with your settings (API keys, model options, execution preferences).

### 4) Run the app

```bash
python app.py
```

Open the local UI in your browser (default Flask port is `5000`).

## Usage

Main API endpoints:

- `POST /clarify`
- `POST /generate`
- `POST /generate_city`
- `POST /generate_factory`
- `POST /execute`
- `POST /export_datapack`

You can use the web interface or call the endpoints directly.

## Testing

Run the test suite:

```bash
pytest
```

## Status & Roadmap

This repository is under active development. Near-term focus includes:

- Improving the building-generation engine quality and consistency
- Expanding archetypes and detailing behavior
- Strengthening placement, repair, and scoring quality
- Improving reliability and performance of full generation pipelines

## Documentation

Additional docs in this repository:

- `/home/runner/work/minecraft-builder/minecraft-builder/UPGRADE_GUIDE.md`
- `/home/runner/work/minecraft-builder/minecraft-builder/DECISIONS.md`
- `/home/runner/work/minecraft-builder/minecraft-builder/SYSTEM_ARCHITECTURE.html`
- `/home/runner/work/minecraft-builder/minecraft-builder/DETAILED_PIPELINE.html`

## Contributing

Contributions, issues, and suggestions are welcome while the engine evolves.

## License

No license file is currently provided in this repository.
