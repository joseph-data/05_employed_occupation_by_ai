"""Data manager for loading and caching SCB employment pipeline results.

This module encapsulates the logic for computing the SCB-only
transformations in ``pipeline.py`` and persisting the result to disk.
It adds a small amount of resilience around caching and uses
``logging`` instead of printing directly to stdout.  The cache file
includes a version tag to make it easy to invalidate caches when
fundamental changes are made to the pipeline logic.
"""

import os
import tempfile
import logging
from pathlib import Path
from functools import lru_cache

import pandas as pd

from . import pipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache setup
# ---------------------------------------------------------------------------
# A version tag to embed into the cache filenames.  Bump this value
# whenever the underlying ``pipeline`` logic changes in a way that
# invalidates existing caches (or when you want to force a fresh recompute).
CACHE_VERSION: str = "v1"


def _resolve_cache_dir() -> Path:
    """Select a writable directory for caching.

    The lookup order is:

    1. The ``DATA_CACHE_DIR`` environment variable, if set.
    2. A ``data`` folder at the repository root.
    3. A temporary directory in ``/tmp``.

    Each candidate path is tested for writability by attempting to
    create and delete a sentinel file.  The first path that succeeds
    is returned.  If none succeed, a final fallback directory in ``/tmp``
    is created and returned.
    """
    candidates: list[Path] = []
    env = os.getenv("DATA_CACHE_DIR")
    if env:
        # Expand relative or user paths to absolute
        candidates.append(Path(env).expanduser().resolve())

    # Repo root /data (two levels up from this file)
    candidates.append(Path(__file__).resolve().parent.parent / "data")
    # Temp fallback
    candidates.append(Path(tempfile.gettempdir()) / "employment_ai_cache")

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            return path
        except Exception:
            continue

    # Final fallback: ensure the last candidate exists
    fallback = Path(tempfile.gettempdir()) / "employment_ai_cache"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# Resolve the directory once at import time
DATA_DIR: Path = _resolve_cache_dir()

# Single cache file for the SCB-only output DataFrame.
SCB_CACHE: Path = DATA_DIR / f"scb_employment_{CACHE_VERSION}.csv"


def _atomic_to_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV atomically.

    The CSV is first written to a temporary file in the same directory
    and then renamed to the final location.  This avoids leaving a
    partially written file if the process is interrupted mid‑write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


@lru_cache(maxsize=1)
def _compute_pipeline_payload() -> pd.DataFrame:
    """Run the SCB-only pipeline calculation (cached in-process)."""
    return pipeline.run_pipeline()


def load_payload() -> pd.DataFrame:
    """Load employment data from disk cache if available, otherwise compute and save.

    To force a rebuild, delete the cache file or bump `CACHE_VERSION` and restart.
    """
    if SCB_CACHE.exists():
        logger.info("Loading pipeline output from cache directory %s", DATA_DIR)
        try:
            return pd.read_csv(SCB_CACHE)
        except Exception as exc:
            # If reading the cache fails, fall back to recomputing
            logger.warning(
                "Error reading cache file %s: %s; falling back to recompute",
                SCB_CACHE,
                exc,
            )

    logger.info("Computing SCB employment data – this may take a while…")
    payload = _compute_pipeline_payload()

    # Persist to disk atomically
    try:
        _atomic_to_csv(payload, SCB_CACHE)
        logger.info("Cache updated: %s", SCB_CACHE.name)
    except Exception as exc:
        logger.warning("Could not write cache file: %s", exc)

    return payload
