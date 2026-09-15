"""Central configuration for the evaluation framework.

Everything tunable lives here so you never hunt through test files
to change a threshold or swap a model.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Judge model (the LLM that scores your answers) ---
JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", "nvidia")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "meta/llama-3.3-70b-instruct")

# --- System under test (QAVentra itself) ---
TARGET_API_URL = os.getenv("TARGET_API_URL", "http://localhost:8000")
TARGET_TIMEOUT = 300

# --- Rate limiting ---
# NVIDIA's free tier allows ~40 requests/min. Each metric costs at least
# one judge call, so we pause between questions to avoid 429 errors.
DELAY_BETWEEN_CASES = float(os.getenv("EVAL_DELAY", "5"))

# --- Thresholds ---
DEFAULT_THRESHOLD = 0.7

# These four are INVERTED metrics — a higher score means WORSE behaviour.
# DeepEval 4.2.2 scores these higher-is-better, same as the rest
THRESHOLDS = {}

# --- Output ---
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")


def threshold_for(metric_name: str) -> float:
    """Returns the threshold for a metric, falling back to the default."""
    return THRESHOLDS.get(metric_name, DEFAULT_THRESHOLD)