"""Compact paginated controls for the additional Basics plots."""

import json
from dash import dcc, html
import plotly.express as px
import plotly.io as pio

from ..basic_options import BOOLS, CHOICES, COLUMNS, JSON_TYPES, LABELS, MULTI_COLUMNS, NUMBERS, option_pages

PLACEHOLDERS = {
    "width": "Fit panel", "height": "Fit panel", "sort_by": "Keep row order",
    "text_auto": "false, true, or .2f", "range_x": '[0, 100]', "range_y": '[0, 100]',
    "range_color": '[0, 100]', "category_orders": '{"Group": ["A", "B"]}',
    "labels": '{"Value": "Abundance"}', "hover_data_format": '{"Value": ":.2f"}',
    "color_discrete_sequence": '["#198754", "#3366cc"]', "color_discrete_map": '{"A": "red"}',
    "line_dash_sequence": '["solid", "dash"]', "line_dash_map": '{"A": "dash"}',
    "symbol_sequence": '["circle", "square"]', "symbol_map": '{"A": "circle"}',
    "pattern_shape_sequence": '["/", "x"]', "pattern_shape_map": '{"A": "/"}',
}


def basic_options_menu(kind, options, frame, page=1):
    pages = option_pages(kind)
    page = page if isinstance(page, int) and 1 <= page <= len(pages) else 1
    columns = [{"label": str(col), "value": col} for col in frame.columns]
    numeric = [{"label": str(col), "value": col} for col in frame.select_dtypes(include="number").columns]

    def field(name):
        label = LABELS.get(name, name.replace('_', ' ').capitalize())
        props = dict(id={"type": "basic-option", "plot": kind, "name": name}, value=options.get(name))
        placeholder = PLACEHOLDERS.get(name, "None")
        if name in COLUMNS | MULTI_COLUMNS:
            choices = numeric if name.startswith("error_") or name == "base" else columns
            component = dcc.Dropdown(**props, options=choices, multi=name in MULTI_COLUMNS,
                                     placeholder=placeholder, className="scatter-option__dropdown")
        elif name in BOOLS:
            component = dcc.Dropdown(**props, options=[{"label": "Off", "value": False}, {"label": "On", "value": True}],
                                     clearable=False, className="scatter-option__dropdown")
        elif name in NUMBERS:
            component = dcc.Input(**props, type="number", placeholder=placeholder,
                                  className="scatter-option__input", **NUMBERS[name])
        elif name in CHOICES or name in ("template", "color_discrete_palette", "color_continuous_scale"):
            choices = CHOICES.get(name)
            if name == "template":
                choices = [(item, item) for item in pio.templates]
            elif name == "color_discrete_palette":
                choices = [(item, item) for item in dir(px.colors.qualitative) if isinstance(getattr(px.colors.qualitative, item), list)]
            elif name == "color_continuous_scale":
                choices = [(item, item) for item in px.colors.named_colorscales()]
            component = dcc.Dropdown(**props, options=[{"label": label, "value": value} for label, value in choices],
                                     placeholder="Auto", className="scatter-option__dropdown")
        else:
            if props["value"] is not None and not isinstance(props["value"], str):
                props["value"] = json.dumps(props["value"])
            component = dcc.Input(**props, type="text", placeholder=PLACEHOLDERS.get(name),
                                  className="scatter-option__input")
            if name in JSON_TYPES:
                label += " (JSON)"
        return html.Div([html.Label(label), component], className="scatter-option", title=label)

    return [
        html.Div([
            html.Span("Plot options", className="plot-control__label"),
            html.Div(html.Div([
                html.Button(str(index), id={"type": "basic-page-button", "plot": kind, "page": index},
                            n_clicks=0, type="button",
                            className="scatter-page-button" + (" is-active" if index == page else ""),
                            **{"aria-label": f"{kind.title()} options page {index}", "aria-pressed": str(index == page).lower()})
                for index in range(1, len(pages) + 1)
            ], className="scatter-pages", role="group", **{"aria-label": f"{kind.title()} option pages"}),
                className="scatter-options-actions"),
        ], className="scatter-options-header"),
        html.Div(html.Div([field(name) for name in pages[page - 1]] + [
            html.Button("Build plot", id="build-basic-plot", type="button", n_clicks=0, className="build-plot-button"),
        ], className="scatter-options-page"), className="scatter-options"),
    ]
