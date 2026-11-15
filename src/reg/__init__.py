"""rag-eval-gate: baseline-aware merge gate for RAG quality, built on continuous-eval."""

import os

# continuous-eval sends anonymous usage events to PostHog unless this is set.
# It must be set before continuous_eval is imported anywhere in the process.
os.environ["CONTINUOUS_EVAL_DO_NOT_TRACK"] = "true"

__version__ = "0.1.0"

UPSTREAM = "continuous-eval"
