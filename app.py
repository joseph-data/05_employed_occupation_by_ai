# Shiny Express app for exploring SCB employment by occupation.
#
# This file defines the UI controls (sidebar) and the reactive filters that
# drive the Plotly output. Data is loaded once at startup via `load_payload()`
# and then filtered client-side.

from pathlib import Path

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
from src.plot_helper import employment_multi_plot


# Helpers for UI mapping
LEVEL_CHOICES = {value: label for label, value in LEVEL_OPTIONS}
YEAR_RANGE_DEFAULT = list(range(DEFAULT_YEAR_RANGE[0], DEFAULT_YEAR_RANGE[1] + 1))

# ======================================================
#  UI LAYOUT
# ======================================================
css_file = Path(__file__).parent / "css" / "theme.css"

ui.include_css(css_file)

ui.tags.head(
    ui.tags.link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
    )
)

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
    ui.input_action_button(
        "reset_filters",
        "Reset filters",
        icon=ui.tags.i(class_="fas fa-rotate-left"),
        class_="btn-primary mt-3 w-100",
    )


# ======================================================
#  REACTIVE STATE
# ======================================================

# Load the (cached) pipeline output once at startup; filters operate on this in-memory DataFrame.
payload = load_payload()


@reactive.effect
@reactive.event(input.reset_filters)
def _reset_filters():
    # Reset UI inputs back to defaults (this does not trigger a data reload).
    ui.update_select("level", selected=DEFAULT_LEVEL)
    ui.update_slider("year_range", value=DEFAULT_YEAR_RANGE)
    ui.update_selectize("selectize", selected=[])


# Build Selectize choices per selected level
@reactive.calc
def level_label_choices():
    # Shiny choices are `{value: label}`; we use the plain label as the value returned by the input,
    # while displaying `code - label` in the dropdown.
    df = payload
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

    # Prune selections that no longer exist after switching levels.
    valid_selected = [s for s in current if s in choices]

    # # apply a default when nothing valid remains
    # if not valid_selected and choices:
    #     # pick the first option (or slice for multiple defaults)
    #     valid_selected = [next(iter(choices))]

    ui.update_selectize("selectize", choices=choices, selected=valid_selected)


# Filtered data based on UI inputs
@reactive.calc
def filtered_data():
    df = payload
    level = int(input.level())
    year_min, year_max = input.year_range()
    selected_titles = input.selectize()

    idx_level = df["level"] == level
    idx_year = df["year"].between(year_min, year_max)

    # If no titles selected, return empty dataframe
    if not selected_titles:
        # Returning an empty frame allows the plot helper to render a friendly placeholder.
        return df[idx_level & idx_year & (df["label"] == "")].copy()

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
        return employment_multi_plot(filtered_data(), level=input.level())
