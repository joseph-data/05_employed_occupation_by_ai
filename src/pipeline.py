"""Core pipeline logic for SCB employment-only data.

This module fetches employment data from Statistics Sweden (SCB),
derives SSYK2012 hierarchy columns from 4-digit codes, and aggregates
employment totals across hierarchy levels. DAIOE exposure inputs have
been removed so the output contains only SCB employment counts.
"""

from __future__ import annotations

from typing import Dict, Optional

import logging
import pandas as pd

from .config import TAXONOMY
from .label_enrichment import apply_translations
from .scb_fetch import fetch_all_employment_data

logger = logging.getLogger(__name__)


def filter_years(
    df: pd.DataFrame,
    year_min: Optional[int],
    year_max: Optional[int],
    *,
    year_col: str,
) -> pd.DataFrame:
    """Return a DataFrame filtered to the inclusive year range."""
    if year_min is None and year_max is None:
        return df.copy()
    mask = pd.Series(True, index=df.index, dtype=bool)
    if year_min is not None:
        mask &= df[year_col] >= year_min
    if year_max is not None:
        mask &= df[year_col] <= year_max
    mask = mask.fillna(False)
    return df.loc[mask].copy()


def prepare_employment(
    raw: pd.DataFrame,
    *,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> pd.DataFrame:
    """Clean SCB employment data and derive SSYK hierarchy columns."""
    if raw.empty:
        raise ValueError("SCB fetch returned an empty DataFrame.")

    emp = raw.copy()
    emp["code4"] = emp["code_4"].astype(str).str.zfill(4)
    emp["code3"] = emp["code4"].str[:3]
    emp["code2"] = emp["code4"].str[:2]
    emp["code1"] = emp["code4"].str[:1]

    emp["label4"] = emp["occupation"].fillna("").str.strip()
    emp["label3"] = emp["code3"]
    emp["label2"] = emp["code2"]
    emp["label1"] = emp["code1"]

    emp["age"] = emp["age"].astype(str).str.strip()
    emp["year"] = pd.to_numeric(emp["year"], errors="coerce").astype("Int64")
    emp["employment"] = pd.to_numeric(emp["value"], errors="coerce").fillna(0)

    emp = emp.dropna(subset=["year"])
    emp = filter_years(emp, year_min, year_max, year_col="year")

    ordered_cols = [
        "year",
        "age",
        "code4",
        "label4",
        "code3",
        "label3",
        "code2",
        "label2",
        "code1",
        "label1",
        "employment",
    ]
    return emp[ordered_cols]


def compute_children_maps(df: pd.DataFrame) -> Dict[int, pd.DataFrame]:
    """Count the number of descendants for each code at each hierarchy level."""
    base = df[["year", "code4", "code3", "code2", "code1"]].drop_duplicates()
    counts: Dict[int, pd.DataFrame] = {}
    counts[3] = (
        base.groupby(["year", "code3"])["code4"]
        .nunique()
        .reset_index(name="n_children")
    )
    counts[2] = (
        base.groupby(["year", "code2"])["code3"]
        .nunique()
        .reset_index(name="n_children")
    )
    counts[1] = (
        base.groupby(["year", "code1"])["code2"]
        .nunique()
        .reset_index(name="n_children")
    )
    lvl4 = base.groupby(["year", "code4"]).size().reset_index(name="n_children")
    lvl4["n_children"] = 1
    counts[4] = lvl4
    return counts


def build_employment_views(emp: pd.DataFrame) -> Dict[int, Dict[str, pd.DataFrame]]:
    """Build employment views (age and totals) for each hierarchy level."""
    views: Dict[int, Dict[str, pd.DataFrame]] = {}
    for level in (4, 3, 2, 1):
        code_col, label_col = f"code{level}", f"label{level}"
        age_view = emp.groupby(
            ["year", "age", code_col, label_col], as_index=False
        )["employment"].sum()
        total_view = (
            age_view.groupby(["year", code_col, label_col], as_index=False)["employment"]
            .sum()
            .rename(columns={"employment": "employment_total"})
        )
        views[level] = {"age": age_view, "total": total_view}
    return views


def build_level_frame(
    level: int, views: Dict[int, Dict[str, pd.DataFrame]], children: Dict[int, pd.DataFrame]
) -> pd.DataFrame:
    """Combine age-level employment, totals and child counts for a level."""
    code_col, label_col = f"code{level}", f"label{level}"
    age_view = views[level]["age"].copy()
    totals = views[level]["total"]

    merged = (
        age_view.merge(totals, on=["year", code_col, label_col], how="left")
        .merge(children[level], on=["year", code_col], how="left")
    )
    merged["level"] = level
    merged["taxonomy"] = TAXONOMY
    merged = merged.rename(columns={code_col: "code", label_col: "label"})

    ordered = [
        "taxonomy",
        "level",
        "code",
        "label",
        "year",
        "n_children",
        "age",
        "employment",
        "employment_total",
    ]
    return merged[ordered]


def run_pipeline(
    *,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> pd.DataFrame:
    """Run the SCB-only pipeline and return aggregated employment data."""
    logger.info("Starting SCB-only employment pipeline")
    raw = fetch_all_employment_data()
    employment = prepare_employment(raw, year_min=year_min, year_max=year_max)

    if employment.empty:
        raise ValueError("No SCB employment rows remain after filtering.")

    children = compute_children_maps(employment)
    emp_views = build_employment_views(employment)

    levels = [
        build_level_frame(level, emp_views, children) for level in (1, 2, 3, 4)
    ]
    combined = pd.concat(levels, ignore_index=True)
    combined = combined.sort_values(["level", "code", "year", "age"], ignore_index=True)
    combined = apply_translations(combined)
    return combined
