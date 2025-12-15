import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def multi_plot(df: pd.DataFrame) -> go.Figure:
    age_groups = sorted(df["age"].dropna().unique())

    occupations = sorted(df["label"].dropna().unique())
    # Use a Plotly qualitative palette
    palette = px.colors.qualitative.Plotly
    # Cycle safely if occupations > palette length
    occ_color_map = {
        occ: palette[i % len(palette)] for i, occ in enumerate(occupations)
    }

    # ------------------------------------------------------------------
    # 2. Create multi-row subplot scaffolding
    # ------------------------------------------------------------------
    subplot_titles = [
        (f"<b>Employed Persons Aged {age} Years by Occupation") for age in age_groups
    ]

    fig = make_subplots(
        rows=len(age_groups),
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.03,
        subplot_titles=subplot_titles,
    )

    # ------------------------------------------------------------------
    # 3. Add traces per age group and exposure level
    # ------------------------------------------------------------------

    # Need to pre-define the max row number for the final x-axis update
    max_row = len(age_groups)

    for i, age in enumerate(age_groups, start=1):
        df_age = df[df["age"] == age]

        # Aggregate by Year and Label
        df_plot = df_age.groupby(["year", "label"], as_index=False)["employment"].sum()

        for occ_title, sub in df_plot.groupby("label"):
            fig.add_trace(
                go.Scatter(
                    x=sub["year"],
                    y=sub["employment"],
                    mode="lines+markers",
                    showlegend=True
                    if i == 1
                    else False,  # Show legend only in the first subplot
                    name=occ_title,
                    line=dict(color=occ_color_map[occ_title], width=2),
                    # Add group/age info to the hover template for debugging/clarity
                    hovertemplate=f"Age: {age}<br>Year: %{{x}}<br>Employment: %{{y:,}}<extra>{occ_title}</extra>",
                ),
                row=i,
                col=1,
            )

        # Y-axis update must be inside the loop to target the current row (i)
        fig.update_yaxes(
            title_text="Number of Employed Persons",
            tickformat=",",
            rangemode="tozero",
            row=i,
            col=1,
        )

        # X-axis update must target the bottom row (max_row)
        fig.update_xaxes(
            title_text="Year",
            tickmode="linear",
            dtick=1,
            row=max_row,
            col=1,
        )

    # ------------------------------------------------------------------
    # 4. Global layout tweaks
    # ------------------------------------------------------------------
    fig.update_annotations(yshift=30)
    fig.update_layout(
        height=400 * len(age_groups),  # Reduced height for sample data
        width=1000,  # Added a main title
        legend_traceorder="normal",
        legend=dict(
            title="Occupation Title(s)",
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.02,
            bordercolor="#c7c7c7",
            borderwidth=1,
            bgcolor="#f9f9f9",
            font=dict(size=10),
        ),
        margin=dict(t=100, l=50, r=80, b=40),
        plot_bgcolor="#f5f7fb",
        xaxis_showgrid=True,
    )

    return fig
