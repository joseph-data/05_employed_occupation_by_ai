"""
Shiny app: Employment headcount by age group for a selected SSYK3 occupation,
indexed to 2022 = 1. Uses SCB AKU employment pulled via scripts/04_occ.py.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd
from shiny import App, render, ui

ROOT = Path(__file__).resolve().parent
OCC_PATH = ROOT / "scripts" / "04_occ.py"

# Age groups available from SCB; keep order consistent for the UI and legend.
AGE_ORDER: List[str] = [
    "16-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
]
AGE_LABELS: Dict[str, str] = {age: f"{age} years" for age in AGE_ORDER}


def _load_occ_module():
    """Load the employment fetcher from scripts/04_occ.py."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("scripts.occ", OCC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def load_employment() -> pd.DataFrame:
    """Fetch SCB AKU employment by occupation, age, and year."""
    occ_mod = _load_occ_module()
    df = occ_mod.fetch_scb_aku_occupations()
    df = df.rename(columns={"code_3": "code"})
    df["code"] = df["code"].astype(str).str.zfill(3)
    df["year"] = df["year"].astype(int)
    df["value"] = df["value"].astype(int)
    df = df[df["age"].isin(AGE_ORDER)].copy()
    return df


@lru_cache(maxsize=1)
def profession_choices() -> Dict[str, str]:
    """
    Build a mapping of SSYK3 codes to display labels.
    Uses the most frequent occupation label observed for each code.
    """
    df = load_employment()
    df = df[df["code"].str.len() == 3].copy()
    df = df.dropna(subset=["occupation"])

    def pick_label(group: pd.Series) -> str:
        return group.mode().iat[0] if not group.mode().empty else group.iloc[0]

    labels = (
        df.groupby("code")["occupation"]
        .apply(pick_label)
        .reset_index()
        .sort_values("code")
    )
    return {row.code: f"{row.code} - {row.occupation}" for row in labels.itertuples()}


@lru_cache(maxsize=1)
def available_years() -> List[int]:
    """Years present in the employment series, sorted ascending."""
    df = load_employment()
    return sorted(df["year"].unique().tolist())


def build_headcount(code: str, ages: List[str], base_year: int | None) -> pd.DataFrame:
    """
    Filter employment to a single SSYK3 code and selected age groups.
    Optionally index each age group to the selected base year.
    """
    emp = load_employment()
    filtered = emp[(emp["code"] == code) & (emp["age"].isin(ages))].copy()
    if filtered.empty:
        return filtered

    if base_year is not None:
        base = (
            filtered[filtered["year"] == base_year][["age", "value"]]
            .rename(columns={"value": "base_value"})
            .set_index("age")
        )
        filtered["base_value"] = filtered["age"].map(base["base_value"])
        filtered = filtered[filtered["base_value"].notna()].copy()
        if filtered.empty:
            return filtered
        filtered["metric"] = filtered["value"] / filtered["base_value"]
    else:
        filtered["metric"] = filtered["value"]

    filtered["age_label"] = filtered["age"].map(AGE_LABELS)
    filtered = filtered.sort_values(["age", "year"])
    return filtered


def make_headcount_plot(df: pd.DataFrame, title: str, base_year: int | None):
    """Create a line plot of headcount by age group for one occupation."""
    fig, ax = plt.subplots(figsize=(10, 6))

    palette = [
        "#0072B2",
        "#009E73",
        "#E69F00",
        "#D55E00",
        "#CC79A7",
        "#56B4E9",
        "#999999",
        "#F0E442",
        "#8C564B",
    ]

    for idx, (age, group) in enumerate(df.groupby("age_label")):
        ax.plot(group["year"], group["metric"], label=age, color=palette[idx % len(palette)], linewidth=2)

    if base_year is not None:
        ax.axvline(base_year, color="#555555", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlabel("Year")
    ylabel = f"Normalized headcount (base={base_year})" if base_year is not None else "Headcount"
    ax.set_ylabel(ylabel)
    ax.set_title(f"Headcount over time by age group\n{title}")
    ax.legend(title="Age group", loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.2)
    fig.tight_layout()
    return fig


profession_map = profession_choices()
default_code = next(iter(profession_map.keys()), "")

app_ui = ui.page_fluid(
    ui.h2("Headcount over time by age group"),
    ui.input_select(
        "profession",
        "SSYK 3-digit occupation",
        choices=profession_map,
        selected=default_code,
    ),
    ui.input_select(
        "base_year",
        "Base year (optional)",
        choices={"": "No indexing (show raw values)", **{str(y): str(y) for y in available_years()}},
        selected="",
    ),
    ui.input_checkbox_group(
        "age_groups",
        "Age groups",
        choices={age: AGE_LABELS[age] for age in AGE_ORDER},
        selected=AGE_ORDER,
        inline=True,
    ),
    ui.output_plot("headcount_plot", width="100%", height="650px"),
    ui.markdown(
        "Data: SCB AKU employment. Select a base year to normalize, or leave blank to see raw headcount."
    ),
)


def server(input, output, session):
    @render.plot
    def headcount_plot():
        code = input.profession()
        ages = input.age_groups()
        base_year_raw = input.base_year()
        base_year = int(base_year_raw) if base_year_raw else None
        if not code or not ages:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "Select an occupation and at least one age group.", ha="center", va="center")
            ax.axis("off")
            return fig

        df = build_headcount(code, ages, base_year)
        if df.empty:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "No data available for this selection.", ha="center", va="center")
            ax.axis("off")
            return fig

        title = profession_map.get(code, code)
        return make_headcount_plot(df, title, base_year)


app = App(app_ui, server)


if __name__ == "__main__":
    # Run with: shiny run --reload app_headcount_age.py
    app.run()
