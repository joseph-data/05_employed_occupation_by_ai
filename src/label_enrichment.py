"""
Utilities to add English occupation labels to pipeline output using the
published SSYK2012 translation workbook.

The translation file is read directly from:
https://github.com/joseph-data/07_translate_ssyk/blob/main/02_translation_files/ssyk2012_en.xlsx
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from .config import TRANSLATION_URL


def _load_level(sheet_name: str, level: int, url: str) -> pd.DataFrame:
    """Load a single level sheet and return columns ``code<level>``/``label<level>``."""
    # Header row with code/name resides at index 3 (0-based)
    df = pd.read_excel(url, sheet_name=sheet_name, header=3)
    df = df.rename(columns=lambda c: str(c).strip())

    code_col = next(c for c in df.columns if "SSYK" in str(c))
    name_col = next(c for c in df.columns if "Name" in str(c))

    df = df[[code_col, name_col]].dropna(subset=[code_col])
    df[code_col] = df[code_col].astype(str).str.strip().str.zfill(level)
    df[name_col] = df[name_col].astype(str).str.strip()

    return df.rename(columns={code_col: f"code{level}", name_col: f"label{level}"})


def load_translation_tables(url: str = TRANSLATION_URL) -> Dict[int, pd.DataFrame]:
    """Return translation tables for SSYK levels 1–4 keyed by level."""
    tables: Dict[int, pd.DataFrame] = {}
    for level, sheet in ((1, "1-digit"), (2, "2-digit"), (3, "3-digit"), (4, "4-digit")):
        tables[level] = _load_level(sheet, level, url)
    return tables


def apply_translations(df: pd.DataFrame, *, tables: Dict[int, pd.DataFrame] | None = None) -> pd.DataFrame:
    """
    Apply English labels to an aggregated SCB DataFrame with columns ``level``, ``code`` and ``label``.

    The ``label`` column is replaced (when available) with the translation matching
    the SSYK level/code combination. Rows without a translation keep their original label.
    """
    if tables is None:
        tables = load_translation_tables()

    label_maps = {
        level: tbl.set_index(f"code{level}")[f"label{level}"] for level, tbl in tables.items()
    }

    out = df.copy()
    for level, mapping in label_maps.items():
        mask = out["level"] == level
        if mask.any():
            out.loc[mask, "label"] = out.loc[mask, "code"].map(mapping).fillna(
                out.loc[mask, "label"]
            )
    return out


if __name__ == "__main__":
    # Example usage: enrich pipeline output with translated labels and preview
    from .data_manager import load_payload

    pipeline_df = load_payload()
    labeled = apply_translations(pipeline_df)
    print(labeled.head())
