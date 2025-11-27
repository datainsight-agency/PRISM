# PRISM v6 (Public Release)

A two-mode AI processing framework for CSV-based classification:

- **Interactive**: guided single-file runs (`runner.py`).
- **Automated**: parallel, resumable batch runs (`O_orchestrator.py` + `W_worker.py`).

## Highlights
- Run-scoped IDs (`project_version_modeltag_timestamp`) to avoid collisions across concurrent runs.
- File-based worker status and checkpoints for safe pause/resume and retries.
- Prompt-driven schema with validation and fallback defaults.
- Pause/resume via lightweight flag (`pause.flag`).

## Layout
```
github/
├── README.md
├── job_config.example.yaml
├── config/
│   ├── models.json
│   ├── settings.json
│   └── prompts/default_prompt.json
├── prompts/
│   └── example_prompt.json
├── utilities/run_ids.py
├── runner.py
├── O_orchestrator.py
├── W_worker.py
├── P_processor.py
├── R_repository.py
├── S_serializer.py
└── M_monitor.py
```

## Quick Start (Automated / Parallel)
1) Install deps: `pip install -r requirements.txt` (create your own venv).
2) Copy `job_config.example.yaml` to `job_config.yaml` and adjust:
   - `project.name`, `version`
   - `model.name`
   - `input_queue` paths
   - `prompts.config_file` (e.g., `prompts/example_prompt.json`)
3) Run:
```
python3 O_orchestrator.py job_config.yaml
```
Useful flags:
- `--dry-run` (plan only)
- `--monitor-only` (watch existing workers)
- `--run-id <id>` (attach to an existing run)
- `--resume` (with `--run-id`) resume via manifest
- `--summary` (with `--run-id`) manifest summary
- `--pause-run` / `--resume-run` (with `--run-id`) to pause/unpause

## Quick Start (Interactive)
```
python3 runner.py
```
Walk through model, batch size, row range selection. Outputs go to `projects/{project}/data/outputs/`.

## Pause / Resume (Automated)
- Pause a run: `python3 O_orchestrator.py job_config.yaml --run-id <run_id> --pause-run`
- Resume processing: `python3 O_orchestrator.py job_config.yaml --run-id <run_id> --resume-run`
- Full run resume (after stop): `python3 O_orchestrator.py job_config.yaml --run-id <run_id> --resume`

## Architecture
- **runner.py**: interactive CLI, uses `Repository`, `Processor`, `Serializer`, `Monitor`.
- **O_orchestrator.py**: spawns detached `W_worker.py` processes per row-range, tracks via status files, merges outputs, maintains run manifest.
- **W_worker.py**: loads data slice, runs `Processor`, writes checkpoints and status.
- **P_processor.py**: handles model calls, batching, JSON parsing, validation, stats, pause hook.
- **S_serializer.py**: checkpoint save/merge/resume helpers.
- **M_monitor.py**: logs, progress, analytics summaries.
- **utilities/run_ids.py**: consistent run-id and model tag helper.

## Prompts & Validation
- Edit `prompts/example_prompt.json` (or `config/prompts/default_prompt.json`) to match your schema.
- `columns_to_code` defines expected keys. `validation_rules` supply allowed values per column. `not_applicable_defaults` are used when parent logic short-circuits.

## Data Expectations
- Input CSV must contain `RowID` and `Message` (plus any columns you reference in prompts, e.g., `Title`, `Sentiment`).
- Outputs preserve `RowID` and append model-derived columns.

## Requirements (suggested)
Create `requirements.txt` with:
```
ollama
pandas
pyyaml
rich
```

## Notes
- No datasets are shipped. Provide your own CSVs under `data/` or project folders.
- Status, logs, checkpoints, and outputs are organized under run-scoped directories inside the base paths you configure.
- The public configs here are placeholders; plug in your own models and prompt schemas.
