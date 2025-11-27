# PRISM v6

**P**rocess · **R**efine · **I**ntegrate · **S**ummarize · **M**anage

A production-ready AI processing framework for CSV-based classification using local LLMs via Ollama. PRISM provides two operational modes: an interactive single-file runner for exploratory work and a parallel orchestrator for large-scale batch processing.

![PRISM Banner](docs/images/banner.png)
<!-- TODO: Add banner image -->

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Modes](#usage-modes)
- [Module Reference](#module-reference)
- [Prompt Engineering](#prompt-engineering)
- [Data Format](#data-format)
- [Advanced Operations](#advanced-operations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Features

### Core Capabilities
- **Dual-Mode Operation**: Interactive CLI for single-file runs or parallel orchestrator for batch processing
- **Local LLM Integration**: Seamless connection to Ollama for privacy-preserving, on-premise AI processing
- **Batch Processing**: Configurable batch sizes (1-15+ rows per API call) for throughput optimization
- **Checkpoint System**: Automatic incremental saves with full resume capability
- **Parallel Workers**: Spawn multiple detached worker processes for large datasets

### Reliability & Recovery
- **Run-Scoped Identifiers**: Unique `{project}_{version}_{model}_{timestamp}` IDs prevent collisions
- **File-Based Status Tracking**: Workers communicate via JSON status files for orchestrator monitoring
- **Graceful Pause/Resume**: Lightweight flag-based pause mechanism
- **Automatic Retry**: Configurable retry logic with exponential backoff
- **Failed Range Tracking**: Persist failed row ranges for targeted reprocessing

### Monitoring & Analytics
- **Real-Time Dashboard**: Rich terminal UI with progress bars, ETA, and throughput metrics
- **Token Statistics**: Track tokens/second, average tokens/row, total token consumption
- **Run Summaries**: Automatic markdown reports per run
- **Analytics Export**: CSV-based performance analytics with categorical distributions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRISM v6 Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │  runner.py  │     │              O_orchestrator.py                   │  │
│  │ (Interactive│     │  ┌─────────┐ ┌─────────┐ ┌─────────┐            │  │
│  │    Mode)    │     │  │Worker 1 │ │Worker 2 │ │Worker N │  Parallel  │  │
│  └──────┬──────┘     │  │W_worker │ │W_worker │ │W_worker │  Processes │  │
│         │            │  └────┬────┘ └────┬────┘ └────┬────┘            │  │
│         │            │       │           │           │                  │  │
│         │            │       └───────────┼───────────┘                  │  │
│         │            │                   │                              │  │
│         │            │           status/*.json                          │  │
│         │            └──────────────────────────────────────────────────┘  │
│         │                                │                                  │
│         └────────────────┬───────────────┘                                  │
│                          │                                                  │
│                          ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         Shared Module Layer                           │ │
│  │                                                                       │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │P_processor  │  │S_serializer │  │ M_monitor   │  │R_repository │  │ │
│  │  │             │  │             │  │             │  │             │  │ │
│  │  │• Ollama API │  │• Checkpoints│  │• Logging    │  │• Project    │  │ │
│  │  │• Batching   │  │• Merge      │  │• Progress   │  │  Structure  │  │ │
│  │  │• Validation │  │• Resume     │  │• Analytics  │  │• Paths      │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│                                    ▼                                        │
│                          ┌─────────────────┐                               │
│                          │   Ollama API    │                               │
│                          │  (Local LLM)    │                               │
│                          └─────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | File | Purpose |
|--------|------|---------|
| **Orchestrator** | `O_orchestrator.py` | Spawns parallel workers, monitors status, merges outputs |
| **Worker** | `W_worker.py` | Processes assigned row range independently |
| **Processor** | `P_processor.py` | Handles Ollama API calls, batching, JSON parsing, validation |
| **Serializer** | `S_serializer.py` | Checkpoint save/load/merge, resume logic |
| **Monitor** | `M_monitor.py` | Logging, progress tracking, analytics generation |
| **Repository** | `R_repository.py` | Project structure, path management |
| **Run IDs** | `utilities/run_ids.py` | Consistent run identifier generation |

---

## Prerequisites

### System Requirements
- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running locally
- At least one LLM model pulled in Ollama (e.g., `ollama pull llama3.2`)

### Verify Ollama Installation
```bash
# Check Ollama is running
ollama list

# Pull a model if needed
ollama pull llama3.2
```

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/prism.git
cd prism
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt contents:**
```
ollama
pandas
pyyaml
rich
```

### 4. Verify Installation
```bash
python3 -c "import ollama; print('Ollama:', ollama.__version__)"
python3 -c "import pandas; print('Pandas:', pandas.__version__)"
python3 -c "from rich.console import Console; print('Rich: OK')"
```

---

## Quick Start

### Interactive Mode (Single File)

Best for: exploratory runs, small datasets, testing prompts.

```bash
python3 runner.py
```

![Interactive Runner Start](docs/images/runner_start.png)
<!-- TODO: Add screenshot of runner.py startup -->

Follow the prompts to:
1. Select or create a project
2. Choose a model
3. Set batch size
4. Define row range
5. Confirm and start

![Interactive Runner Processing](docs/images/runner_processing.png)
<!-- TODO: Add screenshot of runner.py during processing -->

### Automated Mode (Parallel Processing)

Best for: large datasets, production runs, batch processing.

**Step 1: Configure your job**
```bash
cp job_config.example.yaml job_config.yaml
# Edit job_config.yaml with your settings
```

**Step 2: Run the orchestrator**
```bash
python3 O_orchestrator.py job_config.yaml
```

![Orchestrator Dashboard](docs/images/orchestrator_dashboard.png)
<!-- TODO: Add screenshot of orchestrator dashboard with workers -->

**Step 3: Monitor progress**

The orchestrator displays a real-time dashboard showing all worker states, progress, ETA, and errors.

![Orchestrator Complete](docs/images/orchestrator_complete.png)
<!-- TODO: Add screenshot of completed orchestrator run -->

---

## Configuration

### Directory Structure

```
prism/
├── config/
│   ├── models.json           # Model definitions
│   ├── settings.json         # Global settings
│   └── prompts/
│       └── default_prompt.json
├── prompts/
│   └── example_prompt.json   # Custom prompt schemas
├── data/                     # Input data (create as needed)
│   └── sample.csv
├── projects/                 # Auto-created project directories
├── output/                   # Orchestrator outputs
├── checkpoints/              # Checkpoint files
├── status/                   # Worker status files
├── logs/                     # Run logs
├── utilities/
│   └── run_ids.py
├── job_config.yaml           # Your job configuration
├── O_orchestrator.py
├── W_worker.py
├── P_processor.py
├── S_serializer.py
├── M_monitor.py
├── R_repository.py
├── runner.py
└── requirements.txt
```

### Job Configuration (job_config.yaml)

```yaml
# Project identification
project:
  name: "customer_feedback"      # Project name (alphanumeric, underscores)
  version: "v1"                  # Version tag
  description: "Classify customer feedback by topic and sentiment"

# Model settings
model:
  name: "llama3.2"               # Must match Ollama model name
  batch_size: 10                 # Rows per API call (1-15 recommended)
  retries: 3                     # Retry attempts on failure
  delay: 5                       # Seconds between retries

# Input files to process
input_queue:
  - path: "data/feedback_q1.csv"
    label: "q1_feedback"
  - path: "data/feedback_q2.csv"
    label: "q2_feedback"

# Parallelization settings
parallelization:
  enabled: true
  workers: 4                     # Number of parallel workers
  split_strategy: "auto"         # "auto" or "manual"
  manual_ranges:                 # Only used if strategy is "manual"
    - start: 1
      end: 500
    - start: 501
      end: 1000

# Output configuration
output:
  directory: "output/"
  naming_pattern: "{run_id}_{label}"
  checkpoints:
    directory: "checkpoints/"
    interval: 25                 # Checkpoint every N rows
    cleanup_after_merge: false

# Error handling
error_handling:
  strategy: "continue_and_report"
  max_worker_retries: 2
  save_failed_ranges: true
  prompt_on_failure: true        # Ask user what to do on failure

# Merge settings
merge:
  auto_merge: true
  condition: "all_success"       # "all_success", "any_success", "always"
  sort_by: "RowID"

# Prompt configuration
prompts:
  config_file: "prompts/example_prompt.json"

# Monitoring
monitoring:
  status_dir: "status/"
  logs_dir: "logs/"
  dashboard_refresh: 5           # Seconds between dashboard updates
```

### Model Configuration (config/models.json)

```json
{
  "available_models": [
    {
      "id": 1,
      "name": "llama3.2",
      "description": "Meta Llama 3.2 - Fast, general purpose",
      "recommended_for": "general"
    },
    {
      "id": 2,
      "name": "mistral",
      "description": "Mistral 7B - Good for classification",
      "recommended_for": "classification"
    },
    {
      "id": 3,
      "name": "qwen2.5:14b",
      "description": "Qwen 2.5 14B - High accuracy",
      "recommended_for": "complex_tasks"
    }
  ],
  "batch_sizes": [
    {"size": 1, "description": "Maximum accuracy", "speed_multiplier": 1},
    {"size": 5, "description": "Balanced", "speed_multiplier": 5},
    {"size": 10, "description": "Fast", "speed_multiplier": 10},
    {"size": 15, "description": "Very fast", "speed_multiplier": 15}
  ]
}
```

### Global Settings (config/settings.json)

```json
{
  "checkpoint_interval": 50,
  "retry_attempts": 3,
  "retry_delay_seconds": 5,
  "required_input_columns": ["RowID", "Message"],
  "input_filename": "input.csv",
  "project_structure": {
    "data": ["inputs", "outputs"],
    "checkpoints": [],
    "logs": ["terminal_logs", "summaries"],
    "analytics": []
  },
  "log_settings": {
    "save_terminal_logs": true,
    "create_summaries": true,
    "create_analytics": true
  },
  "interactive_version": "v_public"
}
```

---

## Usage Modes

### Interactive Mode (`runner.py`)

The interactive runner provides a guided CLI experience for single-file processing.

```bash
python3 runner.py
```

**Workflow:**
1. **Project Selection**: Choose existing or create new project
2. **Input Validation**: Automatically checks for `input.csv` in `projects/{name}/data/inputs/`
3. **Model Selection**: Pick from configured models
4. **Batch Size**: Choose processing speed vs. accuracy tradeoff
5. **Row Range**: Process all or subset of rows
6. **Confirmation**: Review settings before starting
7. **Processing**: Real-time progress with checkpoint saves
8. **Output**: Merged results in `projects/{name}/data/outputs/`

**Outputs Generated:**
- `data/outputs/{run_id}_r{start}-{end}.csv` - Processed results
- `logs/terminal_logs/run_{run_id}.log` - Full terminal log
- `logs/summaries/summary_{run_id}.md` - Markdown summary
- `analytics/analytics_{run_id}.csv` - Performance metrics

---

### Automated Mode (`O_orchestrator.py`)

The orchestrator manages parallel processing of multiple files.

#### Basic Run
```bash
python3 O_orchestrator.py job_config.yaml
```

#### Dry Run (Preview Execution Plan)
```bash
python3 O_orchestrator.py job_config.yaml --dry-run
```

![Dry Run Output](docs/images/dry_run.png)
<!-- TODO: Add screenshot of dry-run output -->

#### Override Workers
```bash
python3 O_orchestrator.py job_config.yaml --workers 8
```

#### Monitor Existing Run
```bash
python3 O_orchestrator.py job_config.yaml --monitor-only
# Or attach to specific run
python3 O_orchestrator.py job_config.yaml --monitor-only --run-id sample_v1_m1_20250127_143052
```

#### Resume Previous Run
```bash
python3 O_orchestrator.py job_config.yaml --resume --run-id sample_v1_m1_20250127_143052
```

#### View Run Summary
```bash
python3 O_orchestrator.py job_config.yaml --summary --run-id sample_v1_m1_20250127_143052
```

---

### Pause and Resume Operations

PRISM supports graceful pause/resume without data loss.

#### Pause a Running Job
```bash
# Create pause flag - workers will pause at next checkpoint
python3 O_orchestrator.py job_config.yaml --pause-run --run-id <run_id>
```

#### Resume a Paused Job
```bash
# Remove pause flag - workers continue processing
python3 O_orchestrator.py job_config.yaml --resume-run --run-id <run_id>
```

#### Full Resume After Stop
If the orchestrator was terminated:
```bash
python3 O_orchestrator.py job_config.yaml --resume --run-id <run_id>
```

**How Pause Works:**
1. `--pause-run` creates a `pause.flag` file in the status directory
2. Workers check for this flag between batches
3. When found, workers enter a wait loop (logging "Paused... waiting to resume")
4. `--resume-run` removes the flag
5. Workers detect removal and continue processing

---

## Module Reference

### P_processor.py - Processing Engine

The core AI interaction module handling all Ollama API communication.

**Key Features:**
- Single-row and batch processing modes
- Automatic JSON parsing with fallback extraction
- Token usage tracking for throughput metrics
- Configurable retry logic with exponential backoff
- Permissive validation allowing organic labels

**Key Methods:**
```python
processor = Processor(
    model_name="llama3.2",
    prompts_config=prompts_config,
    retries=3,
    delay=5
)

# Process single row
result = processor.process_single_row(row)

# Process batch
results = processor.process_batch(df_batch)

# Full dataframe processing with monitoring
results, api_calls = processor.process_dataframe(
    df=df,
    batch_size=10,
    monitor=monitor,
    serializer=serializer,
    job_id="job_123",
    metadata={"Model_Name": "llama3.2"},
    pause_event=should_pause_func  # Optional pause hook
)
```

**Validation Logic:**
- Enforces conditional relationships (e.g., if `Topic=N/A`, downstream fields = `-`)
- Allows organic labels (model-generated categories not in predefined list)
- Logs warnings for unexpected values without failing

---

### S_serializer.py - Checkpoint Management

Handles all data persistence and recovery operations.

**Key Methods:**
```python
serializer = Serializer(
    checkpoint_dir="checkpoints/",
    checkpoint_interval=50
)

# Save checkpoint
checkpoint_file = serializer.save_checkpoint(df_chunk, job_id, checkpoint_num, metadata)

# Find resume point
df_remaining, last_row_id, has_checkpoint = serializer.get_resume_point(job_id, df)

# Merge all checkpoints
serializer.merge_checkpoints(job_id, output_path)

# Clean up after successful merge
serializer.cleanup_checkpoints(job_id, keep_merged=True)
```

**Checkpoint Naming:**
```
checkpoint_{job_id}_part0001.csv
checkpoint_{job_id}_part0002.csv
...
```

---

### M_monitor.py - Monitoring & Analytics

Provides logging, progress tracking, and post-run analytics.

**Key Methods:**
```python
monitor = Monitor(
    project_path="projects/my_project",
    run_id="run_20250127_143052",
    enable_logging=True
)

monitor.start(total_rows=1000)
monitor.update_progress(current_row=100, total_rows=1000, api_calls=10, metrics={...})
monitor.record_checkpoint(checkpoint_num=1, checkpoint_file="...")
monitor.record_error("Something went wrong")
metrics = monitor.finish()

# Generate analytics from results
monitor.create_analytics(output_df, job_config)
```

**Metrics Tracked:**
- Rows per second
- Tokens per second
- Average tokens per row
- Total API calls
- Error count
- Checkpoint count

---

### W_worker.py - Standalone Worker

Independent process that handles a row range assignment.

**CLI Arguments:**
```bash
python3 W_worker.py \
  --worker-id 1 \
  --input-file data/sample.csv \
  --row-start 1 \
  --row-end 250 \
  --model llama3.2 \
  --batch-size 10 \
  --prompts-config prompts/example_prompt.json \
  --output-dir output/ \
  --output-name results_w1.csv \
  --checkpoint-dir checkpoints/ \
  --checkpoint-interval 25 \
  --status-dir status/ \
  --run-id my_run_123
```

**Status File Output (`status/worker_1.json`):**
```json
{
  "worker_id": 1,
  "run_id": "sample_v1_m1_20250127_143052",
  "state": "running",
  "started_at": "2025-01-27T14:30:52",
  "updated_at": "2025-01-27T14:35:22",
  "row_start": 1,
  "row_end": 250,
  "rows_processed": 150,
  "total_rows": 250,
  "progress_pct": 60.0,
  "api_calls": 15,
  "rows_per_sec": 0.83,
  "tokens_per_sec": 245.5,
  "errors": 0,
  "eta_seconds": 120,
  "checkpoints": ["checkpoint_..._part0001.csv", "..."]
}
```

---

### O_orchestrator.py - Job Orchestrator

Coordinates parallel workers and manages the overall job lifecycle.

**Key Features:**
- Spawns detached worker processes
- File-based status monitoring (workers continue if orchestrator disconnects)
- Automatic row range calculation
- Output merging
- Run manifest for resume capability

**Run Manifest (`logs/{run_id}/run_manifest.json`):**
```json
{
  "run_id": "sample_v1_m1_20250127_143052",
  "project": "sample",
  "version": "v1",
  "model_name": "llama3.2",
  "created_at": "2025-01-27T14:30:52",
  "config_snapshot": {...},
  "files": [
    {
      "label": "feedback_q1",
      "input_file": "data/feedback_q1.csv",
      "status": "completed",
      "row_ranges": [...],
      "merged_output": "output/sample_v1_m1_20250127_143052_feedback_q1.csv"
    }
  ]
}
```

---

## Prompt Engineering

### Prompt Schema Structure

Prompts are defined in JSON files with four key sections:

```json
{
  "system_prompt": "Your instructions to the model...",
  "columns_to_code": ["Column1", "Column2", "Column3"],
  "validation_rules": {
    "valid_column1": ["Value1", "Value2", "Value3"],
    "valid_column2": ["A", "B", "C"]
  },
  "not_applicable_defaults": {
    "Column1": "-",
    "Column2": "-",
    "Column3": "-"
  }
}
```

### Example: Customer Feedback Classification

```json
{
  "system_prompt": "You are a customer feedback analyst. Classify each message into structured categories. Return ONLY valid JSON with no additional text.\n\nFor each message, determine:\n1. Topic: The main subject area\n2. Sentiment: Overall emotional tone\n3. Urgency: How time-sensitive is this\n4. Key_Point: One-sentence summary\n\nIf the message is not relevant customer feedback, set Topic to 'NOT_APPLICABLE' and use defaults for other fields.",
  
  "columns_to_code": [
    "Topic",
    "Sentiment", 
    "Urgency",
    "Key_Point"
  ],
  
  "validation_rules": {
    "valid_topic": ["Product", "Support", "Billing", "Shipping", "Account", "Other"],
    "valid_sentiment": ["Positive", "Negative", "Neutral", "Mixed"],
    "valid_urgency": ["High", "Medium", "Low"]
  },
  
  "not_applicable_defaults": {
    "Topic": "Other",
    "Sentiment": "Neutral",
    "Urgency": "Low",
    "Key_Point": "-"
  }
}
```

### Prompt Best Practices

1. **Be Explicit About Output Format**: Specify "Return ONLY valid JSON"
2. **Define All Expected Values**: List valid options in the system prompt
3. **Handle Edge Cases**: Include NOT_APPLICABLE logic for irrelevant inputs
4. **Use Conditional Logic**: First column can gate subsequent fields
5. **Keep It Concise**: Shorter prompts = faster processing

### Batch Prompt Format

When `batch_size > 1`, PRISM automatically constructs batch prompts:

```
Classify these 10 mentions. Return a JSON ARRAY with one object per mention in the EXACT order given.

═══════════════════════════════════════════════════════════════════
[MENTION 1 of 10]
RowID: 1
[INPUT SENTIMENT]: Negative ← Validate and override if wrong

Title: Poor service
Content: I waited 45 minutes for support and nobody helped me...
═══════════════════════════════════════════════════════════════════

... (repeats for each row)

**RETURN:** A JSON array with EXACTLY 10 objects in order: [{...}, {...}, ...]
```

---

## Data Format

### Input Requirements

Your input CSV must contain:

| Column | Required | Description |
|--------|----------|-------------|
| `RowID` | **Yes** | Unique integer identifier for each row |
| `Message` | **Yes** | Text content to classify |
| `Title` | No | Optional title/subject line |
| `Sentiment` | No | Pre-existing sentiment (model can validate/override) |

**Example Input (`input.csv`):**
```csv
RowID,Title,Message,Sentiment
1,Great product!,I love this product. Works exactly as described.,Positive
2,Shipping delay,My order arrived 2 weeks late. Very disappointed.,Negative
3,,The app crashes whenever I try to login,Negative
4,Question,How do I reset my password?,Neutral
```

### Output Format

Outputs preserve input columns and add model-derived columns:

```csv
RowID,Sentiment,Topic,Validated_Sentiment,Urgency,Key_Point,Model_Name,Batch_Size,Run_ID
1,Positive,Product,Positive,Low,Customer satisfied with product quality,llama3.2,10,sample_v1_m1_20250127
2,Negative,Shipping,Negative,Medium,Delivery significantly delayed,llama3.2,10,sample_v1_m1_20250127
3,Negative,Support,Negative,High,App login functionality broken,llama3.2,10,sample_v1_m1_20250127
4,Neutral,Account,Neutral,Low,Password reset inquiry,llama3.2,10,sample_v1_m1_20250127
```

---

## Advanced Operations

### Running Multiple Files

Configure multiple inputs in `job_config.yaml`:

```yaml
input_queue:
  - path: "data/january.csv"
    label: "jan"
  - path: "data/february.csv"
    label: "feb"
  - path: "data/march.csv"
    label: "mar"
```

Each file is processed sequentially, with parallel workers per file.

### Manual Row Range Assignment

For fine-grained control over worker assignments:

```yaml
parallelization:
  enabled: true
  workers: 4
  split_strategy: "manual"
  manual_ranges:
    - start: 1
      end: 100
    - start: 101
      end: 300
    - start: 301
      end: 600
    - start: 601
      end: 1000
```

### Handling Large Datasets

For datasets with 100k+ rows:

1. **Increase workers**: `--workers 8` or more (depends on your hardware)
2. **Optimize batch size**: `batch_size: 15` for throughput
3. **Reduce checkpoint frequency**: `interval: 100` to reduce I/O
4. **Use SSD storage**: Faster checkpoint writes

### Recovery from Failures

If a run fails mid-processing:

```bash
# 1. Check what happened
python3 O_orchestrator.py job_config.yaml --summary --run-id <run_id>

# 2. View failed ranges
cat failed_ranges.json

# 3. Resume the run
python3 O_orchestrator.py job_config.yaml --resume --run-id <run_id>
```

### Custom Run IDs

Override the auto-generated run ID:

```bash
python3 O_orchestrator.py job_config.yaml --run-id my_custom_run_2025
```

---

## Troubleshooting

### Common Issues

#### "Could not connect to Ollama"
```
❌ ConnectionError: Could not connect to Ollama
```
**Solution:** Ensure Ollama is running:
```bash
ollama serve  # Start Ollama server
ollama list   # Verify models are available
```

#### "No valid JSON found"
```
⚠️ Row 123: JSON parse error
```
**Solution:** 
- Reduce batch size (try `batch_size: 1`)
- Simplify your system prompt
- Check model supports JSON output

#### Workers Not Starting
**Solution:** Check worker logs:
```bash
cat projects/{project}_{version}/{run_id}/logs/terminal_logs/run_*_w1.log
```

#### Out of Memory
**Solution:**
- Reduce `workers` count
- Use smaller model
- Process in smaller row ranges

### Debug Mode

For detailed troubleshooting, examine:
1. **Worker status files**: `status/{run_id}/worker_*.json`
2. **Worker logs**: `projects/.../logs/terminal_logs/run_*_w*.log`
3. **Run manifest**: `logs/{run_id}/run_manifest.json`
4. **Failed ranges**: `failed_ranges.json`

---

## CLI Reference

### runner.py
```
python3 runner.py
```
Interactive mode - no arguments, guided prompts.

### O_orchestrator.py
```
python3 O_orchestrator.py <config> [options]

Arguments:
  config                    Path to job_config.yaml

Options:
  --dry-run                 Show execution plan without running
  --workers N               Override number of workers
  --version TAG             Override version tag
  --monitor-only            Only monitor existing workers
  --run-id ID               Use explicit run ID
  --resume                  Resume previous run (requires --run-id)
  --summary                 Print run summary (requires --run-id)
  --pause-run               Create pause flag (requires --run-id)
  --resume-run              Remove pause flag (requires --run-id)
```

---

## Performance Tuning

### Batch Size Selection

| Batch Size | Accuracy | Speed | Use Case |
|------------|----------|-------|----------|
| 1 | Highest | Slowest | Complex classification, debugging |
| 5 | High | Moderate | Balanced production runs |
| 10 | Good | Fast | Standard classification |
| 15 | Acceptable | Fastest | Simple labeling, high volume |

### Worker Scaling

| Workers | CPU Cores | Expected Throughput |
|---------|-----------|---------------------|
| 2 | 4+ | 2x single worker |
| 4 | 8+ | ~3.5x single worker |
| 8 | 16+ | ~6x single worker |

*Note: Ollama is the bottleneck; returns diminish beyond 4-6 workers.*

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

### Development Setup
```bash
git clone https://github.com/yourusername/prism.git
cd prism
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## License

[Add your license here]

---

## Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM infrastructure
- [Rich](https://rich.readthedocs.io/) for terminal UI components
- [Pandas](https://pandas.pydata.org/) for data manipulation

---

**Built with ❤️ for local AI processing**
