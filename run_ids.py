"""
utilities/run_ids.py - Helpers for consistent run identifiers and model tags
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def resolve_model_tag(model_name: str, models_path: Path = Path("config/models.json")) -> str:
    """
    Resolve a short model tag (e.g., '7' → 'm7') using config/models.json when possible.
    Falls back to a sanitized slice of the model name if no id is found.
    """
    model_tag = None

    if models_path.exists():
        try:
            with open(models_path, "r", encoding="utf-8") as f:
                models = json.load(f).get("available_models", [])
            for model in models:
                if model.get("name") == model_name:
                    model_tag = str(model.get("id"))
                    break
        except Exception:
            # Non-fatal: fall back to sanitized model name
            model_tag = None

    if not model_tag:
        # Sanitize model name to an alphanumeric slug and trim for brevity
        cleaned = "".join(ch for ch in model_name if ch.isalnum())
        model_tag = cleaned[:10] or "unknown"

    return f"m{model_tag}"


def build_run_id(
    project_name: str,
    version: str,
    model_name: str,
    *,
    timestamp: Optional[str] = None,
) -> str:
    """
    Build a run identifier that encodes project, version, model tag, and a timestamp.
    Example: bookings_v2_m7_20250129_153012
    """
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    model_tag = resolve_model_tag(model_name)
    
    def _clean(segment: str) -> str:
        return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in segment)
    
    project_clean = _clean(project_name)
    version_clean = _clean(version)
    
    return f"{project_clean}_{version_clean}_{model_tag}_{ts}"
