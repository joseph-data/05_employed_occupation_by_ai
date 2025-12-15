from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_plotly, output_widget
from src.config import (
    DEFAULT_LEVEL,
    DEFAULT_YEAR_RANGE,
    LEVEL_OPTIONS,
    GLOBAL_YEAR_MIN,
    GLOBAL_YEAR_MAX,
)

from src.data_manager import load_payload


# Helpers for UI mapping
LEVEL_CHOICES = {value: label for label, value in LEVEL_OPTIONS}
YEAR_RANGE_DEFAULT = list(range(DEFAULT_YEAR_RANGE[0], DEFAULT_YEAR_RANGE[1] + 1))

# ======================================================
#  UI LAYOUT
# ======================================================
css_file = Path(__file__).parent / "css" / "theme.css"

ui.include_css(css_file)

ui.page_opts(
    fillable=False,
    fillable_mobile=True,
    full_width=True,
    id="page",
    lang="en",
)


with ui.sidebar(open="desktop", position="right"):
    ui.input_select(
        "level", "Select Occupation level", LEVEL_CHOICES, selected=DEFAULT_LEVEL
    )
    ui.input_selectize(
        "selectize",
        "Select Occupation title(s)",
        {},
        multiple=True,
        options=(
            {
                "placeholder": "Statisticians...",
                "create": False,
                "plugins": ["clear_button"],
            }
        ),
    )
    # ui.input_radio_buttons(
    #     "count_mode",
    #     "Employed persons display",
    #     {"raw": "Raw counts", "index": "Index to base year"},
    #     selected="raw",
    # )
    # with ui.panel_conditional("input.count_mode == 'index'"):
    #     ui.input_select(
    #         "base_year",
    #         "Base year",
    #         YEAR_RANGE_DEFAULT,
    #         selected=2022,
    #     )

    ui.input_slider(
        "year_range",
        "Year range",
        min=GLOBAL_YEAR_MIN,
        max=GLOBAL_YEAR_MAX,
        value=DEFAULT_YEAR_RANGE,
        step=1,
        sep="",
    )
    ui.input_action_button("refresh_data", "Refresh data", class_="btn-primary")


# ======================================================
#  REACTIVE STATE
# ======================================================

# Reactive value to store the loaded payload
payload_store = reactive.Value(load_payload())


@reactive.effect
@reactive.event(input.refresh_data)
def _refresh_payload():
    with ui.Progress() as progress:
        progress.set(message="Refreshing data...", value=0.1)
        # Force recompute in data manager
        updated = load_payload(force_recompute=True)
        progress.set(message="Updating UI...", value=0.8)
        payload_store.set(updated)
        progress.set(message="Done", value=1.0)


# Build Selectize choices per selected level
@reactive.calc
def level_label_choices():
    df = payload_store()
    lvl = int(input.level())
    subset = df[df["level"] == lvl][["code", "label"]].dropna().drop_duplicates()
    choices_list = []
    for _, row in subset.iterrows():
        key = row["label"]
        value = f"{row['code']} - {row['label']}"
        choices_list.append((key, value))

    # Sort by the code (extract code from display value)
    choices_list.sort(key=lambda x: x[1].split(" - ")[0])

    # Convert to dictionary while maintaining order
    return {key: value for key, value in choices_list}


# keep selectize choices in sync with level selection
@reactive.effect
def _sync_selectize_choices():
    choices = level_label_choices()
    current = input.selectize() or []

    # only keep items still valid
    valid_selected = [s for s in current if s in choices]

    # apply a default when nothing valid remains
    if not valid_selected and choices:
        # pick the first option (or slice for multiple defaults)
        valid_selected = [next(iter(choices))]

    ui.update_selectize("selectize", choices=choices, selected=valid_selected)


# Filtered data based on UI inputs
@reactive.calc
def filtered_data():
    df = payload_store()
    level = int(input.level())
    year_min, year_max = input.year_range()
    selected_titles = input.selectize()

    idx_level = df["level"] == level
    idx_year = df["year"].between(year_min, year_max)

    # If no titles selected, return empty dataframe
    if not selected_titles:
        return df[idx_level & idx_year & (df["label"] == "")].copy()  # Empty result

    idx_title = df["label"].isin(selected_titles)
    filtered_df = df[idx_level & idx_year & idx_title]

    return filtered_df


# # Warning message for no selections
# with ui.div(style="margin: 20px;"):

#     @render.ui
#     def selection_status():
#         if not input.selectize():
#             return ui.div(
#                 ui.tags.div(
#                     "⚠️ Please select at least one occupation title to view data.",
#                     style="background-color: #fff3cd; color: #856404; padding: 15px; border: 1px solid #ffeaa7; border-radius: 5px; text-align: center; font-weight: bold;",
#                 )
#             )
#         else:
#             return ui.div()  # Return empty div when selections exist


# @render_plotly
# def data_table():
#     df = filtered_data()

#     # Show message if no data available
#     if df.empty:
#         fig = go.Figure()
#         fig.add_annotation(
#             text="No data available. Please select occupation titles.",
#             xref="paper",
#             yref="paper",
#             x=0.5,
#             y=0.5,
#             showarrow=False,
#             font=dict(size=16),
#         )
#         fig.update_layout(
#             xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor="white"
#         )
#         return fig

#     fig = go.Figure(
#         data=go.Table(
#             header=dict(
#                 values=list(df.columns), fill_color="paleturquoise", align="left"
#             ),
#             cells=dict(
#                 values=[df[col] for col in df.columns],
#                 fill_color="lavender",
#                 align="left",
#             ),
#         )
#     )
#     return fig


with ui.div(style="display:flex; justify-content:center;"):
    output_widget("employment_plot")

    @render_plotly
    def employment_plot2():
        df = filtered_data()

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
            (f"<b>Employed Persons Aged {age} Years by Occupation")
            for age in age_groups
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

        for i, age in enumerate(age_groups, start=1):
            df_age = df[df["age"] == age]

            # Aggregate by Year and Label
            df_plot = df_age.groupby(["year", "label"], as_index=False)[
                "employment"
            ].sum()

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
                        line=dict(color=occ_color_map[occ_title], width=3),
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

            # X-axis update must be inside the loop to target the current row (i)
            fig.update_xaxes(
                title_text="Year",
                tickmode="linear",
                dtick=1,
                row=i,
                col=1,
            )

        # ------------------------------------------------------------------
        # 4. Global layout tweaks
        # ------------------------------------------------------------------
        fig.update_annotations(yshift=30)
        fig.update_layout(
            height=700 * len(age_groups),
            width=1200,
            legend_traceorder="normal",
            legend=dict(
                title="Occupation Title(s)",
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="left",
                x=-0.5,
                bordercolor="#c7c7c7",
                borderwidth=2,
                bgcolor="#f9f9f9",
                font=dict(size=10),
            ),
            margin=dict(t=100, l=50, r=80, b=40),
            plot_bgcolor="#f5f7fb",
            xaxis_showgrid=True,
        )

        return fig
