# PRISM v6 - Quickstart Guide

Get PRISM running with Ollama Cloud in under 10 minutes.

---

## Table of Contents

1. [Clone & Install](#1-clone--install)
2. [Setup Ollama Cloud](#2-setup-ollama-cloud)
3. [Test Cloud Models](#3-test-cloud-models)
4. [Configure Your Prompt](#4-configure-your-prompt)
5. [Prepare Your Data](#5-prepare-your-data)
6. [Run PRISM](#6-run-prism)
7. [Next Steps](#7-next-steps)

---

## 1. Clone & Install

### Clone the Repository

```bash
git clone https://github.com/datainsight-agency/PRISM.git
cd prism
```

### Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate it
source venv/bin/activate        # Linux/macOS
# or
venv\Scripts\activate           # Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- `ollama` - Ollama Python client
- `pandas` - Data manipulation
- `pyyaml` - YAML config parsing
- `rich` - Beautiful terminal UI

### Verify Installation

```bash
python3 -c "import ollama, pandas, yaml, rich; print('✅ All dependencies installed!')"
```

---

## 2. Setup Ollama Cloud

### Install Ollama (if not already installed)

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from [ollama.com/download](https://ollama.com/download)

### Sign In to Ollama Cloud

```bash
ollama login
```

This opens your browser to authenticate. Sign in or create an account at [ollama.com](https://ollama.com).

> 💡 **Tip:** Ollama Pro ($20/mo) gives you 20x+ more usage. Free tier has limited requests.

### Verify Cloud Access

```bash
# Quick test - should respond without needing local GPU
ollama run gpt-oss:20b-cloud "Say hello in exactly 5 words"
```

If this works, you're ready to use cloud models! 🎉

---

## 3. Test Cloud Models

### Available Cloud Models

| Model | Command | Best For |
|-------|---------|----------|
| GPT-OSS 20B | `ollama run gpt-oss:20b-cloud` | Fast, general purpose |
| GPT-OSS 120B | `ollama run gpt-oss:120b-cloud` | Production, higher accuracy |
| DeepSeek V3.1 | `ollama run deepseek-v3.1:671b-cloud` | Complex reasoning |
| Qwen3-Coder | `ollama run qwen3-coder:480b-cloud` | Code tasks |
| GLM-4.6 | `ollama run glm-4.6:cloud` | Coding & agents |
| MiniMax M2 | `ollama run minimax-m2:cloud` | Agentic workflows |
| Kimi K2 | `ollama run kimi-k2:1t-cloud` | General, 256K context |
| Kimi K2 Thinking | `ollama run kimi-k2-thinking:cloud` | Research-grade reasoning |

### Test a Model

```bash
# Start a conversation
ollama run gpt-oss:20b-cloud

# You'll see a prompt like:
# >>> 

# Type your message:
>>> Classify this feedback as Positive, Negative, or Neutral: "Great product!"

# To exit:
>>> /bye
```

### Exit / Unload Models

```bash
# Exit interactive mode
>>> /bye

# Or press Ctrl+D

# To stop the Ollama service (if running locally)
# Just close the terminal or:
ollama stop
```

---

## 4. Configure Your Prompt

PRISM uses a JSON prompt configuration file. You need to customize this for your classification task.

### Prompt File Location

The orchestrator uses: `prompts/example_prompt.json`
(configured in `job_config.yaml` under `prompts.config_file`)

### Edit the Prompt

```bash
# Open the prompt file
nano prompts/example_prompt.json
# or use your preferred editor
```

### Prompt Structure Explained

```json
{
  "system_prompt": "Your instructions to the AI model...",
  "columns_to_code": ["Column1", "Column2", "Column3"],
  "validation_rules": {
    "valid_column1": ["Option1", "Option2", "Option3"]
  },
  "not_applicable_defaults": {
    "Column1": "DefaultValue",
    "Column2": "-"
  }
}
```

### Example: Customer Feedback Classification

Replace `prompts/example_prompt.json` with:

```json
{
  "system_prompt": "You are a customer feedback analyst. Classify each message into structured categories.\n\nRules:\n1. Return ONLY valid JSON, no additional text\n2. Use exactly these categories\n3. If message is not customer feedback, set Topic to 'NOT_APPLICABLE'\n\nFor each message determine:\n- Topic: Main subject (Product, Support, Billing, Shipping, Account, Other)\n- Sentiment: Emotional tone (Positive, Negative, Neutral, Mixed)\n- Urgency: Time sensitivity (High, Medium, Low)\n- Key_Point: One sentence summary of the main issue",

  "columns_to_code": [
    "Topic",
    "Sentiment",
    "Urgency",
    "Key_Point"
  ],

  "validation_rules": {
    "valid_topic": ["Product", "Support", "Billing", "Shipping", "Account", "Other", "NOT_APPLICABLE"],
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

### Key Fields

| Field | Purpose |
|-------|---------|
| `system_prompt` | Instructions for the AI model |
| `columns_to_code` | Output columns the model should generate |
| `validation_rules` | Valid values for each column (optional) |
| `not_applicable_defaults` | Default values when first column is NOT_APPLICABLE |

---

## 5. Prepare Your Data

### Input File Requirements

Your CSV must have these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `RowID` | ✅ Yes | Unique integer ID for each row |
| `Message` | ✅ Yes | Text to classify |
| `Title` | ❌ No | Optional title/subject |
| `Sentiment` | ❌ No | Pre-existing sentiment (model can validate) |

### Example Input CSV

Create `data/input.csv`:

```csv
RowID,Title,Message,Sentiment
1,Great product!,I absolutely love this product. Works exactly as described and arrived quickly.,Positive
2,Shipping delay,My order was supposed to arrive last week but it's still not here. Very frustrated.,Negative
3,,The mobile app keeps crashing whenever I try to check my account balance.,Negative
4,Question,How do I update my payment method? I can't find the option in settings.,Neutral
5,Thank you!,Your support team was incredibly helpful. Issue resolved in minutes!,Positive
```

### For Orchestrator Mode

Place your CSV at the path specified in `job_config.yaml`:

```yaml
input_queue:
  - path: "data/input.csv"    # <-- Your file goes here
    label: "feedback"
```

### For Interactive Mode

Place your CSV at:
```
projects/{project_name}/data/inputs/input.csv
```

---

## 6. Run PRISM

### Option A: Interactive Mode (Single File, Guided)

Best for: Testing, small datasets, exploring.

```bash
python3 runner.py
```

**What happens:**
1. Select or create a project
2. Choose a cloud model
3. Set batch size (10 recommended)
4. Select row range
5. Confirm and process

![Interactive Mode](docs/images/runner_interactive.png)
<!-- TODO: Add screenshot -->

### Option B: Orchestrator Mode (Parallel, Automated)

Best for: Large datasets, production runs.

#### Step 1: Configure Job

Copy and edit the job config:

```bash
cp job_config.example.yaml job_config.yaml
nano job_config.yaml
```

**Key settings to change:**

```yaml
# Project name
project:
  name: "my_analysis"
  version: "v1"

# Cloud model selection
model:
  name: "gpt-oss:20b-cloud"    # Change to your preferred model
  batch_size: 10

# Your input file
input_queue:
  - path: "data/input.csv"     # Path to your CSV
    label: "main"

# Prompt file
prompts:
  config_file: "prompts/example_prompt.json"

# Workers (cloud can handle 4-8)
parallelization:
  enabled: true
  workers: 4
```

#### Step 2: Dry Run (Preview)

```bash
python3 O_orchestrator.py job_config.yaml --dry-run
```

This shows the execution plan without actually running.

#### Step 3: Run

```bash
python3 O_orchestrator.py job_config.yaml
```

![Orchestrator Dashboard](docs/images/orchestrator_dashboard.png)
<!-- TODO: Add screenshot -->

#### Step 4: Monitor (Optional)

If you detach (Ctrl+C), workers continue. Reattach with:

```bash
python3 O_orchestrator.py job_config.yaml --monitor-only
```

---

## 7. Next Steps

### Check Your Results

**Orchestrator mode outputs:**
```
output/{run_id}/                    # Merged CSV outputs
checkpoints/{run_id}/               # Incremental checkpoints
logs/{run_id}/                      # Logs and summaries
status/{run_id}/                    # Worker status files
```

**Interactive mode outputs:**
```
projects/{project}/data/outputs/    # Final CSV
projects/{project}/checkpoints/     # Checkpoints
projects/{project}/logs/            # Logs
projects/{project}/analytics/       # Performance analytics
```

### Useful Commands

```bash
# Resume an interrupted run
python3 O_orchestrator.py job_config.yaml --resume --run-id <run_id>

# Pause a running job
python3 O_orchestrator.py job_config.yaml --pause-run --run-id <run_id>

# View run summary
python3 O_orchestrator.py job_config.yaml --summary --run-id <run_id>

# Override worker count
python3 O_orchestrator.py job_config.yaml --workers 8
```

### Customize Settings

Edit `config/settings.json` for global settings:

```json
{
  "checkpoint_interval": 50,      // Save every N rows
  "retry_attempts": 3,            // Retries on failure
  "retry_delay_seconds": 5,       // Delay between retries
  "required_input_columns": [
    "RowID",
    "Message"
  ]
}
```

### Update Model Catalog

Edit `config/models.json` to add/modify available models.

---

## Quick Reference

### File Structure

```
prism/
├── runner.py                    # Interactive mode
├── O_orchestrator.py            # Parallel orchestrator
├── W_worker.py                  # Worker process
├── job_config.yaml              # Your job configuration
├── prompts/
│   └── example_prompt.json      # Your prompt config ⬅️ EDIT THIS
├── config/
│   ├── models.json              # Model definitions
│   └── settings.json            # Global settings
├── data/
│   └── input.csv                # Your input data ⬅️ ADD THIS
└── output/                      # Results appear here
```

### Model Quick Reference

| Speed | Model | Use |
|-------|-------|-----|
| ⚡⚡⚡⚡⚡ | `gpt-oss:20b-cloud` | Fast general tasks |
| ⚡⚡⚡⚡ | `gpt-oss:120b-cloud` | Production |
| ⚡⚡⚡ | `deepseek-v3.1:671b-cloud` | Complex reasoning |
| ⚡⚡⚡ | `qwen3-coder:480b-cloud` | Code analysis |

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Not logged in" | Run `ollama login` |
| "Model not found" | Check model name spelling, ensure `-cloud` suffix |
| Rate limited | Reduce workers/batch size, or upgrade to Pro |
| JSON parse error | Reduce batch_size to 1, simplify prompt |

---

## Need Help?

- 📖 Full documentation: [README.md](README.md)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/prism/issues)
- 💬 Ollama Discord: [discord.gg/ollama](https://discord.gg/ollama)

---

**Happy classifying! 🎯**
