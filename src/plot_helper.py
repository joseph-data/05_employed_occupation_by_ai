"""Plotly figure helpers used by the Shiny app.

The app passes a filtered pipeline DataFrame into these helpers and receives
back a fully configured Plotly figure (including placeholders for empty
selections).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import AGE_ORDER


def _placeholder(msg: str) -> go.Figure:
    """Return a simple placeholder figure (used when there is nothing to plot)."""
    fig = make_subplots(rows=1, cols=1)
    fig.add_annotation(
        text=msg,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=700, width=1200, margin=dict(t=80), showlegend=False)
    return fig


def employment_multi_plot(
    df: pd.DataFrame,
    *,
    level: str | int | None = None,
    empty_message: str = "Select an occupation to load the charts.",
    no_age_message: str = "No age data available for this selection.",
) -> go.Figure:
    """Build the multi-panel employment chart.

    Expects `df` to contain (at minimum) the columns: `year`, `age`, `label`,
    and `employment`.
    """
    if df is None or df.empty:
        return _placeholder(empty_message)

    # Order ages by AGE_ORDER, append any extra groups alphabetically.
    unique_ages = [a for a in df["age"].dropna().unique() if a]
    age_set = set(unique_ages)
    age_groups = [age for age in AGE_ORDER if age in age_set]
    age_groups.extend(sorted(age_set - set(AGE_ORDER)))

    if not age_groups:
        return _placeholder(no_age_message)

    n_rows = len(age_groups)
    ssyk_level = (
        f"(🇸🇪 SSYK 2012, Level {level})" if level is not None else "(SSYK 2012)"
    )

    subplot_titles = [
        (
            f"<b>Employed Persons Aged {age} Years by Occupation</b><br>"
            f"<span style='font-size:13px; color:#6b7280;'display:inline-block;'>"
            f"{ssyk_level}"
            f"</span>"
        )
        for age in age_groups
    ]

    occupations = sorted(df["label"].dropna().unique())
    palette = px.colors.qualitative.Plotly
    occ_color_map = {
        occ: palette[i % len(palette)] for i, occ in enumerate(occupations)
    }

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.03,
        subplot_titles=subplot_titles,
    )

    for i, age in enumerate(age_groups, start=1):
        df_age = df[df["age"] == age]
        df_plot = df_age.groupby(["year", "label"], as_index=False)["employment"].sum()

        for occ_title, sub in df_plot.groupby("label"):
            fig.add_trace(
                go.Scatter(
                    x=sub["year"],
                    y=sub["employment"],
                    mode="lines+markers",
                    showlegend=(i == 1),
                    name=occ_title,
                    line=dict(color=occ_color_map[occ_title], width=3),
                    hovertemplate=f"Age: {age}<br>Year: %{{x}}<br>Count: %{{y:,}}<extra>{occ_title}</extra>",
                ),
                row=i,
                col=1,
            )

        fig.update_yaxes(
            title_text="Number of Employed Persons",
            tickformat=",",
            rangemode="tozero",
            row=i,
            col=1,
        )
        fig.update_xaxes(
            title_text="Year",
            tickmode="linear",
            dtick=1,
            row=i,
            col=1,
        )

    BASE_PLOT_WIDTH = 1200
    LEFT_LEGEND_MARGIN = 260

    fig.update_annotations(yshift=36)
    fig.update_layout(
        height=700 * n_rows,
        width=BASE_PLOT_WIDTH + LEFT_LEGEND_MARGIN,
        legend_traceorder="normal",
        legend=dict(
            title="<b>Occupation Title(s)</b><br>",
            orientation="v",
            x=-0.1,  # left edge of plotting area
            xanchor="right",  # legend sits just outside-left
            y=0.98,
            yanchor="top",
            itemsizing="constant",
            itemwidth=35,  # keeps items compact
            tracegroupgap=6,
            bordercolor="rgba(0,0,0,0.15)",
            borderwidth=1,
            bgcolor="rgba(255,255,255,0.85)",
            font=dict(size=12),
            indentation=10,
            yref="paper",
        ),
        margin=dict(
            t=170,
            l=LEFT_LEGEND_MARGIN,
            r=60,
            b=60,
        ),
        plot_bgcolor="#f5f7fb",
        xaxis_showgrid=True,
    )

    return fig


def multi_plot(df: pd.DataFrame) -> go.Figure:
    """Backwards-compatible alias for `employment_multi_plot`."""
    return employment_multi_plot(df)
